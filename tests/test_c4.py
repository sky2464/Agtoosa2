"""Automated test suite for DEV-028: Automated C4 Architecture-as-Code & Live Diagram Sync."""

import argparse
import json
from pathlib import Path
import tempfile
import unittest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.c4.generator import C4DiagramGenerator, C4Level, C4Format
from agtoosa.c4.sync import C4SyncManager
from agtoosa.cli.c4_cmd import cmd_c4
from agtoosa.mcp.server import MCPServer


class TestC4Architecture(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.db_path = self.workspace / ".agtoosa" / "graph.db"
        self.store = GraphStore(self.db_path)
        self.generator = C4DiagramGenerator(self.store, self.workspace)
        self.sync_mgr = C4SyncManager(self.store, self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_c4_context_mermaid(self):
        """Verify Level 1 System Context diagram generation in Mermaid syntax."""
        diagram = self.generator.generate(level=C4Level.CONTEXT, format_type=C4Format.MERMAID)
        self.assertIn("C4Context", diagram)
        self.assertIn('Person(developer, "Developer / Engineer"', diagram)
        self.assertIn('System(agtoosa, "Agtoosa Knowledge Engine"', diagram)
        self.assertIn('System_Ext(github, "GitHub / Git Remote"', diagram)
        self.assertIn('Rel(developer, agtoosa', diagram)

    def test_generate_c4_container_plantuml(self):
        """Verify Level 2 Container diagram generation in PlantUML syntax."""
        diagram = self.generator.generate(level=C4Level.CONTAINER, format_type=C4Format.PLANTUML)
        self.assertIn("@startuml", diagram)
        self.assertIn("!include <C4/C4_Container>", diagram)
        self.assertIn('Container(cli, "CLI Subsystem"', diagram)
        self.assertIn('Container(mcp, "Native MCP Server"', diagram)
        self.assertIn('ContainerDb(db, "Knowledge Graph DB"', diagram)
        self.assertIn("@enduml", diagram)

    def test_generate_c4_component_structurizr(self):
        """Verify Level 3 Component diagram generation in Structurizr DSL syntax."""
        diagram = self.generator.generate(level=C4Level.COMPONENT, format_type=C4Format.STRUCTURIZR)
        self.assertIn("workspace", diagram)
        self.assertIn("model {", diagram)
        self.assertIn('softwareSystem "Agtoosa Knowledge Engine"', diagram)
        self.assertIn("views {", diagram)

    def test_c4_with_discovered_services_and_topics(self):
        """Verify dynamic inclusion of discovered microservices and message topics in C4 diagrams."""
        svc = Node(id="service:payment-svc", name="payment-svc", node_type=NodeType.SERVICE, path="runtime://services/payment-svc")
        top = Node(id="topic:orders.v1", name="orders.v1", node_type=NodeType.TOPIC, path="app/events.py", metadata={"broker": "kafka"})
        self.store.insert_batch([svc, top], [])

        diagram = self.generator.generate(level=C4Level.CONTAINER, format_type=C4Format.MERMAID)
        self.assertIn("payment_svc", diagram)
        self.assertIn("orders_v1", diagram)

    def test_live_docs_marker_sync(self):
        """Test in-place replacement of C4 diagram blocks in Markdown documentation."""
        doc_path = self.workspace / "architecture.md"
        doc_path.write_text(
            "# Architecture\n\n"
            "<!-- agtoosa-c4-start:container -->\n"
            "Old diagram content here\n"
            "<!-- agtoosa-c4-end:container -->\n\n"
            "More docs here...\n",
            encoding="utf-8"
        )

        res = self.sync_mgr.sync_file(doc_path, format_type=C4Format.MERMAID, check_only=False)
        self.assertTrue(res["has_drift"])
        self.assertTrue(res["updated"])

        new_text = doc_path.read_text(encoding="utf-8")
        self.assertIn("```mermaid", new_text)
        self.assertIn("C4Container", new_text)
        self.assertNotIn("Old diagram content here", new_text)

        # Running again with check_only=True should report zero drift
        check_res = self.sync_mgr.sync_file(doc_path, format_type=C4Format.MERMAID, check_only=True)
        self.assertFalse(check_res["has_drift"])

    def test_sync_check_ci_drift(self):
        """Test CI drift detection on directory sync."""
        arch_dir = self.workspace / "docs" / "architecture"

        # Initially, files don't exist -> drift detected in check mode
        res_initial = self.sync_mgr.sync_directory(arch_dir, check_only=True)
        self.assertFalse(res_initial["in_sync"])
        self.assertGreaterEqual(res_initial["total_drifts"], 1)

        # Now sync files to disk
        res_sync = self.sync_mgr.sync_directory(arch_dir, check_only=False)
        self.assertFalse(res_sync["check_only"])
        self.assertTrue((arch_dir / "c4-container.mmd").exists())

        # Checking again should be 100% in sync
        res_clean = self.sync_mgr.sync_directory(arch_dir, check_only=True)
        self.assertTrue(res_clean["in_sync"])
        self.assertEqual(res_clean["total_drifts"], 0)

    def test_cli_c4_commands(self):
        """Test 'agtoosa c4 export' and 'agtoosa c4 sync' CLI entrypoints."""
        # 1. Export CLI command
        out_file = self.workspace / "exported.mmd"
        args_export = argparse.Namespace(
            command="c4",
            c4_action="export",
            level="context",
            format="mermaid",
            output=str(out_file)
        )
        rc_export = cmd_c4(args_export, self.workspace)
        self.assertEqual(rc_export, 0)
        self.assertTrue(out_file.exists())
        self.assertIn("C4Context", out_file.read_text(encoding="utf-8"))

        # 2. Sync CLI command
        target_dir = self.workspace / "docs" / "c4"
        args_sync = argparse.Namespace(
            command="c4",
            c4_action="sync",
            dir=str(target_dir),
            format="mermaid",
            check=False,
            json=False
        )
        rc_sync = cmd_c4(args_sync, self.workspace)
        self.assertEqual(rc_sync, 0)

        # 3. Check CLI command (should pass)
        args_check = argparse.Namespace(
            command="c4",
            c4_action="sync",
            dir=str(target_dir),
            format="mermaid",
            check=True,
            json=True
        )
        rc_check = cmd_c4(args_check, self.workspace)
        self.assertEqual(rc_check, 0)

    def test_mcp_c4_tool(self):
        """Test 'agtoosa_get_c4_diagram' MCP tool call."""
        server = MCPServer(self.workspace)
        tool_defs = server.get_tool_definitions()
        c4_tool = next((t for t in tool_defs if t["name"] == "agtoosa_get_c4_diagram"), None)
        self.assertIsNotNone(c4_tool)

        res_json = server.handle_tool_call("agtoosa_get_c4_diagram", {
            "level": "container",
            "format": "mermaid"
        })
        data = json.loads(res_json)
        self.assertEqual(data["level"], "container")
        self.assertEqual(data["format"], "mermaid")
        self.assertIn("C4Container", data["diagram"])


if __name__ == "__main__":
    unittest.main()
