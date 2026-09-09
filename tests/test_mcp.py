"""Tests for native Model Context Protocol (MCP) Server."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure repository root is on sys.path if run directly as a script
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agtoosa.core.model import Node, NodeType
from agtoosa.graph.store import GraphStore
from agtoosa.mcp.server import MCPServer


class TestMCPServer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / ".agtoosa" / "graph.db"
        self.store = GraphStore(self.db_path)

        # Seed test node
        node = Node(
            id="func:compute",
            name="compute",
            node_type=NodeType.FUNCTION,
            path="calc.py",
            start_line=5,
            docstring="Perform calculation"
        )
        self.store.insert_batch([node], [])
        self.server = MCPServer(self.root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initialize(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        resp = self.server.handle_message(req)
        self.assertIsNotNone(resp)
        assert resp is not None
        self.assertEqual(resp["id"], 1)
        self.assertIn("serverInfo", resp["result"])
        self.assertEqual(resp["result"]["serverInfo"]["name"], "agtoosa-mcp")

    def test_tools_list(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        resp = self.server.handle_message(req)
        self.assertIsNotNone(resp)
        assert resp is not None
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("agtoosa_search_graph", tool_names)
        self.assertIn("agtoosa_get_symbol", tool_names)
        self.assertIn("agtoosa_query_impact", tool_names)
        self.assertIn("agtoosa_get_task_context", tool_names)
        self.assertIn("agtoosa_verify_ship", tool_names)

    def test_tool_call_search(self):
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "agtoosa_search_graph",
                "arguments": {"query": "compute"}
            }
        }
        resp = self.server.handle_message(req)
        self.assertIsNotNone(resp)
        assert resp is not None
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "compute")

    def test_tool_call_get_symbol(self):
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "agtoosa_get_symbol",
                "arguments": {"symbol": "compute"}
            }
        }
        resp = self.server.handle_message(req)
        self.assertIsNotNone(resp)
        assert resp is not None
        content = resp["result"]["content"][0]["text"]
        data = json.loads(content)
        self.assertEqual(data["node"]["name"], "compute")
        self.assertEqual(data["node"]["docstring"], "Perform calculation")


if __name__ == "__main__":
    unittest.main()
