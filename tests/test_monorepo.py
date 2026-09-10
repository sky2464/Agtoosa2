"""Automated test suite for Stage 16 (DEV-016: Monorepo Package Boundary Enforcement)."""

import argparse
import json
from pathlib import Path
import pytest

from agtoosa.review.monorepo import (
    MonorepoBoundaryEngine,
    WorkspacePackage,
    BoundaryViolation,
    MonorepoReport,
)
from agtoosa.cli.lifecycle_cmd import cmd_review_boundaries
from agtoosa.mcp.server import MCPServer


def test_non_monorepo_graceful_handling(tmp_path: Path):
    """A standard single-package repo should report is_monorepo=False and pass cleanly."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src/main.py").write_text("print('hello')", encoding="utf-8")

    engine = MonorepoBoundaryEngine(tmp_path)
    report = engine.check_boundaries()

    assert not report.is_monorepo
    assert report.passed
    assert len(report.violations) == 0


def test_pnpm_workspace_discovery(tmp_path: Path):
    """Verify discovery of packages from pnpm-workspace.yaml."""
    pnpm_yaml = tmp_path / "pnpm-workspace.yaml"
    pnpm_yaml.write_text("packages:\n  - 'packages/*'\n  - 'apps/*'\n", encoding="utf-8")

    pkg_a = tmp_path / "packages/pkg-a"
    pkg_a.mkdir(parents=True)
    (pkg_a / "package.json").write_text(json.dumps({
        "name": "@myorg/pkg-a",
        "version": "1.0.0",
        "main": "src/index.ts",
        "dependencies": {}
    }), encoding="utf-8")

    app_web = tmp_path / "apps/web"
    app_web.mkdir(parents=True)
    (app_web / "package.json").write_text(json.dumps({
        "name": "@myorg/web",
        "version": "1.0.0",
        "dependencies": {"@myorg/pkg-a": "workspace:*"}
    }), encoding="utf-8")

    engine = MonorepoBoundaryEngine(tmp_path)
    packages = engine.discover_packages()

    assert len(packages) == 2
    assert "@myorg/pkg-a" in packages
    assert "@myorg/web" in packages
    assert packages["@myorg/pkg-a"].manifest_type == "npm"
    assert "@myorg/pkg-a" in packages["@myorg/web"].declared_dependencies


def test_cargo_workspace_discovery(tmp_path: Path):
    """Verify discovery of packages from Cargo.toml workspace."""
    cargo_toml = tmp_path / "Cargo.toml"
    cargo_toml.write_text(
        '[workspace]\nmembers = ["crates/core", "crates/cli"]\n',
        encoding="utf-8"
    )

    core_crate = tmp_path / "crates/core"
    core_crate.mkdir(parents=True)
    (core_crate / "Cargo.toml").write_text(
        '[package]\nname = "myorg-core"\nversion = "0.1.0"\n',
        encoding="utf-8"
    )

    cli_crate = tmp_path / "crates/cli"
    cli_crate.mkdir(parents=True)
    (cli_crate / "Cargo.toml").write_text(
        '[package]\nname = "myorg-cli"\nversion = "0.1.0"\n[dependencies.myorg-core]\npath = "../core"\n',
        encoding="utf-8"
    )

    engine = MonorepoBoundaryEngine(tmp_path)
    packages = engine.discover_packages()

    assert "myorg-core" in packages
    assert "myorg-cli" in packages
    assert packages["myorg-core"].manifest_type == "cargo"


def test_encapsulation_leak_violation(tmp_path: Path):
    """Engine must flag when a package bypasses public API to import an internal module."""
    # Setup workspace
    (tmp_path / "package.json").write_text(json.dumps({
        "workspaces": ["packages/*"]
    }), encoding="utf-8")

    # Package A (auth) with public index and private internal helper
    pkg_auth = tmp_path / "packages/auth"
    (pkg_auth / "src/internal").mkdir(parents=True)
    (pkg_auth / "package.json").write_text(json.dumps({
        "name": "@myorg/auth",
        "main": "src/index.ts"
    }), encoding="utf-8")
    (pkg_auth / "src/index.ts").write_text("export const login = () => {};\n", encoding="utf-8")
    (pkg_auth / "src/internal/secret_cipher.ts").write_text("export const cipher = 'aes';\n", encoding="utf-8")

    # Package B (web) importing internal secret_cipher directly
    pkg_web = tmp_path / "packages/web"
    (pkg_web / "src").mkdir(parents=True)
    (pkg_web / "package.json").write_text(json.dumps({
        "name": "@myorg/web",
        "dependencies": {"@myorg/auth": "*"}
    }), encoding="utf-8")
    (pkg_web / "src/app.ts").write_text(
        "import { cipher } from '@myorg/auth/src/internal/secret_cipher';\n",
        encoding="utf-8"
    )

    engine = MonorepoBoundaryEngine(tmp_path)
    report = engine.check_boundaries()

    assert report.is_monorepo
    assert not report.passed
    leaks = [v for v in report.violations if v.rule == "ENCAPSULATION_LEAK"]
    assert len(leaks) >= 1
    assert leaks[0].source_package == "@myorg/web"
    assert leaks[0].target_package == "@myorg/auth"
    assert "internal" in leaks[0].target_file


def test_undeclared_dependency_violation(tmp_path: Path):
    """Engine must flag when a package imports from a sibling without declaring it in manifest."""
    (tmp_path / "package.json").write_text(json.dumps({
        "workspaces": ["packages/*"]
    }), encoding="utf-8")

    pkg_a = tmp_path / "packages/pkg-a"
    (pkg_a / "src").mkdir(parents=True)
    (pkg_a / "package.json").write_text(json.dumps({"name": "@myorg/pkg-a", "main": "src/index.ts"}), encoding="utf-8")
    (pkg_a / "src/index.ts").write_text("export const foo = 1;\n", encoding="utf-8")

    pkg_b = tmp_path / "packages/pkg-b"
    (pkg_b / "src").mkdir(parents=True)
    # Notice: pkg-a NOT declared in dependencies
    (pkg_b / "package.json").write_text(json.dumps({"name": "@myorg/pkg-b", "dependencies": {}}), encoding="utf-8")
    (pkg_b / "src/index.ts").write_text("import { foo } from '@myorg/pkg-a';\n", encoding="utf-8")

    engine = MonorepoBoundaryEngine(tmp_path)
    report = engine.check_boundaries()

    assert report.is_monorepo
    undeclared = [v for v in report.violations if v.rule == "UNDECLARED_DEPENDENCY"]
    assert len(undeclared) >= 1
    assert undeclared[0].source_package == "@myorg/pkg-b"
    assert undeclared[0].target_package == "@myorg/pkg-a"


def test_circular_package_dependency(tmp_path: Path):
    """Engine must detect cycles between workspace packages."""
    (tmp_path / "package.json").write_text(json.dumps({
        "workspaces": ["packages/*"]
    }), encoding="utf-8")

    pkg_a = tmp_path / "packages/pkg-a"
    (pkg_a / "src").mkdir(parents=True)
    (pkg_a / "package.json").write_text(json.dumps({"name": "@myorg/pkg-a", "dependencies": {"@myorg/pkg-b": "*"}}), encoding="utf-8")
    (pkg_a / "src/index.ts").write_text("import { b } from '@myorg/pkg-b';\nexport const a = b + 1;\n", encoding="utf-8")

    pkg_b = tmp_path / "packages/pkg-b"
    (pkg_b / "src").mkdir(parents=True)
    (pkg_b / "package.json").write_text(json.dumps({"name": "@myorg/pkg-b", "dependencies": {"@myorg/pkg-a": "*"}}), encoding="utf-8")
    (pkg_b / "src/index.ts").write_text("import { a } from '@myorg/pkg-a';\nexport const b = 2;\n", encoding="utf-8")

    engine = MonorepoBoundaryEngine(tmp_path)
    report = engine.check_boundaries()

    assert report.is_monorepo
    assert not report.passed
    assert len(report.cycles) >= 1
    cycle = report.cycles[0]
    assert "@myorg/pkg-a" in cycle
    assert "@myorg/pkg-b" in cycle


def test_custom_boundaries_rules(tmp_path: Path):
    """Verify custom boundary policy rules from .agtoosa/boundaries.json."""
    (tmp_path / "packages/domain-core").mkdir(parents=True)
    (tmp_path / "packages/domain-core/package.json").write_text(
        json.dumps({"name": "@myorg/domain-core", "dependencies": {"@myorg/web-app": "*"}}),
        encoding="utf-8"
    )
    (tmp_path / "packages/domain-core/index.ts").write_text(
        "import { App } from '@myorg/web-app';\n",
        encoding="utf-8"
    )

    (tmp_path / "packages/web-app").mkdir(parents=True)
    (tmp_path / "packages/web-app/package.json").write_text(
        json.dumps({"name": "@myorg/web-app", "dependencies": {}}),
        encoding="utf-8"
    )
    (tmp_path / "packages/web-app/index.ts").write_text("export const App = 1;\n", encoding="utf-8")

    # Custom boundaries policy
    agtoosa_dir = tmp_path / ".agtoosa"
    agtoosa_dir.mkdir()
    (agtoosa_dir / "boundaries.json").write_text(json.dumps({
        "packages": [
            {"name": "@myorg/domain-core", "path": "packages/domain-core", "scope": "domain"},
            {"name": "@myorg/web-app", "path": "packages/web-app", "scope": "presentation"}
        ],
        "rules": [
            {
                "source_scope": "domain",
                "disallow": ["presentation"],
                "message": "Domain core packages cannot import presentation apps."
            }
        ]
    }), encoding="utf-8")

    engine = MonorepoBoundaryEngine(tmp_path)
    report = engine.check_boundaries()

    scope_violations = [v for v in report.violations if v.rule == "SCOPE_VIOLATION"]
    assert len(scope_violations) >= 1
    assert "Domain core packages cannot import presentation apps" in scope_violations[0].message


def test_cli_boundaries_command(tmp_path: Path, capsys):
    """Test CLI 'agtoosa review boundaries' command output."""
    (tmp_path / "packages/pkg-a").mkdir(parents=True)
    (tmp_path / "packages/pkg-a/package.json").write_text(json.dumps({"name": "pkg-a"}), encoding="utf-8")
    (tmp_path / "packages/pkg-b").mkdir(parents=True)
    (tmp_path / "packages/pkg-b/package.json").write_text(json.dumps({"name": "pkg-b"}), encoding="utf-8")

    # 1. Standard text output
    args = argparse.Namespace(path=str(tmp_path), strict=False, json=False)
    exit_code = cmd_review_boundaries(args, tmp_path)
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Monorepo Package Boundary Review" in captured
    assert "pkg-a" in captured
    assert "pkg-b" in captured

    # 2. JSON output
    args_json = argparse.Namespace(path=str(tmp_path), strict=False, json=True)
    exit_code_json = cmd_review_boundaries(args_json, tmp_path)
    assert exit_code_json == 0
    captured_json = capsys.readouterr().out
    data = json.loads(captured_json)
    assert data["is_monorepo"] is True
    assert data["packages_count"] == 2


def test_mcp_check_monorepo_boundaries(tmp_path: Path):
    """Test MCPServer tool agtoosa_check_monorepo_boundaries."""
    server = MCPServer(tmp_path)
    res_str = server.handle_tool_call("agtoosa_check_monorepo_boundaries", {"strict": False})
    data = json.loads(res_str)
    assert "is_monorepo" in data
    assert "passed" in data
