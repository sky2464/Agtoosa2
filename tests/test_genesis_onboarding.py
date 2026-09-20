"""Automated test suite for Adaptive Onboarding & Genesis Dashboard (DEV-058)."""

from pathlib import Path
import tempfile
import unittest
import urllib.request
import json
import threading

from agtoosa.core.model import Node, NodeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.visualizer import VisualizerEngine
from agtoosa.graph.server import run_studio_server


class TestGenesisOnboarding(unittest.TestCase):
    """Verify adaptive Genesis Launchpad, dynamic project grounding, and progressive disclosure."""

    def test_genesis_detection_on_documentation_only_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db_path = root / ".agtoosa" / "graph.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            store = GraphStore(db_path)

            # Insert 2 doc nodes (reproducing test2 scenario)
            doc1 = Node(id="doc:readme", node_type=NodeType.DOC, name="README.md", path="README.md")
            doc2 = Node(id="doc:specs", node_type=NodeType.DOC, name="specs.md", path="docs/specs.md")
            store.insert_batch([doc1, doc2], [])

            vis = VisualizerEngine(store, workspace_root=root)
            data = vis.extract_graph_data()

            ws_meta = data["workspaceMetadata"]
            self.assertTrue(ws_meta["isGenesis"], "Should be in Genesis state when 0 code files exist")
            self.assertEqual(ws_meta["workspaceName"], root.name)
            self.assertEqual(ws_meta["codeFileCount"], 0)
            self.assertEqual(ws_meta["totalNodeCount"], 2)

            findings = data["plainEnglishFindings"]
            self.assertTrue(len(findings) >= 2)
            finding_ids = [f["id"] for f in findings]
            self.assertIn("genesis_stage", finding_ids)
            self.assertIn("agent_governance", finding_ids)

    def test_generated_html_structure_and_dynamic_grounding(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db_path = root / ".agtoosa" / "graph.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            store = GraphStore(db_path)

            # Insert 1 doc node
            store.insert_batch([Node(id="doc:guide", node_type=NodeType.DOC, name="guide.md", path="guide.md")], [])

            vis = VisualizerEngine(store, workspace_root=root)
            html = vis.generate_html()

            # Verify presence of Genesis Launchpad elements
            self.assertIn("view-genesis", html)
            self.assertIn("btn-mode-toggle", html)
            self.assertIn("genesis-superpowers-grid", html)
            self.assertIn("10x Smarter AI Agent Context", html)
            self.assertIn("Spaghetti-Proof Guardrails", html)
            self.assertIn("Living Architecture as Code", html)
            self.assertIn("btn-enforce-agents", html)
            self.assertIn("btn-preview-cockpit", html)
            self.assertIn("advanced-tab", html)

            # Verify presence of Engineering Loop and Copilot guidance elements
            self.assertIn("genesis-workflow-section", html)
            self.assertIn("The Agtoosa Engineering Loop: Develop, Update &amp; Verify", html)
            self.assertIn("Phase 1: Develop", html)
            self.assertIn("Phase 2: Update", html)
            self.assertIn("Phase 3: Verify", html)
            self.assertIn("genesis-copilot-card", html)
            self.assertIn("btn-copy-cmd", html)

            # Verify no hardcoded "39 Stories" or "8 core Agtoosa subsystems"
            self.assertNotIn("39 Stories", html)
            self.assertNotIn("8 core Agtoosa subsystems", html)

    def test_server_agent_enforce_endpoint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db_path = root / ".agtoosa" / "graph.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            store = GraphStore(db_path)

            server = run_studio_server(store, root, port=0, auto_port=True)
            actual_port = server.server_port
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()

            try:
                url = f"http://127.0.0.1:{actual_port}/api/agent/enforce"
                req = urllib.request.Request(
                    url,
                    data=json.dumps({"with_git_hooks": False}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req) as resp:
                    self.assertEqual(resp.status, 200)
                    res_data = json.loads(resp.read().decode("utf-8"))
                    self.assertTrue(res_data["is_enforced"])
                    self.assertIn("AGENTS.md", res_data["installed_files"])

                # Verify files written to disk
                self.assertTrue((root / "AGENTS.md").exists())
                self.assertTrue((root / "CLAUDE.md").exists())
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
