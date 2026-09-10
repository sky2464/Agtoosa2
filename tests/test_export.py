"""Tests for multi-format graph exporter (JSON, Obsidian, GraphML, Cypher, DOT)."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.export import MultiFormatExporter


class TestExport(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.store = GraphStore(self.db_path)

        nodes = [
            Node(id="class:auth:User", name="User", node_type=NodeType.CLASS, path="auth.py", docstring="User model."),
            Node(id="func:auth:login", name="login", node_type=NodeType.FUNCTION, path="auth.py", docstring="Login helper.")
        ]
        edges = [
            Edge(source_id="func:auth:login", target_id="class:auth:User", edge_type=EdgeType.CALLS)
        ]
        self.store.insert_batch(nodes, edges)
        self.exporter = MultiFormatExporter(self.store)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_json_export(self):
        out_str = self.exporter.to_json()
        data = json.loads(out_str)
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertEqual(len(data["nodes"]), 2)

    def test_obsidian_export(self):
        vault_dir = Path(self.temp_dir.name) / "vault"
        msg = self.exporter.to_obsidian_vault(vault_dir)
        self.assertTrue(vault_dir.exists())
        self.assertTrue((vault_dir / "Index.md").exists())

        # Check that note files are created with wikilinks
        files = list(vault_dir.glob("*.md"))
        self.assertGreaterEqual(len(files), 3)  # User, login, Index.md

        login_note = next(f for f in files if "login" in f.name)
        content = login_note.read_text(encoding="utf-8")
        self.assertIn("[[", content)
        self.assertIn("User", content)

    def test_graphml_export(self):
        xml_str = self.exporter.to_graphml()
        self.assertIn("<graphml", xml_str)
        self.assertIn('id="AgtoosaGraph"', xml_str)

        # Verify valid XML
        root = ET.fromstring(xml_str)
        self.assertIsNotNone(root)

    def test_cypher_export(self):
        cypher_str = self.exporter.to_cypher()
        self.assertIn("CREATE CONSTRAINT", cypher_str)
        self.assertIn("MERGE (n:Node:Class", cypher_str)
        self.assertIn("MERGE (n:Node:Function", cypher_str)
        self.assertIn("-[:CALLS", cypher_str)

    def test_dot_export(self):
        dot_str = self.exporter.to_dot()
        self.assertIn("digraph Agtoosa2Graph", dot_str)
        self.assertIn('"func:auth:login"', dot_str)
        self.assertIn("->", dot_str)

    def test_export_file_dispatch(self):
        out_file = Path(self.temp_dir.name) / "out.graphml"
        self.exporter.export("graphml", output_path=out_file)
        self.assertTrue(out_file.exists())
        self.assertGreater(out_file.stat().st_size, 100)


if __name__ == "__main__":
    unittest.main()
