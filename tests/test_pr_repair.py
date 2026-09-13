"""Automated test suite for DEV-031: AI Automated PR Repair & Code Review Agent."""

import argparse
import json
from pathlib import Path
import tempfile
import unittest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.repair.agent import PRAgentRepairEngine, RepairIssue, RepairPlan
from agtoosa.cli.lifecycle_cmd import cmd_ci_repair
from agtoosa.mcp.server import MCPServer


class TestPRRepairAgent(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.db_path = self.workspace / ".agtoosa" / "graph.db"
        self.store = GraphStore(self.db_path)

        # Create sample Python source files
        self.src_dir = self.workspace / "app"
        self.src_dir.mkdir(parents=True, exist_ok=True)

        self.file_a = self.src_dir / "service_a.py"
        self.file_a.write_text(
            "class ServiceA:\n"
            "    def call_b(self):\n"
            "        from app.service_b import ServiceB\n"
            "        return ServiceB().do_something()\n"
            "\n"
            "def unused_helper():\n"
            "    return 'dead'\n",
            encoding="utf-8"
        )

        self.file_b = self.src_dir / "service_b.py"
        self.file_b.write_text(
            "class ServiceB:\n"
            "    def call_a(self):\n"
            "        from app.service_a import ServiceA\n"
            "        return ServiceA().call_b()\n"
            "    def do_something(self):\n"
            "        return 'ok'\n",
            encoding="utf-8"
        )

        # Seed graph store
        node_a = Node(id="class:app/service_a.py:ServiceA", name="ServiceA", node_type=NodeType.CLASS, path="app/service_a.py", start_line=1, end_line=4)
        node_dead = Node(id="function:app/service_a.py:unused_helper", name="unused_helper", node_type=NodeType.FUNCTION, path="app/service_a.py", start_line=6, end_line=7)
        node_b = Node(id="class:app/service_b.py:ServiceB", name="ServiceB", node_type=NodeType.CLASS, path="app/service_b.py", start_line=1, end_line=6)

        edge_ab = Edge(source_id=node_a.id, target_id=node_b.id, edge_type=EdgeType.CALLS)
        edge_ba = Edge(source_id=node_b.id, target_id=node_a.id, edge_type=EdgeType.CALLS)

        self.store.insert_batch([node_a, node_dead, node_b], [edge_ab, edge_ba])
        self.engine = PRAgentRepairEngine(self.store, self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_diagnose_architectural_issues(self):
        """Verify PRAgentRepairEngine diagnoses circular dependencies and dead code."""
        issues = self.engine.diagnose()
        self.assertGreaterEqual(len(issues), 2)

        types = [i.issue_type for i in issues]
        self.assertIn("circular_dependency", types)
        self.assertIn("dead_code", types)

        cycle_issue = next(i for i in issues if i.issue_type == "circular_dependency")
        self.assertEqual(cycle_issue.suggested_action, "decouple_interface")
        self.assertEqual(cycle_issue.severity, "ERROR")

        dead_issue = next(i for i in issues if i.issue_type == "dead_code")
        self.assertEqual(dead_issue.suggested_action, "prune_symbol")

    def test_synthesize_cycle_repair(self):
        """Verify synthesis of decoupling interface plan for circular dependencies."""
        cycle_issue = RepairIssue(
            issue_id="test_cycle",
            issue_type="circular_dependency",
            severity="ERROR",
            symbols=["class:app/service_a.py:ServiceA", "class:app/service_b.py:ServiceB"],
            description="Circular call between ServiceA and ServiceB",
            suggested_action="decouple_interface"
        )

        plan = self.engine.synthesize_repair(cycle_issue)
        self.assertIsNotNone(plan)
        self.assertIn("Decoupling Interface Protocol", plan.description)
        self.assertGreaterEqual(len(plan.diff), 1)

    def test_synthesize_and_verify_dead_code_repair(self):
        """Verify automated pruning of dead code with atomic backup."""
        dead_issue = RepairIssue(
            issue_id="test_dead",
            issue_type="dead_code",
            severity="WARNING",
            symbols=["function:app/service_a.py:unused_helper"],
            description="Dead code unused_helper in service_a.py",
            suggested_action="prune_symbol"
        )

        plan = self.engine.synthesize_repair(dead_issue)
        self.assertIsNotNone(plan)
        self.assertIn("unused_helper", plan.description)

        # Apply repair
        res = self.engine.apply_and_verify(plan, dry_run=False)
        self.assertTrue(res["success"])
        self.assertTrue(plan.verified)
        self.assertIsNotNone(plan.backup_id)

        # Verify file on disk had unused_helper removed
        updated_content = self.file_a.read_text(encoding="utf-8")
        self.assertNotIn("def unused_helper", updated_content)
        self.assertIn("class ServiceA", updated_content)

    def test_auto_rollback_on_verification_failure(self):
        """Verify atomic rollback restores original file when post-repair invariants fail."""
        dead_issue = RepairIssue(
            issue_id="test_rollback",
            issue_type="dead_code",
            severity="WARNING",
            symbols=["function:app/service_a.py:unused_helper"],
            description="Dead code test",
            suggested_action="prune_symbol"
        )
        plan = self.engine.synthesize_repair(dead_issue)
        self.assertIsNotNone(plan)

        # Mock guard to fail invariants post-repair
        original_audit = self.engine.guard.audit
        self.engine.guard.audit = lambda base_ref=None: {
            "clean": False,
            "findings": [{"rule": "circular_dependency", "cycle": plan.issue.symbols}]
        }

        # Force issue_type to circular_dependency to trigger check
        plan.issue.issue_type = "circular_dependency"

        res = self.engine.apply_and_verify(plan, dry_run=False)
        self.assertFalse(res["success"])
        self.assertTrue(res["rolled_back"])

        # Check original file content is restored
        content = self.file_a.read_text(encoding="utf-8")
        self.assertIn("def unused_helper", content)

        # Restore guard
        self.engine.guard.audit = original_audit

    def test_cli_ci_repair(self):
        """Test 'agtoosa ci repair' CLI entrypoint."""
        args = argparse.Namespace(
            command="ci",
            ci_action="repair",
            base=None,
            apply=False,
            dry_run=True,
            branch=None,
            json=True
        )
        rc = cmd_ci_repair(args, self.workspace)
        self.assertEqual(rc, 0)

    def test_mcp_auto_repair_tool(self):
        """Test 'agtoosa_auto_repair_pr' MCP tool call."""
        server = MCPServer(self.workspace)
        tool_defs = server.get_tool_definitions()
        repair_tool = next((t for t in tool_defs if t["name"] == "agtoosa_auto_repair_pr"), None)
        self.assertIsNotNone(repair_tool)

        res_json = server.handle_tool_call("agtoosa_auto_repair_pr", {"dry_run": True})
        data = json.loads(res_json)
        self.assertIn("status", data)
        self.assertIn("repairs", data)
        self.assertGreaterEqual(data["total_issues"], 1)


if __name__ == "__main__":
    unittest.main()
