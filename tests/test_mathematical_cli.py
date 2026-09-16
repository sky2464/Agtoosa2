"""Tests for Mathematical & Formal Invariants CLI commands (DEV-052, DEV-054, DEV-055)."""

import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from agtoosa.cli.main import main


class TestMathematicalCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)

        # Create module A
        mod_a = self.workspace / "mod_a.py"
        mod_a.write_text(
            '''import mod_b

def func_a():
    """Function A calls B."""
    return mod_b.func_b()
''',
            encoding="utf-8"
        )

        # Create module B
        mod_b = self.workspace / "mod_b.py"
        mod_b.write_text(
            '''def func_b():
    """Function B."""
    return 42
''',
            encoding="utf-8"
        )

        # Build graph
        ret = main(["-C", str(self.workspace), "graph", "build"])
        self.assertEqual(ret, 0)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _run_cli(self, args: list) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["-C", str(self.workspace)] + args)
        return ret, buf.getvalue()

    def test_spectral_cli_json(self):
        # 1. Full spectral report
        ret, out = self._run_cli(["graph", "spectral", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(out)
        self.assertIn("algebraic_connectivity", data)
        self.assertIn("cheeger_conductance", data)
        self.assertIn("spectral_radius", data)
        self.assertIn("von_neumann_entropy", data)
        self.assertIn("feedback_arc_count", data)

        # 2. Spectral cut
        ret, out = self._run_cli(["graph", "spectral", "--cut", "--json"])
        self.assertEqual(ret, 0)
        cut_data = json.loads(out)
        self.assertIn("cheeger_conductance", cut_data)
        self.assertIn("cut_partition", cut_data)

        # 3. Spectral radius
        ret, out = self._run_cli(["graph", "spectral", "--radius", "--json"])
        self.assertEqual(ret, 0)
        rad_data = json.loads(out)
        self.assertIn("spectral_radius", rad_data)
        self.assertIn("epidemic_threshold", rad_data)

        # 4. Minimum Feedback Arc Set
        ret, out = self._run_cli(["graph", "spectral", "--fas", "--json"])
        self.assertEqual(ret, 0)
        fas_data = json.loads(out)
        self.assertIn("feedback_arcs", fas_data)
        self.assertIn("feedback_arc_count", fas_data)

        # 5. Transitive reduction
        ret, out = self._run_cli(["graph", "spectral", "--transitive", "--json"])
        self.assertEqual(ret, 0)
        trans_data = json.loads(out)
        self.assertIn("essential_edge_count", trans_data)

    def test_spectral_cli_text(self):
        ret, out = self._run_cli(["graph", "spectral"])
        self.assertEqual(ret, 0)
        self.assertIn("Algebraic Connectivity", out)
        self.assertIn("Cheeger Conductance", out)
        self.assertIn("Von Neumann Graph Entropy", out)

    def test_curvature_cli_json_and_text(self):
        # Text output
        ret, out = self._run_cli(["graph", "curvature", "--hyperbolic"])
        self.assertEqual(ret, 0)
        self.assertIn("Forman-Ricci Curvature", out)
        self.assertIn("Gromov", out)

        # JSON output
        ret, out = self._run_cli(["graph", "curvature", "--top", "5", "--hyperbolic", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(out)
        self.assertIn("total_edges", data)
        self.assertIn("average_curvature", data)
        self.assertIn("top_bottlenecks", data)
        self.assertIn("hyperbolicity", data)

    def test_telemetry_causal_cli(self):
        # Create a mock contingency dataset
        data_file = self.workspace / "contingency.json"
        data_file.write_text(
            json.dumps([
                {"func_a": 1, "func_b": 1},
                {"func_a": 1, "func_b": 1},
                {"func_a": 0, "func_b": 0},
                {"func_a": 0, "func_b": 1},
            ]),
            encoding="utf-8"
        )

        # 1. Causal CLI with text
        ret, out = self._run_cli(["telemetry", "causal", "--source", "func_a", "--target", "func_b", "--data", str(data_file)])
        self.assertEqual(ret, 0)
        self.assertIn("Causal Architecture Inference", out)
        self.assertIn("Back-Door Admissible", out)
        self.assertIn("Average Causal Effect", out)

        # 2. Causal CLI with JSON
        ret, out = self._run_cli(["telemetry", "causal", "--source", "func_a", "--target", "func_b", "--data", str(data_file), "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(out)
        self.assertIn("source", data)
        self.assertIn("target", data)
        self.assertTrue(data["is_admissible"])
        self.assertIn("causal_effect", data)
        self.assertIn("average_causal_effect", data["causal_effect"])


if __name__ == "__main__":
    unittest.main()
