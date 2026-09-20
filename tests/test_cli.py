"""Tests for CLI entrypoint and commands."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure repository root is on sys.path if run directly as a script
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agtoosa.cli.main import main


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

        # Create a sample file in workspace
        sample = self.workspace / "service.py"
        sample.write_text(
            '''def start_service():
    """Start the background service."""
    return True
''',
            encoding="utf-8"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_build_and_status(self):
        # Build graph
        ret = main(["-C", str(self.workspace), "graph", "build"])
        self.assertEqual(ret, 0)

        # Verify DB exists
        db_path = self.workspace / ".agtoosa" / "graph.db"
        self.assertTrue(db_path.exists())

        # Check status
        ret = main(["-C", str(self.workspace), "graph", "status"])
        self.assertEqual(ret, 0)

    def test_cli_query(self):
        main(["-C", str(self.workspace), "graph", "build"])
        ret = main(["-C", str(self.workspace), "graph", "query", "start_service"])
        self.assertEqual(ret, 0)

    def test_cli_export(self):
        main(["-C", str(self.workspace), "graph", "build"])
        out_file = self.workspace / "out.json"
        ret = main(["-C", str(self.workspace), "graph", "export", "-o", str(out_file)])
        self.assertEqual(ret, 0)
        self.assertTrue(out_file.exists())

        data = json.loads(out_file.read_text(encoding="utf-8"))
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertIn("stats", data)

    def test_cli_explain_and_impact(self):
        main(["-C", str(self.workspace), "graph", "build"])
        ret_explain = main(["-C", str(self.workspace), "graph", "explain", "start_service"])
        self.assertEqual(ret_explain, 0)

        ret_impact = main(["-C", str(self.workspace), "graph", "impact", "start_service"])
        self.assertEqual(ret_impact, 0)

    def test_cli_path(self):
        client = self.workspace / "client.py"
        client.write_text(
            '''from service import start_service
def run_client():
    start_service()
''',
            encoding="utf-8"
        )
        main(["-C", str(self.workspace), "graph", "build"])
        ret = main(["-C", str(self.workspace), "graph", "path", "run_client", "start_service"])
        self.assertEqual(ret, 0)

    def test_cli_context_review_ship(self):
        spec = self.workspace / "spec-DEV-001.md"
        spec.write_text(
            '''# Spec: DEV-001 — Core Foundation

- **AC-1 (Foundational)**: System SHALL bootstrap service.

### Tasks
- [x] **Task 1.1**: Initialize service.
''',
            encoding="utf-8"
        )
        main(["-C", str(self.workspace), "graph", "build"])

        # Context compile
        ret_ctx = main(["-C", str(self.workspace), "context", "compile", "DEV-001"])
        self.assertEqual(ret_ctx, 0)

        # Review
        ret_rev = main(["-C", str(self.workspace), "review"])
        self.assertEqual(ret_rev, 0)

        # Ship
        ret_ship = main(["-C", str(self.workspace), "ship", "DEV-001"])
        self.assertEqual(ret_ship, 0)

    def test_cli_view_and_report_and_export_formats(self):
        main(["-C", str(self.workspace), "graph", "build"])

        # View
        html_out = self.workspace / "view.html"
        ret_view = main(["-C", str(self.workspace), "graph", "view", "-o", str(html_out)])
        self.assertEqual(ret_view, 0)
        self.assertTrue(html_out.exists())

        # Report (text and markdown)
        rep_out = self.workspace / "report.md"
        ret_rep = main(["-C", str(self.workspace), "graph", "report", "-f", "markdown", "-o", str(rep_out)])
        self.assertEqual(ret_rep, 0)
        self.assertTrue(rep_out.exists())

        # Export dot
        dot_out = self.workspace / "graph.dot"
        ret_dot = main(["-C", str(self.workspace), "graph", "export", "-f", "dot", "-o", str(dot_out)])
        self.assertEqual(ret_dot, 0)
        self.assertTrue(dot_out.exists())

        # Export graphml
        gml_out = self.workspace / "graph.graphml"
        ret_gml = main(["-C", str(self.workspace), "graph", "export", "-f", "graphml", "-o", str(gml_out)])
        self.assertEqual(ret_gml, 0)
        self.assertTrue(gml_out.exists())

    def test_cli_view_serve_strict_port_conflict(self):
        import socket
        main(["-C", str(self.workspace), "graph", "build"])

        # Bind an ephemeral socket to make port busy
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        busy_port = sock.getsockname()[1]

        try:
            # Using strict-port should fail cleanly with return code 1
            ret = main(["-C", str(self.workspace), "graph", "view", "--serve", "--strict-port", "--port", str(busy_port)])
            self.assertEqual(ret, 1)
        finally:
            sock.close()

    def test_cli_update_command_dispatch(self):
        # Verify update and upgrade are registered parsers
        with self.assertRaises(SystemExit) as cm:
            main(["update", "--help"])
        self.assertEqual(cm.exception.code, 0)

        with self.assertRaises(SystemExit) as cm:
            main(["upgrade", "--help"])
        self.assertEqual(cm.exception.code, 0)


if __name__ == "__main__":
    unittest.main()


