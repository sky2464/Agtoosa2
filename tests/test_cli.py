"""Tests for CLI entrypoint and commands."""

import json
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
