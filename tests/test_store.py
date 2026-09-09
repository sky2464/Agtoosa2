"""Tests for SQLite graph store."""

import tempfile
import unittest
from pathlib import Path

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore


class TestGraphStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_graph.db"
        self.store = GraphStore(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_schema_initialization(self):
        self.assertTrue(self.db_path.exists())
        stats = self.store.get_stats()
        self.assertEqual(stats.total_nodes, 0)
        self.assertEqual(stats.total_edges, 0)

    def test_insert_and_query_fts(self):
        nodes = [
            Node(
                id="file:app.py",
                name="app.py",
                node_type=NodeType.FILE,
                path="app.py",
                docstring="Main application module for auth."
            ),
            Node(
                id="func:app.py:login",
                name="login",
                node_type=NodeType.FUNCTION,
                path="app.py",
                start_line=10,
                end_line=25,
                docstring="Authenticate user credentials."
            )
        ]
        edges = [
            Edge(
                source_id="file:app.py",
                target_id="func:app.py:login",
                edge_type=EdgeType.CONTAINS
            )
        ]

        self.store.insert_batch(nodes, edges)
        stats = self.store.get_stats()
        self.assertEqual(stats.total_nodes, 2)
        self.assertEqual(stats.total_edges, 1)

        # FTS query matching function name
        results = self.store.query_fts("login")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "login")
        self.assertEqual(results[0]["start_line"], 10)

        # FTS query matching docstring
        results = self.store.query_fts("credentials")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "login")

    def test_neighbors_traversal(self):
        nodes = [
            Node(id="class:User", name="User", node_type=NodeType.CLASS, path="models.py"),
            Node(id="func:save", name="save", node_type=NodeType.FUNCTION, path="models.py")
        ]
        edges = [
            Edge(source_id="class:User", target_id="func:save", edge_type=EdgeType.CONTAINS)
        ]
        self.store.insert_batch(nodes, edges)

        out_neighbors = self.store.get_neighbors("class:User", direction="out")
        self.assertEqual(len(out_neighbors), 1)
        self.assertEqual(out_neighbors[0]["id"], "func:save")

        in_neighbors = self.store.get_neighbors("func:save", direction="in")
        self.assertEqual(len(in_neighbors), 1)
        self.assertEqual(in_neighbors[0]["id"], "class:User")


if __name__ == "__main__":
    unittest.main()
