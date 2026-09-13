"""Automated test suite for DEV-029: PR Blast Radius & Breaking Schema Review Bot."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import io

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.review.pr_bot import (
    PRReviewEngine,
    PRBotCommentFormatter,
    post_or_update_pr_comment,
    STICKY_PR_BOT_MARKER
)
from agtoosa.cli.main import main


class TestPRReviewBot(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.db_path = self.workspace / ".agtoosa" / "graph.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.store = GraphStore(self.db_path)

        # 1. Setup sample graph:
        # File nodes
        f1 = Node(id="file:app/api.py", name="api.py", node_type=NodeType.FILE, path="app/api.py")
        f2 = Node(id="file:app/service.py", name="service.py", node_type=NodeType.FILE, path="app/service.py")

        # Function nodes
        fn_checkout = Node(
            id="func:app/api.py:checkout",
            name="checkout",
            node_type=NodeType.FUNCTION,
            path="app/api.py",
            start_line=10,
            end_line=25
        )
        fn_process_payment = Node(
            id="func:app/service.py:process_payment",
            name="process_payment",
            node_type=NodeType.FUNCTION,
            path="app/service.py",
            start_line=15,
            end_line=30
        )
        fn_caller = Node(
            id="func:app/client.py:run_job",
            name="run_job",
            node_type=NodeType.FUNCTION,
            path="app/client.py",
            start_line=5,
            end_line=12
        )

        # Endpoint node (FastAPI /checkout route)
        ep = Node(
            id="endpoint:POST:/checkout",
            name="POST /checkout",
            node_type=NodeType.ENDPOINT,
            path="app/api.py",
            start_line=10,
            metadata={"http_method": "POST", "path": "/checkout", "framework": "fastapi"}
        )

        # Topic node (Kafka orders topic)
        top = Node(
            id="topic:orders.v1",
            name="orders.v1",
            node_type=NodeType.TOPIC,
            path="app/service.py",
            start_line=20,
            metadata={"topic": "orders.v1", "broker": "kafka"}
        )

        # Edges
        e_route = Edge(source_id=ep.id, target_id=fn_checkout.id, edge_type=EdgeType.ROUTES_TO)
        e_call = Edge(source_id=fn_checkout.id, target_id=fn_process_payment.id, edge_type=EdgeType.CALLS)
        e_pub = Edge(source_id=fn_process_payment.id, target_id=top.id, edge_type=EdgeType.PUBLISHES)
        e_sub = Edge(source_id=fn_caller.id, target_id=top.id, edge_type=EdgeType.SUBSCRIBES)

        self.store.insert_batch(
            [f1, f2, fn_checkout, fn_process_payment, fn_caller, ep, top],
            [e_route, e_call, e_pub, e_sub]
        )

        # Ingest sample telemetry
        self.store.save_telemetry_batch([
            {
                "node_id": fn_process_payment.id,
                "call_count": 15000,
                "total_duration_ms": 637500.0,
                "error_count": 300
            }
        ])

        self.engine = PRReviewEngine(self.store, self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pr_analysis_with_routes_and_events(self):
        """Verify PRReviewEngine detects modified symbols, impacted routes, and impacted topics."""
        # Simulate git diff modifying lines 18-22 of app/service.py (touches process_payment)
        diff_ranges = {
            "app/service.py": [(18, 22)]
        }

        analysis = self.engine.analyze(diff_ranges=diff_ranges)

        # Check modified symbols
        self.assertEqual(len(analysis["modified_symbols"]), 1)
        sym = analysis["modified_symbols"][0]
        self.assertEqual(sym["name"], "process_payment")
        self.assertEqual(sym["caller_count"], 1)

        # Check production risk tier (15,000 calls -> P0_CRITICAL)
        self.assertEqual(analysis["production_risk_tier"], "P0_CRITICAL")
        self.assertEqual(analysis["total_traffic_at_risk"], 15000)

        # Check impacted topics (process_payment publishes to orders.v1)
        self.assertEqual(len(analysis["impacted_topics"]), 1)
        top = analysis["impacted_topics"][0]
        self.assertEqual(top["name"], "orders.v1")
        self.assertEqual(top["broker"], "kafka")
        self.assertIn(sym["id"], top["touched_publishers"])

    def test_markdown_comment_formatting(self):
        """Verify PRBotCommentFormatter produces clean GitHub Markdown with marker and tables."""
        diff_ranges = {
            "app/api.py": [(12, 14)]
        }
        analysis = self.engine.analyze(diff_ranges=diff_ranges)
        formatter = PRBotCommentFormatter(analysis)
        md = formatter.format_markdown(pr_number=42)

        self.assertIn(STICKY_PR_BOT_MARKER, md)
        self.assertIn("## 🏛️ Agtoosa Architecture & Blast Radius Bot", md)
        self.assertIn("Overall Gate Verdict", md)
        self.assertIn("Production Traffic Risk", md)
        self.assertIn("Impacted HTTP API Routes", md)
        self.assertIn("/checkout", md)

    @patch("urllib.request.urlopen")
    def test_github_pr_comment_posting(self, mock_urlopen):
        """Verify post_or_update_pr_comment correctly calls GitHub API."""
        # 1. Simulate empty existing comments (POST new comment)
        mock_resp_list = MagicMock()
        mock_resp_list.read.return_value = b"[]"
        mock_resp_list.__enter__.return_value = mock_resp_list

        mock_resp_post = MagicMock()
        mock_resp_post.read.return_value = json.dumps({"id": 101, "body": "test"}).encode("utf-8")
        mock_resp_post.__enter__.return_value = mock_resp_post

        mock_urlopen.side_effect = [mock_resp_list, mock_resp_post]

        res = post_or_update_pr_comment(
            repo="owner/repo",
            pr_number=123,
            comment_body=f"{STICKY_PR_BOT_MARKER}\nHello",
            token="ghp_fake_token"
        )
        self.assertEqual(res["id"], 101)

    def test_cli_ci_pr_bot_json(self):
        """Verify 'agtoosa ci pr-bot --json' executes cleanly."""
        out_f = self.workspace / "comment.md"
        with patch.object(PRReviewEngine, "get_git_diff_ranges", return_value={"app/api.py": [(12, 15)]}):
            code = main([
                "-C", str(self.workspace),
                "ci", "pr-bot",
                "-o", str(out_f),
                "--json"
            ])
            self.assertEqual(code, 0)
            self.assertTrue(out_f.exists())
            comment_text = out_f.read_text(encoding="utf-8")
            self.assertIn(STICKY_PR_BOT_MARKER, comment_text)


if __name__ == "__main__":
    unittest.main()
