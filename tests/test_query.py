"""Tests for graph query, explain, path, and impact algorithms."""

import tempfile
import unittest
from pathlib import Path

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.query import explain_node, find_path, compute_impact


class TestGraphQuery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.store = GraphStore(self.db_path)

        # Build sample graph:
        # file:main.py -> import:auth -> func:login -> class:User
        nodes = [
            Node(id="file:main.py", name="main.py", node_type=NodeType.FILE, path="main.py"),
            Node(id="import:main.py:login", name="login", node_type=NodeType.IMPORT, path="main.py"),
            Node(id="func:auth.py:login", name="login", node_type=NodeType.FUNCTION, path="auth.py", docstring="User login function."),
            Node(id="class:auth.py:User", name="User", node_type=NodeType.CLASS, path="auth.py")
        ]
        edges = [
            Edge(source_id="file:main.py", target_id="import:main.py:login", edge_type=EdgeType.IMPORTS),
            Edge(source_id="import:main.py:login", target_id="func:auth.py:login", edge_type=EdgeType.REFERENCES),
            Edge(source_id="func:auth.py:login", target_id="class:auth.py:User", edge_type=EdgeType.CALLS)
        ]
        self.store.insert_batch(nodes, edges)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_explain_node(self):
        res = explain_node(self.store, "func:auth.py:login")
        self.assertIsNotNone(res)
        self.assertEqual(res["node"]["name"], "login")
        self.assertEqual(res["node"]["docstring"], "User login function.")

        # Check incoming and outgoing
        incoming_ids = [n["id"] for n in res["incoming"]]
        self.assertIn("import:main.py:login", incoming_ids)

        outgoing_ids = [n["id"] for n in res["outgoing"]]
        self.assertIn("class:auth.py:User", outgoing_ids)

    def test_find_path(self):
        path = find_path(self.store, "file:main.py", "class:auth.py:User")
        self.assertIsNotNone(path)
        self.assertEqual(len(path), 4)  # main.py -> import:login -> func:login -> class:User
        self.assertEqual(path[0]["node"]["id"], "file:main.py")
        self.assertEqual(path[-1]["node"]["id"], "class:auth.py:User")

    def test_compute_impact(self):
        res = compute_impact(self.store, "class:auth.py:User")
        self.assertIsNotNone(res)
        self.assertEqual(res["impacted_count"], 3)  # login, import:login, main.py

        impacted_ids = [n["id"] for n in res["impacted"]]
        self.assertIn("func:auth.py:login", impacted_ids)
        self.assertIn("import:main.py:login", impacted_ids)
        self.assertIn("file:main.py", impacted_ids)


if __name__ == "__main__":
    unittest.main()
