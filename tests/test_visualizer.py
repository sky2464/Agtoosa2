"""Tests for standalone offline HTML visualizer."""

from pathlib import Path
import sys
import tempfile
import unittest

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.visualizer import VisualizerEngine


class TestVisualizer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.store = GraphStore(self.db_path)

        nodes = [
            Node(id="class:Service", name="Service", node_type=NodeType.CLASS, path="svc.py"),
            Node(id="func:start", name="start", node_type=NodeType.FUNCTION, path="svc.py")
        ]
        edges = [
            Edge(source_id="class:Service", target_id="func:start", edge_type=EdgeType.CONTAINS)
        ]
        self.store.insert_batch(nodes, edges)
        self.visualizer = VisualizerEngine(self.store)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_html_content(self):
        html = self.visualizer.generate_html()
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Agtoosa Studio — Architecture Command Center", html)
        self.assertIn("kpi-strip", html)
        self.assertIn("perspective-switcher", html)
        self.assertIn("Domain Blueprint", html)
        self.assertIn("btn-copy-ai", html)
        self.assertIn("canvas-container", html)
        self.assertIn("sidebar", html)
        self.assertIn("class:Service", html)
        self.assertIn("func:start", html)
        self.assertIn("spectral-curvature-section", html)
        self.assertIn("graph-btn-bottlenecks", html)
        self.assertIn("view-overview", html)
        self.assertIn("radar-subnav", html)
        self.assertIn("v0.9.9", html)
        self.assertIn('class="view-panel active"', html)
        self.assertIn("overview-copilot-card", html)
        self.assertIn("The Agtoosa Engineering Loop: Develop, Update", html)
        self.assertNotIn("&bull;", html)

    def test_filter_type(self):
        html_filtered = self.visualizer.generate_html(filter_type="class")
        self.assertIn("class:Service", html_filtered)
        # func:start should be filtered out from nodes payload
        self.assertNotIn('"name": "start"', html_filtered)

    def test_save_html_file(self):
        out_path = Path(self.temp_dir.name) / "view.html"
        res = self.visualizer.save_html(out_path, open_browser=False)
        self.assertEqual(res, out_path)
        self.assertTrue(out_path.exists())
        self.assertGreater(out_path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
