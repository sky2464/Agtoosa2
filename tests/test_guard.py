"""Unit and integration tests for DEV-024: Pre-Push Architectural Daemon & Drift Linter."""

import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest

from agtoosa.cli.main import main
from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.review.guard import ArchitecturalGuard, GuardReport, GuardFinding
from agtoosa.watcher.hooks import get_git_hooks_status, install_git_hooks, remove_git_hooks


class TestArchitecturalGuard(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.db_path = self.workspace / ".agtoosa" / "graph.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.store = GraphStore(self.db_path)
        self.guard = ArchitecturalGuard(self.store, self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_guard_clean_repo(self):
        """A clean repository with no cycles or breaches yields PASSED."""
        n1 = Node(id="func:svc.py:a", name="a", node_type=NodeType.FUNCTION, path="svc.py")
        n2 = Node(id="func:svc.py:b", name="b", node_type=NodeType.FUNCTION, path="svc.py")
        e1 = Edge(source_id="func:svc.py:a", target_id="func:svc.py:b", edge_type=EdgeType.CALLS)
        self.store.insert_batch([n1, n2], [e1])

        report = self.guard.audit()
        self.assertEqual(report.verdict, "PASSED")
        self.assertEqual(len(report.findings), 0)
        self.assertEqual(report.stats["cycles"], 0)
        self.assertEqual(report.stats["layer_violations"], 0)

        # Cache file should be generated
        self.assertTrue(self.guard.status_file_path.exists())
        cached = self.guard.read_status_cache()
        self.assertIsNotNone(cached)
        self.assertEqual(cached["verdict"], "PASSED")

    def test_guard_detects_cycle_and_blocks(self):
        """Circular dependency should be flagged as an ERROR and block."""
        n1 = Node(id="func:svc.py:a", name="a", node_type=NodeType.FUNCTION, path="svc.py")
        n2 = Node(id="func:svc.py:b", name="b", node_type=NodeType.FUNCTION, path="svc.py")
        e1 = Edge(source_id="func:svc.py:a", target_id="func:svc.py:b", edge_type=EdgeType.CALLS)
        e2 = Edge(source_id="func:svc.py:b", target_id="func:svc.py:a", edge_type=EdgeType.CALLS)
        self.store.insert_batch([n1, n2], [e1, e2])

        report = self.guard.audit()
        self.assertEqual(report.verdict, "BLOCKED")
        self.assertTrue(any(f.category == "CYCLE" and f.severity == "ERROR" for f in report.findings))
        self.assertEqual(report.stats["cycles"], 1)

    def test_guard_detects_layer_violation(self):
        """Tier 3 (core) importing Tier 1 (cli) must trigger a LAYER_VIOLATION block."""
        core_node = Node(id="func:agtoosa/core/model.py:init", name="init", node_type=NodeType.FUNCTION, path="agtoosa/core/model.py")
        cli_node = Node(id="func:agtoosa/cli/main.py:run", name="run", node_type=NodeType.FUNCTION, path="agtoosa/cli/main.py")
        bad_edge = Edge(source_id=core_node.id, target_id=cli_node.id, edge_type=EdgeType.IMPORTS)
        self.store.insert_batch([core_node, cli_node], [bad_edge])

        report = self.guard.audit()
        self.assertEqual(report.verdict, "BLOCKED")
        self.assertTrue(any(f.category == "LAYER_VIOLATION" for f in report.findings))

    def test_guard_blast_radius_threshold(self):
        """High blast radius on modified file triggers warning or block under strict mode."""
        # Create base target file node
        target_f = Node(id="file:core.py", name="core.py", node_type=NodeType.FILE, path="core.py")
        nodes = [target_f]
        edges = []

        # Add 6 callers depending on core.py
        for i in range(6):
            c_node = Node(id=f"file:caller_{i}.py", name=f"caller_{i}.py", node_type=NodeType.FILE, path=f"caller_{i}.py")
            nodes.append(c_node)
            edges.append(Edge(source_id=c_node.id, target_id=target_f.id, edge_type=EdgeType.IMPORTS))
        self.store.insert_batch(nodes, edges)

        # Mock changed files
        self.guard._get_changed_files = lambda base_ref=None: ["core.py"]

        # Permissive mode: should yield WARNING
        report = self.guard.audit(max_blast_radius=3, strict=False)
        self.assertEqual(report.verdict, "WARNING")
        self.assertTrue(any(f.category == "BLAST_RADIUS" and f.severity == "WARNING" for f in report.findings))

        # Strict mode: should yield BLOCKED
        report_strict = self.guard.audit(max_blast_radius=3, strict=True)
        self.assertEqual(report_strict.verdict, "BLOCKED")
        self.assertTrue(any(f.category == "BLAST_RADIUS" and f.severity == "ERROR" for f in report_strict.findings))

    def test_guard_daemon_ticks(self):
        """Daemon executes periodic audits and updates cache snapshot."""
        ticks_recorded = []

        def on_tick(rep):
            ticks_recorded.append(rep)

        self.guard.run_daemon(interval=0.01, max_ticks=2, on_tick=on_tick)
        self.assertEqual(len(ticks_recorded), 2)
        self.assertTrue(self.guard.status_file_path.exists())

    def test_guard_cli_direct_and_status(self):
        """CLI invocation of agtoosa guard, --json, and --status."""
        # 1. Clean audit via CLI
        stdout = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = stdout
            code = main(["guard", "--json", "-C", str(self.workspace)])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(code, 0)
        data = json.loads(stdout.getvalue())
        self.assertEqual(data["verdict"], "PASSED")

        # 2. Query --status via CLI
        stdout_status = io.StringIO()
        try:
            sys.stdout = stdout_status
            code = main(["guard", "--status", "--json", "-C", str(self.workspace)])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(code, 0)
        status_data = json.loads(stdout_status.getvalue())
        self.assertEqual(status_data["verdict"], "PASSED")

    def test_guard_hook_installation_and_removal(self):
        """CLI hook installation installs pre-push and removal unlinks it."""
        git_dir = self.workspace / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)

        # Install
        code = main(["guard", "--install-hooks", "-C", str(self.workspace)])
        self.assertEqual(code, 0)

        pre_push = git_dir / "hooks" / "pre-push"
        self.assertTrue(pre_push.exists())
        self.assertIn("agtoosa guard --strict", pre_push.read_text(encoding="utf-8"))
        # Verify executable permission
        self.assertTrue(bool(pre_push.stat().st_mode & stat.S_IXUSR))

        # Status check
        hook_status = get_git_hooks_status(self.workspace)
        self.assertTrue(hook_status.get("pre-push"))

        # Uninstall
        code_un = main(["guard", "--uninstall-hooks", "-C", str(self.workspace)])
        self.assertEqual(code_un, 0)
        self.assertFalse(pre_push.exists())


if __name__ == "__main__":
    unittest.main()
