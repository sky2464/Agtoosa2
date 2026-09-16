"""Tests for Mathematical & Invariant MCP server tools (DEV-052, DEV-053, DEV-054, DEV-055)."""

import json
from pathlib import Path
import tempfile
import unittest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.mcp.server import MCPServer


class TestMathematicalMCP(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / ".agtoosa" / "graph.db"
        self.store = GraphStore(self.db_path)

        # Build a rich graph for testing spectral, curvature, submodular, and causal tools
        nodes = [
            Node(id="story:DEV-001", name="Story DEV-001", node_type=NodeType.STORY, path="docs/specs/spec-1.md", docstring="Implement core engine"),
            Node(id="crit:C1", name="Criterion C1", node_type=NodeType.CRITERION, path="docs/specs/spec-1.md", docstring="Criteria 1"),
            Node(id="task:T1", name="Task T1", node_type=NodeType.TASK, path="docs/specs/spec-1.md", docstring="Task 1"),
            Node(id="func:engine", name="run_engine", node_type=NodeType.FUNCTION, path="engine.py", docstring="Execute core calculations"),
            Node(id="func:helper_a", name="helper_a", node_type=NodeType.FUNCTION, path="helper.py", docstring="Helper function A"),
            Node(id="func:helper_b", name="helper_b", node_type=NodeType.FUNCTION, path="helper.py", docstring="Helper function B"),
            Node(id="func:sink", name="sink_call", node_type=NodeType.FUNCTION, path="sink.py", docstring="Terminal sink"),
        ]

        # Edges
        edges = [
            Edge(source_id="story:DEV-001", target_id="crit:C1", edge_type=EdgeType.CONTAINS),
            Edge(source_id="story:DEV-001", target_id="task:T1", edge_type=EdgeType.CONTAINS),
            Edge(source_id="task:T1", target_id="func:engine", edge_type=EdgeType.REFERENCES),
            Edge(source_id="func:engine", target_id="func:helper_a", edge_type=EdgeType.CALLS),
            Edge(source_id="func:engine", target_id="func:helper_b", edge_type=EdgeType.CALLS),
            Edge(source_id="func:helper_a", target_id="func:sink", edge_type=EdgeType.CALLS),
            Edge(source_id="func:helper_b", target_id="func:sink", edge_type=EdgeType.CALLS),
            # Cycle for FAS testing
            Edge(source_id="func:sink", target_id="func:engine", edge_type=EdgeType.CALLS),
        ]

        self.store.insert_batch(nodes, edges)
        self.server = MCPServer(self.root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _call_tool(self, name: str, args: dict) -> dict:
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": args
            }
        }
        resp = self.server.handle_message(req)
        self.assertIsNotNone(resp)
        assert resp is not None
        self.assertNotIn("error", resp)
        content = resp["result"]["content"][0]["text"]
        return json.loads(content)

    def test_spectral_analysis_tool(self):
        # 1. Mode 'all'
        data_all = self._call_tool("agtoosa_spectral_analysis", {"mode": "all"})
        self.assertIn("cheeger_cut", data_all)
        self.assertIn("spectral_radius", data_all)
        self.assertIn("feedback_arc_set", data_all)
        self.assertIn("transitive_reduction", data_all)
        self.assertIn("von_neumann_entropy", data_all)
        self.assertGreaterEqual(data_all["von_neumann_entropy"], 0.0)

        # 2. Mode 'cut'
        data_cut = self._call_tool("agtoosa_spectral_analysis", {"mode": "cut"})
        self.assertIn("cheeger_cut", data_cut)
        self.assertNotIn("feedback_arc_set", data_cut)

        # 3. Mode 'radius'
        data_rad = self._call_tool("agtoosa_spectral_analysis", {"mode": "radius"})
        self.assertIn("spectral_radius", data_rad)
        self.assertGreater(data_rad["spectral_radius"]["spectral_radius"], 0.0)

        # 4. Mode 'fas'
        data_fas = self._call_tool("agtoosa_spectral_analysis", {"mode": "fas"})
        self.assertIn("feedback_arc_set", data_fas)
        self.assertGreaterEqual(data_fas["feedback_arc_set"]["feedback_arc_count"], 1)

    def test_submodular_context_tool(self):
        data = self._call_tool("agtoosa_submodular_context", {
            "target": "DEV-001",
            "budget_tokens": 1000
        })
        self.assertEqual(data["target"], "story:DEV-001")
        self.assertIn("selected", data)
        self.assertIn("tokens_used", data)
        self.assertIn("coverage_score", data)
        self.assertEqual(data["approximation_ratio"], 0.632)
        self.assertIn("prompt_pack", data)
        self.assertIn("Story DEV-001", data["prompt_pack"])

    def test_curvature_audit_tool(self):
        data = self._call_tool("agtoosa_curvature_audit", {
            "top": 5,
            "hyperbolic": True
        })
        self.assertIn("total_edges", data)
        self.assertIn("average_curvature", data)
        self.assertIn("bottleneck_count", data)
        self.assertIn("cluster_edge_count", data)
        self.assertIn("top_bottlenecks", data)
        self.assertIn("hyperbolicity", data)
        self.assertIn("delta", data["hyperbolicity"])

    def test_causal_effect_tool(self):
        # Causal without observational data (tests backdoor admissibility and minimal adjustment set)
        data = self._call_tool("agtoosa_causal_effect", {
            "source": "func:engine",
            "target": "func:sink"
        })
        self.assertEqual(data["source"], "func:engine")
        self.assertEqual(data["target"], "func:sink")
        self.assertIn("is_admissible", data)
        self.assertIn("minimal_adjustment_set", data)

        # Causal with observational contingency data
        contingency = [
            {"func:engine": 1, "func:sink": 1},
            {"func:engine": 1, "func:sink": 1},
            {"func:engine": 1, "func:sink": 0},
            {"func:engine": 0, "func:sink": 0},
            {"func:engine": 0, "func:sink": 0},
            {"func:engine": 0, "func:sink": 1},
        ]
        data_obs = self._call_tool("agtoosa_causal_effect", {
            "source": "func:engine",
            "target": "func:sink",
            "contingency_data": contingency
        })
        self.assertIn("causal_effect", data_obs)
        self.assertIn("average_causal_effect", data_obs["causal_effect"])
        self.assertIn("naive_observational_diff", data_obs["causal_effect"])


if __name__ == "__main__":
    unittest.main()
