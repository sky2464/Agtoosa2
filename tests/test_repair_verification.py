"""Tests for DEV-044: Verified Repair and Conservative Dead-Code Actions."""

import tempfile
import sys
from pathlib import Path
import pytest

from agtoosa.graph.store import GraphStore
from agtoosa.parser import ParserEngine
from agtoosa.repair.agent import PRAgentRepairEngine, RepairIssue, RepairPlan
from agtoosa.refactor.engine import PatchPlan, PatchAction


def test_dry_run_is_conservative_preview():
    """Verify dry runs return verified: False (R-10 / AC-14)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        db_path = workspace / ".agtoosa" / "graph.db"
        db_path.parent.mkdir(parents=True)
        store = GraphStore(db_path)
        engine = PRAgentRepairEngine(store, workspace)

        plan = RepairPlan(
            plan_id="plan-test",
            issue=RepairIssue("iss-1", "dead_code", "WARNING", ["sym1"], "Dead code", "prune"),
            description="Test plan",
            diff="--- a/test.py\n+++ b/test.py",
            files_modified=["test.py"],
            underlying_plan=PatchPlan("patch-1", "Test patch", [
                PatchAction("DELETE_SYMBOL", "test.py", "sym1", 1, 5, "")
            ]),
        )

        result = engine.apply_and_verify(plan, dry_run=True)
        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["verified"] is False  # Must not claim verified on dry run


def test_stale_source_detection_aborts_apply():
    """Verify source hash mismatch aborts application without touching files (AC-14)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        db_path = workspace / ".agtoosa" / "graph.db"
        db_path.parent.mkdir(parents=True)
        store = GraphStore(db_path)
        engine = PRAgentRepairEngine(store, workspace)

        test_file = workspace / "test.py"
        test_file.write_text("x = 1\n")

        # Plan synthesized when content was 'x = 1\n' (hash recorded)
        import hashlib
        orig_hash = hashlib.sha256(b"x = 1\n").hexdigest()

        plan = RepairPlan(
            plan_id="plan-test",
            issue=RepairIssue("iss-1", "dead_code", "WARNING", ["sym1"], "Dead code", "prune"),
            description="Test plan",
            diff="diff",
            files_modified=["test.py"],
            source_hashes={"test.py": orig_hash},
            underlying_plan=PatchPlan("patch-1", "Test patch", [
                PatchAction("DELETE_SYMBOL", "test.py", "sym1", 1, 1, "")
            ]),
        )

        # File changes before apply
        test_file.write_text("x = 2 # modified\n")

        result = engine.apply_and_verify(plan, dry_run=False)
        assert result["success"] is False
        assert result["stale"] is True
        assert result["verified"] is False
        # File should remain untouched
        assert test_file.read_text() == "x = 2 # modified\n"


def test_verification_command_failure_triggers_rollback():
    """Verify failed verification command rolls back patch and graph state (AC-16)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        db_path = workspace / ".agtoosa" / "graph.db"
        db_path.parent.mkdir(parents=True)
        store = GraphStore(db_path)
        engine = PRAgentRepairEngine(store, workspace)

        test_file = workspace / "test.py"
        original_content = "def keeper():\n    return 42\n"
        test_file.write_text(original_content)

        import hashlib
        orig_hash = hashlib.sha256(original_content.encode("utf-8")).hexdigest()

        plan = RepairPlan(
            plan_id="plan-test",
            issue=RepairIssue("iss-1", "dead_code", "WARNING", ["keeper"], "Dead code", "prune"),
            description="Test plan",
            diff="diff",
            files_modified=["test.py"],
            source_hashes={"test.py": orig_hash},
            underlying_plan=PatchPlan("patch-1", "Test patch", [
                PatchAction("INSERT_INTERFACE", "test.py", "broken", 2, 2, "syntax error here !!!")
            ]),
        )

        # Run with a failing verification command (e.g. exit 1)
        failing_cmd = [sys.executable, "-c", "import sys; sys.exit(1)"]
        result = engine.apply_and_verify(plan, dry_run=False, verification_commands=[failing_cmd])

        assert result["success"] is False
        assert result["rolled_back"] is True
        assert result["verified"] is False
        # Content was restored
        assert test_file.read_text() == original_content
