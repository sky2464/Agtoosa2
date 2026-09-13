"""Automated test suite for VS Code & Cursor Extension (DEV-013)."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from agtoosa import __version__
from agtoosa.cli.main import main
from agtoosa.graph.store import GraphStore
from agtoosa.core.model import Node, Edge, NodeType, EdgeType

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestExtensionManifest(unittest.TestCase):
    """Verify VS Code / Cursor extension manifest validity and configuration."""

    def setUp(self):
        self.pkg_path = REPO_ROOT / "extension" / "package.json"
        self.assertTrue(self.pkg_path.exists())
        with open(self.pkg_path, "r", encoding="utf-8") as f:
            self.pkg = json.load(f)

    def test_extension_version_alignment(self):
        pkg_version = self.pkg.get("version")
        clean_version = __version__.split("-")[0]
        self.assertTrue(
            pkg_version.startswith(clean_pkg_version := clean_version),
            f"Extension package.json version ({pkg_version}) does not match clean package version ({clean_version})"
        )

    def test_extension_contributed_views(self):
        views = self.pkg.get("contributes", {}).get("views", {}).get("agtoosa-sidebar", [])
        view_ids = [v["id"] for v in views]
        self.assertIn("agtoosa.architectureView", view_ids)
        self.assertIn("agtoosa.blastRadiusView", view_ids)
        self.assertIn("agtoosa.driftFindingsView", view_ids)

    def test_extension_contributed_commands(self):
        commands = self.pkg.get("contributes", {}).get("commands", [])
        cmd_ids = [c["command"] for c in commands]
        self.assertIn("agtoosa.rebuildGraph", cmd_ids)
        self.assertIn("agtoosa.openVisualizer", cmd_ids)
        self.assertIn("agtoosa.runReview", cmd_ids)
        self.assertIn("agtoosa.inspectBlastRadius", cmd_ids)
        self.assertIn("agtoosa.rememberRule", cmd_ids)
        self.assertIn("agtoosa.pruneDeadSymbol", cmd_ids)
        self.assertIn("agtoosa.decoupleCycle", cmd_ids)
        self.assertIn("agtoosa.toggleHotspots", cmd_ids)

    def test_extension_configuration(self):
        props = self.pkg.get("contributes", {}).get("configuration", {}).get("properties", {})
        self.assertIn("agtoosa.enableCodeLens", props)
        self.assertIn("agtoosa.enableDiagnostics", props)
        self.assertIn("agtoosa.enableGutterHotspots", props)
        self.assertIn("agtoosa.enableQuickFixRefactoring", props)

    def test_extension_script_syntax(self):
        ext_js = REPO_ROOT / "extension" / "extension.js"
        self.assertTrue(ext_js.exists())
        content = ext_js.read_text(encoding="utf-8")

        self.assertIn("function activate(", content)
        self.assertIn("function deactivate(", content)
        self.assertIn("class AgtoosaCodeLensProvider", content)
        self.assertIn("class AgtoosaArchitectureTreeProvider", content)
        self.assertIn("class AgtoosaBlastRadiusProvider", content)
        self.assertIn("class AgtoosaGutterDecorator", content)
        self.assertIn("class AgtoosaCodeActionProvider", content)

        # If node executable is available, verify syntax
        node_bin = shutil.which("node")
        if node_bin:
            res = subprocess.run([node_bin, "-c", str(ext_js)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"extension.js syntax error: {res.stderr}")

    def test_vsix_packaging_script(self):
        """Verify build_vsix generates a valid OPC/VSIX archive with manifests."""
        import zipfile
        from scripts.build_extension import build_vsix

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir)
            vsix_file = build_vsix(REPO_ROOT, output_dir=out_dir)
            self.assertTrue(vsix_file.exists())
            self.assertTrue(vsix_file.name.startswith("agtoosa-vscode-0.5.0.vsix"))

            with zipfile.ZipFile(vsix_file, "r") as z:
                names = z.namelist()
                self.assertIn("extension.vsixmanifest", names)
                self.assertIn("[Content_Types].xml", names)
                self.assertIn("extension/package.json", names)
                self.assertIn("extension/extension.js", names)
                self.assertIn("extension/resources/hot.svg", names)
                self.assertIn("extension/resources/error.svg", names)
                self.assertIn("extension/resources/cold.svg", names)

                manifest_xml = z.read("extension.vsixmanifest").decode("utf-8")
                self.assertIn('Version="0.5.0"', manifest_xml)
                self.assertIn('Id="agtoosa-vscode"', manifest_xml)


class TestCLISymbolsAndJSONAPI(unittest.TestCase):
    """Test CLI commands consumed by the IDE extension (symbols, explain, impact)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.agtoosa_dir = self.workspace / ".agtoosa"
        self.agtoosa_dir.mkdir()
        self.db_path = self.agtoosa_dir / "graph.db"
        self.store = GraphStore(self.db_path)

        # Insert dummy nodes and edges
        f1 = Node(id="file:src/service.py", name="service.py", node_type=NodeType.FILE, path="src/service.py")
        c1 = Node(id="class:src/service.py:DataService", name="DataService", node_type=NodeType.CLASS, path="src/service.py", start_line=10, end_line=50, docstring="Core data handling service.")
        m1 = Node(id="func:src/service.py:fetch_records", name="fetch_records", node_type=NodeType.FUNCTION, path="src/service.py", start_line=20, end_line=35, docstring="Retrieve records.")
        caller1 = Node(id="func:src/api.py:get_data", name="get_data", node_type=NodeType.FUNCTION, path="src/api.py", start_line=5, end_line=15)

        e1 = Edge(source_id=f1.id, target_id=c1.id, edge_type=EdgeType.CONTAINS, provenance="test")
        e2 = Edge(source_id=c1.id, target_id=m1.id, edge_type=EdgeType.CONTAINS, provenance="test")
        e3 = Edge(source_id=caller1.id, target_id=m1.id, edge_type=EdgeType.CALLS, provenance="test")

        self.store.insert_batch([f1, c1, m1, caller1], [e1, e2, e3])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_graph_symbols_json(self):
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            ret = main(["-C", str(self.workspace), "graph", "symbols", "src/service.py", "--json"])

        self.assertEqual(ret, 0)
        output = f.getvalue()
        symbols = json.loads(output)

        self.assertEqual(len(symbols), 2)
        names = [s["name"] for s in symbols]
        self.assertIn("DataService", names)
        self.assertIn("fetch_records", names)

        fetch_sym = next(s for s in symbols if s["name"] == "fetch_records")
        self.assertEqual(fetch_sym["start_line"], 20)
        self.assertEqual(fetch_sym["end_line"], 35)
        self.assertEqual(fetch_sym["caller_count"], 2)  # called by get_data and contained in DataService
        self.assertIn("get_data", fetch_sym["top_callers"])

    def test_cli_graph_explain_json(self):
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            ret = main(["-C", str(self.workspace), "graph", "explain", "fetch_records", "--json"])

        self.assertEqual(ret, 0)
        output = f.getvalue()
        res = json.loads(output)

        self.assertEqual(res["node"]["name"], "fetch_records")
        self.assertTrue(len(res["incoming"]) > 0)

    def test_cli_graph_impact_json(self):
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            ret = main(["-C", str(self.workspace), "graph", "impact", "fetch_records", "--json"])

        self.assertEqual(ret, 0)
        output = f.getvalue()
        res = json.loads(output)

        self.assertEqual(res["target"]["name"], "fetch_records")
        self.assertTrue(res["impacted_count"] > 0)


if __name__ == "__main__":
    unittest.main()
