"""Automated verification suite for Standalone Binary Packaging & Multi-Platform Distribution (DEV-012)."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from agtoosa import __version__
from agtoosa.cli.main import main
from scripts.build_standalone import (
    compute_sha256,
    create_release_archive,
    detect_target_platform,
    get_archive_name,
)
from scripts.generate_homebrew_formula import (
    generate_formula,
    parse_checksums_from_dir,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestDistributionManifests(unittest.TestCase):
    """Test project metadata, version consistency, and distribution entrypoints."""

    def test_version_synchronization_across_project(self):
        """Verify version strings match across pyproject.toml, package, and docs."""
        pyproject_path = REPO_ROOT / "pyproject.toml"
        self.assertTrue(pyproject_path.exists())

        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        toml_version = pyproject_data["project"]["version"]
        self.assertEqual(
            toml_version,
            __version__,
            f"pyproject.toml version ({toml_version}) does not match agtoosa.__version__ ({__version__})"
        )

        # Check MCP server version
        from agtoosa.mcp.server import MCPServer
        server = MCPServer(REPO_ROOT)
        init_resp = server.handle_message({"id": 1, "method": "initialize", "params": {}})
        assert init_resp is not None
        server_version = init_resp["result"]["serverInfo"]["version"]
        clean_pkg_version = __version__.split("-")[0]
        self.assertTrue(
            server_version.startswith(clean_pkg_version),
            f"MCPServer version ({server_version}) does not match clean package version ({clean_pkg_version})"
        )

    def test_pyproject_zero_runtime_dependencies(self):
        """Agtoosa core must maintain zero required runtime dependencies."""
        pyproject_path = REPO_ROOT / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        self.assertEqual(data["project"]["dependencies"], [])
        self.assertEqual(data["project"]["scripts"]["agtoosa"], "agtoosa.cli.main:main")
        self.assertEqual(data["project"]["requires-python"], ">=3.11")


class TestHomebrewFormula(unittest.TestCase):
    """Test Homebrew formula structure and generator script."""

    def test_formula_structure(self):
        formula_path = REPO_ROOT / "Formula" / "agtoosa.rb"
        self.assertTrue(formula_path.exists())
        content = formula_path.read_text(encoding="utf-8")

        self.assertIn("class Agtoosa < Formula", content)
        self.assertIn("homepage \"https://github.com/sky2464/Agtoosa2\"", content)
        self.assertIn("bin.install \"agtoosa\"", content)
        self.assertIn("assert_match \"Agtoosa2\", shell_output(\"#{bin}/agtoosa version\")", content)
        self.assertIn("darwin-arm64", content)
        self.assertIn("darwin-x86_64", content)
        self.assertIn("linux-x86_64", content)

    def test_generate_formula_output(self):
        rendered = generate_formula(
            version="0.2.1",
            darwin_arm64_sha="aaa111",
            darwin_x86_64_sha="bbb222",
            linux_x86_64_sha="ccc333"
        )
        self.assertIn("version \"0.2.1\"", rendered)
        self.assertIn("sha256 \"aaa111\"", rendered)
        self.assertIn("sha256 \"bbb222\"", rendered)
        self.assertIn("sha256 \"ccc333\"", rendered)
        self.assertIn("#{bin}/agtoosa version", rendered)

    def test_parse_checksums_from_dir(self):
        with tempfile.TemporaryDirectory() as td:
            dir_path = Path(td)
            (dir_path / "agtoosa-v0.2.1-darwin-arm64.tar.gz.sha256").write_text("hash_arm64  file.tar.gz\n")
            (dir_path / "agtoosa-v0.2.1-darwin-x86_64.tar.gz.sha256").write_text("hash_x86  file.tar.gz\n")
            (dir_path / "agtoosa-v0.2.1-linux-x86_64.tar.gz.sha256").write_text("hash_linux  file.tar.gz\n")

            checksums = parse_checksums_from_dir(dir_path)
            self.assertEqual(checksums["darwin_arm64"], "hash_arm64")
            self.assertEqual(checksums["darwin_x86_64"], "hash_x86")
            self.assertEqual(checksums["linux_x86_64"], "hash_linux")


class TestStandalonePackagingScripts(unittest.TestCase):
    """Test PyInstaller spec and build_standalone helpers."""

    def test_pyinstaller_spec_structure(self):
        spec_path = REPO_ROOT / "scripts" / "agtoosa.spec"
        self.assertTrue(spec_path.exists())
        content = spec_path.read_text(encoding="utf-8")
        self.assertIn("__main__.py", content)
        self.assertIn("agtoosa", content)
        self.assertIn("sqlite3", content)
        self.assertIn("excludes=", content)
        self.assertIn("'tkinter'", content)
        self.assertIn("name='agtoosa'", content)

    def test_detect_target_platform_and_archive_naming(self):
        os_name, arch_name = detect_target_platform()
        self.assertIn(os_name, ("darwin", "linux", "windows"))
        self.assertIn(arch_name, ("arm64", "x86_64"))

        archive_unix = get_archive_name("0.2.1", "darwin", "arm64")
        self.assertEqual(archive_unix, "agtoosa-v0.2.1-darwin-arm64.tar.gz")

        archive_win = get_archive_name("v0.2.1", "windows", "x86_64")
        self.assertEqual(archive_win, "agtoosa-v0.2.1-windows-x86_64.zip")

    def test_compute_sha256_and_create_archive(self):
        with tempfile.TemporaryDirectory() as td:
            temp_dir = Path(td)
            dummy_bin = temp_dir / "agtoosa"
            dummy_bin.write_bytes(b"Simulated standalone binary content")

            expected_hash = hashlib.sha256(b"Simulated standalone binary content").hexdigest()
            self.assertEqual(compute_sha256(dummy_bin), expected_hash)

            out_dir = temp_dir / "dist"
            archive_path, digest = create_release_archive(dummy_bin, out_dir, "test-archive.tar.gz")

            self.assertTrue(archive_path.exists())
            self.assertEqual(archive_path.name, "test-archive.tar.gz")
            checksum_file = Path(str(archive_path) + ".sha256")
            self.assertTrue(checksum_file.exists())


class TestCLIVersionDiagnostics(unittest.TestCase):
    """Test agtoosa version command output and diagnostics."""

    def test_cli_version_human_readable(self):
        import io
        from contextlib import redirect_stdout
        from agtoosa import __version__

        f = io.StringIO()
        with redirect_stdout(f):
            ret = main(["version"])

        output = f.getvalue()
        self.assertEqual(ret, 0)
        self.assertIn(f"Agtoosa2 v{__version__}", output)
        self.assertIn("Execution Mode:", output)
        self.assertIn("Platform:", output)
        self.assertIn("SQLite Engine:", output)
        self.assertIn("FTS5: ✅ Supported", output)

    def test_cli_version_json(self):
        import io
        from contextlib import redirect_stdout
        from agtoosa import __version__

        f = io.StringIO()
        with redirect_stdout(f):
            ret = main(["version", "--json"])

        output = f.getvalue()
        self.assertEqual(ret, 0)
        data = json.loads(output)
        self.assertEqual(data["version"], __version__)
        self.assertTrue(data["fts5_enabled"])
        self.assertIn("sqlite_version", data)
        self.assertIn("execution_mode", data)


if __name__ == "__main__":
    unittest.main()
