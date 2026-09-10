"""Unit and integration tests for CI/CD Quality Gate (DEV-011)."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from agtoosa.review.ci import (
    PRCommentFormatter,
    STICKY_COMMENT_MARKER,
    parse_pr_number_from_env,
    post_or_update_pr_comment,
    run_ci_gate
)
from agtoosa.review.intelligence import DriftReport, DriftFinding
from agtoosa.graph.store import GraphStore
from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.cli.main import main


class TestPRCommentFormatter(unittest.TestCase):
    """Test markdown formatting for GitHub PR comments."""

    def test_format_approved_verdict(self):
        report = DriftReport(
            verdict="APPROVED",
            findings=[],
            modified_files=["agtoosa/watcher/watcher.py"],
            affected_stories=["DEV-009"]
        )
        formatter = PRCommentFormatter(report)
        md = formatter.format_markdown()

        self.assertIn("Architecture_Gate-APPROVED", md)
        self.assertIn("✨ **Clean Architectural Verification**", md)
        self.assertIn("DEV-009", md)
        self.assertIn(STICKY_COMMENT_MARKER, md)
        self.assertIn("pytest tests/test_watcher.py", md)

    def test_format_blocked_with_drift_alarms(self):
        report = DriftReport(
            verdict="BLOCKED",
            findings=[
                DriftFinding(
                    severity="ERROR",
                    category="LAYER_VIOLATION",
                    message="Core imports CLI",
                    symbol_or_path="agtoosa/core/model.py"
                ),
                DriftFinding(
                    severity="WARNING",
                    category="BLAST_RADIUS",
                    message="High Blast Radius: Impacts 12 callers",
                    symbol_or_path="agtoosa/graph/store.py"
                )
            ],
            modified_files=["agtoosa/core/model.py", "agtoosa/graph/store.py"],
            pr_diff_summary={
                "directly_modified_symbols": [
                    {
                        "name": "GraphStore.get_node",
                        "type": "function",
                        "path": "agtoosa/graph/store.py",
                        "impacted_count": 12,
                        "top_dependents": ["resolve_node", "compute_impact"]
                    }
                ],
                "high_risk_symbols": [{"name": "GraphStore.get_node"}]
            }
        )
        formatter = PRCommentFormatter(report)
        md = formatter.format_markdown()

        self.assertIn("Architecture_Gate-BLOCKED", md)
        self.assertIn("> [!CAUTION]", md)
        self.assertIn("Blocker: LAYER_VIOLATION", md)
        self.assertIn("> [!WARNING]", md)
        self.assertIn("Warning: BLAST_RADIUS", md)
        self.assertIn("GraphStore.get_node", md)
        self.assertIn("**12** ⚠️", md)
        self.assertIn("resolve_node, compute_impact", md)
        self.assertIn("pytest tests/test_metrics.py", md)


class TestCIEnvironmentAndPosting(unittest.TestCase):
    """Test PR number parsing and GitHub REST API integration."""

    def test_parse_pr_number_from_env_direct(self):
        with patch.dict(os.environ, {"PR_NUMBER": "123"}):
            self.assertEqual(parse_pr_number_from_env(), 123)

    def test_parse_pr_number_from_ref(self):
        with patch.dict(os.environ, {"GITHUB_REF": "refs/pull/456/merge", "PR_NUMBER": ""}):
            self.assertEqual(parse_pr_number_from_env(), 456)

    def test_parse_pr_number_from_event_json(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"pull_request": {"number": 789}}, f)
            temp_path = f.name

        try:
            with patch.dict(os.environ, {"GITHUB_EVENT_PATH": temp_path, "PR_NUMBER": "", "GITHUB_REF": ""}):
                self.assertEqual(parse_pr_number_from_env(), 789)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_post_comment_writes_step_summary(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            summary_path = f.name

        try:
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": summary_path}):
                post_or_update_pr_comment("## Test Summary Content")
                content = Path(summary_path).read_text(encoding="utf-8")
                self.assertIn("## Test Summary Content", content)
        finally:
            Path(summary_path).unlink(missing_ok=True)

    @patch("urllib.request.urlopen")
    def test_post_new_sticky_comment(self, mock_urlopen):
        # Mock GET comments returning empty list
        mock_get_resp = MagicMock()
        mock_get_resp.read.return_value = json.dumps([]).encode("utf-8")
        mock_get_resp.__enter__.return_value = mock_get_resp

        # Mock POST comment returning 201 Created
        mock_post_resp = MagicMock()
        mock_post_resp.status = 201
        mock_post_resp.__enter__.return_value = mock_post_resp

        mock_urlopen.side_effect = [mock_get_resp, mock_post_resp]

        success = post_or_update_pr_comment(
            comment_md=f"## Review\n{STICKY_COMMENT_MARKER}",
            repo="sky2464/Agtoosa2",
            pr_number=10,
            token="ghp_fake_token"
        )
        self.assertTrue(success)
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("urllib.request.urlopen")
    def test_update_existing_sticky_comment(self, mock_urlopen):
        # Mock GET comments returning existing comment with marker
        existing_comments = [
            {"id": 999, "body": f"Old review\n{STICKY_COMMENT_MARKER}"}
        ]
        mock_get_resp = MagicMock()
        mock_get_resp.read.return_value = json.dumps(existing_comments).encode("utf-8")
        mock_get_resp.__enter__.return_value = mock_get_resp

        # Mock PATCH comment returning 200 OK
        mock_patch_resp = MagicMock()
        mock_patch_resp.status = 200
        mock_patch_resp.__enter__.return_value = mock_patch_resp

        mock_urlopen.side_effect = [mock_get_resp, mock_patch_resp]

        success = post_or_update_pr_comment(
            comment_md=f"## Updated Review\n{STICKY_COMMENT_MARKER}",
            repo="sky2464/Agtoosa2",
            pr_number=10,
            token="ghp_fake_token"
        )
        self.assertTrue(success)
        self.assertEqual(mock_urlopen.call_count, 2)


class TestCIGateExecution(unittest.TestCase):
    """Test full CI gate workflow with graph store and CLI commands."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.agtoosa_dir = self.workspace / ".agtoosa"
        self.agtoosa_dir.mkdir()
        self.db_path = self.agtoosa_dir / "graph.db"
        self.store = GraphStore(self.db_path)

        # Build dummy clean graph
        n1 = Node(id="file:agtoosa/review/ci.py", name="ci.py", node_type=NodeType.FILE, path="agtoosa/review/ci.py")
        n2 = Node(id="class:PRCommentFormatter", name="PRCommentFormatter", node_type=NodeType.CLASS, path="agtoosa/review/ci.py")
        e1 = Edge(source_id=n1.id, target_id=n2.id, edge_type=EdgeType.CONTAINS, provenance="test")
        self.store.insert_batch([n1, n2], [e1])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_run_ci_gate_clean_pass(self):
        out_comment = self.workspace / "comment.md"
        exit_code, report, md = run_ci_gate(
            store=self.store,
            workspace_root=self.workspace,
            base_ref="HEAD",
            strict=True,
            output_comment_path=str(out_comment)
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(report.verdict, "APPROVED")
        self.assertTrue(out_comment.exists())
        self.assertIn("Architecture_Gate-APPROVED", out_comment.read_text(encoding="utf-8"))

    def test_cli_ci_review_and_check(self):
        out_comment = self.workspace / "pr.md"

        # 1. Test 'agtoosa ci review'
        ret_review = main([
            "-C", str(self.workspace),
            "ci", "review",
            "--base-ref", "HEAD",
            "--output-comment", str(out_comment)
        ])
        self.assertEqual(ret_review, 0)
        self.assertTrue(out_comment.exists())

        # 2. Test 'agtoosa ci check'
        ret_check = main([
            "-C", str(self.workspace),
            "ci", "check",
            "--base-ref", "HEAD"
        ])
        self.assertEqual(ret_check, 0)


if __name__ == "__main__":
    unittest.main()
