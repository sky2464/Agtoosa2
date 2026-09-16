"""Tests for graph metrics, PageRank, cycle detection, and health scorecard."""

import sys
import tempfile
import unittest
from pathlib import Path

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.metrics import MetricsEngine


class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.store = GraphStore(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_acyclic_graph_metrics(self):
        # Acyclic pipeline: A -> B -> C
        nodes = [
            Node(id="func:a", name="func_a", node_type=NodeType.FUNCTION, path="a.py"),
            Node(id="func:b", name="func_b", node_type=NodeType.FUNCTION, path="b.py"),
            Node(id="func:c", name="func_c", node_type=NodeType.FUNCTION, path="c.py")
        ]
        edges = [
            Edge(source_id="func:a", target_id="func:b", edge_type=EdgeType.CALLS),
            Edge(source_id="func:b", target_id="func:c", edge_type=EdgeType.CALLS)
        ]
        self.store.insert_batch(nodes, edges)

        engine = MetricsEngine(self.store)
        report = engine.compute_all()

        self.assertEqual(report["stats"]["total_nodes"], 3)
        self.assertEqual(report["stats"]["total_edges"], 2)
        self.assertEqual(len(report["cycles"]), 0)

        # PageRank: C should have highest rank because A -> B -> C
        top_hub = report["top_hubs"][0]
        self.assertEqual(top_hub["name"], "func_c")

        # Health scorecard
        self.assertIn(report["health_scorecard"]["grade"], ("A", "A+", "B"))

        # Spectral and curvature invariants
        self.assertIn("spectral", report)
        self.assertIn("curvature", report)
        self.assertIn("algebraic_connectivity", report["spectral"])
        self.assertIn("cheeger_conductance", report["spectral"])
        self.assertIn("von_neumann_entropy", report["spectral"])
        self.assertIn("bottleneck_count", report["curvature"])

        # Output formatting includes spectral invariants
        text_out = engine.format_text(report)
        self.assertIn("Algebraic Connectivity", text_out)
        self.assertIn("Von Neumann Graph Entropy", text_out)

        md_out = engine.format_markdown(report)
        self.assertIn("Spectral & Geometric Invariants", md_out)

    def test_cycle_detection(self):
        # Circular chain: Module1 -> Module2 -> Module3 -> Module1
        nodes = [
            Node(id="file:m1.py", name="m1.py", node_type=NodeType.FILE, path="m1.py"),
            Node(id="file:m2.py", name="m2.py", node_type=NodeType.FILE, path="m2.py"),
            Node(id="file:m3.py", name="m3.py", node_type=NodeType.FILE, path="m3.py")
        ]
        edges = [
            Edge(source_id="file:m1.py", target_id="file:m2.py", edge_type=EdgeType.IMPORTS),
            Edge(source_id="file:m2.py", target_id="file:m3.py", edge_type=EdgeType.IMPORTS),
            Edge(source_id="file:m3.py", target_id="file:m1.py", edge_type=EdgeType.IMPORTS)
        ]
        self.store.insert_batch(nodes, edges)

        engine = MetricsEngine(self.store)
        report = engine.compute_all()

        self.assertGreaterEqual(len(report["cycles"]), 1)
        cycle_names = [item["name"] for item in report["cycles"][0]]
        self.assertIn("m1.py", cycle_names)
        self.assertIn("m2.py", cycle_names)
        self.assertIn("m3.py", cycle_names)

        # Warning generated in health scorecard
        self.assertTrue(any("circular dependency" in w.lower() for w in report["health_scorecard"]["warnings"]))

    def test_report_formatting(self):
        nodes = [
            Node(id="func:main", name="main", node_type=NodeType.FUNCTION, path="app.py")
        ]
        self.store.insert_batch(nodes, [])

        engine = MetricsEngine(self.store)
        report = engine.compute_all()

        text_out = engine.format_text(report)
        self.assertIn("Agtoosa2 Architecture Health", text_out)
        self.assertIn("Total Nodes: 1", text_out)

        md_out = engine.format_markdown(report)
        self.assertIn("# Agtoosa2 Architecture Health", md_out)
        self.assertIn("| **Total Entities** | 1 |", md_out)

    def test_health_scorecard_grade_a_plus_and_test_verification(self):
        # 6 code nodes
        nodes = [
            Node(id=f"func:app.py:f{i}", name=f"f{i}", node_type=NodeType.FUNCTION, path="app.py")
            for i in range(6)
        ]
        # Test node calling code nodes f0 and f1 (>20% verification)
        test_node = Node(id="func:tests/test_app.py:test_f0", name="test_f0", node_type=NodeType.FUNCTION, path="tests/test_app.py")
        nodes.append(test_node)

        edges = [
            Edge(source_id="func:tests/test_app.py:test_f0", target_id="func:app.py:f0", edge_type=EdgeType.VERIFIES),
            Edge(source_id="func:tests/test_app.py:test_f0", target_id="func:app.py:f1", edge_type=EdgeType.CALLS),
            Edge(source_id="func:app.py:f0", target_id="func:app.py:f2", edge_type=EdgeType.CALLS),
            Edge(source_id="func:app.py:f1", target_id="func:app.py:f3", edge_type=EdgeType.CALLS),
            Edge(source_id="func:app.py:f2", target_id="func:app.py:f4", edge_type=EdgeType.CALLS),
            Edge(source_id="func:app.py:f3", target_id="func:app.py:f5", edge_type=EdgeType.CALLS),
        ]
        self.store.insert_batch(nodes, edges)

        engine = MetricsEngine(self.store)
        report = engine.compute_all()
        health = report["health_scorecard"]

        self.assertEqual(health["grade"], "A+")
        self.assertEqual(health["score"], 100)
        self.assertEqual(health["isolated_count"], 0)
        self.assertGreaterEqual(health["verified_units_ratio"], 0.2)
        self.assertEqual(len(health["warnings"]), 0)


if __name__ == "__main__":
    unittest.main()
