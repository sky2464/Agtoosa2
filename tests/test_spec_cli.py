"""Automated tests for DEV-003: Agtoosa Spec CLI Engine and MarkdownDocParser."""

import argparse
import json
from pathlib import Path
import tempfile
import unittest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.parser.doc_parser import MarkdownDocParser
from agtoosa.cli.lifecycle_cmd import cmd_lifecycle_spec
from agtoosa.mcp.server import MCPServer


class TestSpecCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.db_path = self.workspace / ".agtoosa" / "graph.db"
        self.store = GraphStore(self.db_path)

        # Seed sample story nodes
        self.story_1 = Node(
            id="story:DEV-001",
            name="DEV-001: Core Knowledge Graph",
            node_type=NodeType.STORY,
            path="docs/specs/spec-DEV-001.md",
            start_line=1,
            metadata={
                "story_id": "DEV-001",
                "title": "Core Knowledge Graph",
                "status": "✅ Done",
                "milestone": "Milestone 1",
            }
        )
        self.crit_1 = Node(
            id="criterion:DEV-001:AC-1",
            name="DEV-001 AC-1",
            node_type=NodeType.CRITERION,
            path="docs/specs/spec-DEV-001.md",
            start_line=10,
            docstring="Extracts AST symbols into SQLite",
            metadata={"criterion_code": "AC-1"}
        )
        self.task_1 = Node(
            id="task:DEV-001:Task_1",
            name="DEV-001 Task 1.1",
            node_type=NodeType.TASK,
            path="docs/specs/spec-DEV-001.md",
            start_line=20,
            docstring="Implement parser engine",
            metadata={"completed": True}
        )

        edge_crit = Edge(source_id=self.story_1.id, target_id=self.crit_1.id, edge_type=EdgeType.DEFINES)
        edge_task = Edge(source_id=self.story_1.id, target_id=self.task_1.id, edge_type=EdgeType.CONTAINS)

        self.store.insert_batch(
            [self.story_1, self.crit_1, self.task_1],
            [edge_crit, edge_task]
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_spec_all_table_output(self):
        """agtoosa spec all should render formatted table with summary."""
        import io
        from contextlib import redirect_stdout

        args = argparse.Namespace(target="all", json=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_lifecycle_spec(args, self.workspace)

        self.assertEqual(exit_code, 0)
        output = buf.getvalue()
        self.assertIn("SPEC ID", output)
        self.assertIn("DEV-001", output)
        self.assertIn("Core Knowledge Graph", output)
        self.assertIn("✅ Done", output)
        self.assertIn("Summary:", output)

    def test_spec_single_story_inspection(self):
        """agtoosa spec DEV-001 should display detailed acceptance criteria and tasks."""
        import io
        from contextlib import redirect_stdout

        args = argparse.Namespace(target="DEV-001", json=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_lifecycle_spec(args, self.workspace)

        self.assertEqual(exit_code, 0)
        output = buf.getvalue()
        self.assertIn("DEV-001 — Core Knowledge Graph", output)
        self.assertIn("AC-1", output)
        self.assertIn("Extracts AST symbols", output)
        self.assertIn("[x]", output)
        self.assertIn("Task 1.1", output)

    def test_spec_not_found(self):
        """agtoosa spec NON_EXISTENT should exit with code 1."""
        import io
        from contextlib import redirect_stdout

        args = argparse.Namespace(target="DEV-9999", json=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_lifecycle_spec(args, self.workspace)

        self.assertEqual(exit_code, 1)
        self.assertIn("not found", buf.getvalue())

    def test_spec_all_json_mode(self):
        """agtoosa spec all --json should output valid machine-readable JSON."""
        import io
        from contextlib import redirect_stdout

        args = argparse.Namespace(target="all", json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_lifecycle_spec(args, self.workspace)

        self.assertEqual(exit_code, 0)
        data = json.loads(buf.getvalue())
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["story_id"], "DEV-001")
        self.assertEqual(data[0]["criteria_count"], 1)
        self.assertEqual(data[0]["tasks_count"], 1)
        self.assertTrue(data[0]["can_ship"])

    def test_spec_single_json_mode(self):
        """agtoosa spec DEV-001 --json should output single spec dictionary."""
        import io
        from contextlib import redirect_stdout

        args = argparse.Namespace(target="DEV-001", json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_lifecycle_spec(args, self.workspace)

        self.assertEqual(exit_code, 0)
        data = json.loads(buf.getvalue())
        self.assertIsInstance(data, dict)
        self.assertEqual(data["story_id"], "DEV-001")
        self.assertEqual(len(data["criteria"]), 1)
        self.assertEqual(data["criteria"][0]["code"], "AC-1")

    def test_spec_fallback_without_db(self):
        """agtoosa spec should parse docs/specs/*.md on the fly if DB does not exist."""
        import io
        from contextlib import redirect_stdout

        empty_workspace = Path(tempfile.mkdtemp())
        specs_dir = empty_workspace / "docs" / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        (specs_dir / "spec-DEV-099.md").write_text(
            "# Spec: DEV-099 — Live Fallback Engine\n\n"
            "> **Status:** ✅ Done\n\n"
            "- **AC-1 (Live Parsing)**: Parses markdown directly without database.\n"
            "- [x] **Task 1.1**: Direct file discovery\n"
        )

        args = argparse.Namespace(target="all", json=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_lifecycle_spec(args, empty_workspace)

        self.assertEqual(exit_code, 0)
        output = buf.getvalue()
        self.assertIn("DEV-099", output)
        self.assertIn("Live Fallback Engine", output)

    def test_mcp_list_specs_tool(self):
        """MCPServer should handle agtoosa_list_specs tool calls."""
        server = MCPServer(self.workspace)
        resp_json = server.handle_tool_call("agtoosa_list_specs", {"target": "all"})
        data = json.loads(resp_json)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["story_id"], "DEV-001")

    def test_ship_single_story_approved(self):
        """agtoosa ship DEV-001 should verify proof and approve."""
        import io
        from contextlib import redirect_stdout
        from agtoosa.cli.lifecycle_cmd import cmd_lifecycle_ship

        args = argparse.Namespace(story="DEV-001", json=False, strict=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_lifecycle_ship(args, self.workspace)

        self.assertEqual(exit_code, 0)
        output = buf.getvalue()
        self.assertIn("SHIP APPROVED", output)
        self.assertIn("DEV-001", output)

    def test_ship_release_gate_all(self):
        """agtoosa ship all should evaluate all stories in workspace."""
        import io
        from contextlib import redirect_stdout
        from agtoosa.cli.lifecycle_cmd import cmd_lifecycle_ship

        args = argparse.Namespace(story="all", json=False, strict=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_lifecycle_ship(args, self.workspace)

        self.assertEqual(exit_code, 0)
        output = buf.getvalue()
        self.assertIn("Agtoosa Release Gate", output)
        self.assertIn("GATE APPROVED", output)
        self.assertIn("DEV-001", output)

    def test_ship_release_gate_json(self):
        """agtoosa ship all --json should return machine-readable release gate report."""
        import io
        from contextlib import redirect_stdout
        from agtoosa.cli.lifecycle_cmd import cmd_lifecycle_ship

        args = argparse.Namespace(story="all", json=True, strict=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_lifecycle_ship(args, self.workspace)

        self.assertEqual(exit_code, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["gate_passed"])
        self.assertEqual(data["total_stories"], 1)
        self.assertEqual(data["approved_stories"], 1)


class TestMarkdownDocParserParity(unittest.TestCase):
    def test_parse_real_repository_specs(self):
        """Ensure all 34 specification files in docs/specs/ are parsed into stories."""
        repo_root = Path(__file__).resolve().parent.parent
        specs_dir = repo_root / "docs" / "specs"
        if not specs_dir.exists():
            self.skipTest("docs/specs directory not found")

        parser = MarkdownDocParser()
        spec_files = list(specs_dir.glob("*.md"))
        self.assertEqual(len(spec_files), 38)

        story_ids = set()
        for p in spec_files:
            nodes, edges = parser.parse(p, repo_root)
            stories = [n for n in nodes if n.node_type == NodeType.STORY]
            self.assertEqual(len(stories), 1, f"File {p.name} did not parse exactly 1 story node")
            story_ids.add(stories[0].metadata["story_id"])

        self.assertIn("EPIC-001", story_ids)
        self.assertIn("DEV-001", story_ids)
        self.assertIn("DEV-038", story_ids)
        self.assertIn("DEV-039", story_ids)
        self.assertIn("DEV-050", story_ids)
        self.assertIn("DEV-051", story_ids)
        self.assertIn("DEV-052", story_ids)
        self.assertIn("DEV-053", story_ids)
        self.assertIn("DEV-054", story_ids)
        self.assertIn("DEV-055", story_ids)
        self.assertEqual(len(story_ids), 38)


if __name__ == "__main__":
    unittest.main()
