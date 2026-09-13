"""Tests for Autonomous AST Patch Engine (DEV-022 / Stage 22)."""

import json
from pathlib import Path
import tempfile
import unittest

from agtoosa.refactor.dead_code import ZombieSymbol
from agtoosa.refactor.decoupler import DecouplingStrategy
from agtoosa.refactor.engine import RefactorEngine, PatchPlan, PatchAction


class TestRefactorEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.engine = RefactorEngine(self.workspace)

        # Create sample target file
        self.sample_file = self.workspace / "sample_service.py"
        self.sample_code = """class UserService:
    def active_method(self):
        return True

    def unused_helper(self):
        # Dead function
        return "deprecated"

    def final_method(self):
        return 42
"""
        self.sample_file.write_text(self.sample_code, encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_dead_code_plan(self):
        zombie = ZombieSymbol(
            node_id="func:sample_service.py:unused_helper",
            name="unused_helper",
            node_type="function",
            path="sample_service.py",
            start_line=5,
            end_line=7,
            confidence="high",
            reason="Zero incoming callers",
            estimated_lines=3,
            safe_to_delete=True,
            deletion_steps=["Remove unused_helper definition"]
        )

        plan = self.engine.create_dead_code_plan([zombie], min_confidence="high")
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].action_type, "DELETE_SYMBOL")
        self.assertEqual(plan.actions[0].file_path, "sample_service.py")
        self.assertEqual(plan.actions[0].symbol_name, "unused_helper")

    def test_dry_run_diff_generation(self):
        zombie = ZombieSymbol(
            node_id="func:sample_service.py:unused_helper",
            name="unused_helper",
            node_type="function",
            path="sample_service.py",
            start_line=5,
            end_line=7,
            confidence="high",
            reason="Zero incoming callers",
            estimated_lines=3,
            safe_to_delete=True,
            deletion_steps=[]
        )

        plan = self.engine.create_dead_code_plan([zombie], min_confidence="high")
        res = self.engine.apply_plan(plan, dry_run=True)

        self.assertEqual(res["status"], "dry_run")
        self.assertEqual(res["files_affected"], 1)
        self.assertIn("sample_service.py", res["diffs"])
        self.assertIn("-    def unused_helper(self):", res["diffs"]["sample_service.py"])

        # Ensure file was not modified on disk
        self.assertEqual(self.sample_file.read_text(encoding="utf-8"), self.sample_code)

    def test_apply_and_rollback(self):
        zombie = ZombieSymbol(
            node_id="func:sample_service.py:unused_helper",
            name="unused_helper",
            node_type="function",
            path="sample_service.py",
            start_line=5,
            end_line=7,
            confidence="high",
            reason="Zero incoming callers",
            estimated_lines=3,
            safe_to_delete=True,
            deletion_steps=[]
        )

        plan = self.engine.create_dead_code_plan([zombie], min_confidence="high")
        apply_res = self.engine.apply_plan(plan, dry_run=False)

        self.assertEqual(apply_res["status"], "applied")
        backup_id = apply_res["backup_id"]

        # Verify file on disk was modified (symbol removed)
        modified_code = self.sample_file.read_text(encoding="utf-8")
        self.assertNotIn("def unused_helper", modified_code)
        self.assertIn("def active_method", modified_code)
        self.assertIn("def final_method", modified_code)

        # Verify backup exists
        backups = self.engine.list_backups()
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0]["plan_id"], backup_id)

        # Roll back
        rolled_back = self.engine.rollback(backup_id)
        self.assertTrue(rolled_back)

        # Verify file content is completely restored
        restored_code = self.sample_file.read_text(encoding="utf-8")
        self.assertEqual(restored_code, self.sample_code)

    def test_create_decouple_plan(self):
        strategy = DecouplingStrategy(
            strategy_type="DEPENDENCY_INVERSION",
            cycle=["A", "B", "A"],
            cut_edge=("A", "B"),
            rationale="Break cycle by inverting B -> A dependency",
            proposed_interface_name="UserServiceProtocol",
            generated_code_stub="class UserServiceProtocol:\n    def active_method(self) -> bool: ...\n",
            refactor_steps=["Inject interface"]
        )

        plan = self.engine.create_decouple_plan(strategy, target_path="interfaces/user_service.py")
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].action_type, "INSERT_INTERFACE")

        apply_res = self.engine.apply_plan(plan, dry_run=False)
        self.assertEqual(apply_res["status"], "applied")

        interface_file = self.workspace / "interfaces" / "user_service.py"
        self.assertTrue(interface_file.exists())
        self.assertIn("class UserServiceProtocol:", interface_file.read_text(encoding="utf-8"))

        # Rollback creation of new file
        self.engine.rollback(apply_res["backup_id"])
        self.assertFalse(interface_file.exists())


if __name__ == "__main__":
    unittest.main()
