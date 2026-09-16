"""Tests for monorepo workspace package discovery and path alias resolution."""

import json
from pathlib import Path
import tempfile

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.parser.resolver import (
    load_path_aliases,
    SymbolResolver,
    ResolutionStatus,
)


def test_load_path_aliases_none_and_empty():
    """Verify load_path_aliases returns empty dict for None or empty directory."""
    assert load_path_aliases(None) == {}

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        assert load_path_aliases(root) == {}


def test_load_path_aliases_tsconfig():
    """Verify parsing tsconfig.json with baseUrl, comments, and path mappings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        tsconfig_content = """
        {
            // Root compiler options
            "compilerOptions": {
                "baseUrl": ".",
                "paths": {
                    "@/*": ["src/*"],
                    "@core/*": ["packages/core/*"],
                    "@utils": ["src/utils/index.ts"],
                }
            }
        }
        """
        (root / "tsconfig.json").write_text(tsconfig_content, encoding="utf-8")

        aliases = load_path_aliases(root)
        assert aliases.get("@") == "src"
        assert aliases.get("@core") == "packages/core"
        assert aliases.get("@utils") == "src/utils/index.ts"


def test_load_path_aliases_jsconfig():
    """Verify jsconfig.json fallback when tsconfig.json is absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        jsconfig = {
            "compilerOptions": {
                "baseUrl": "./",
                "paths": {
                    "@components/*": ["src/components/*"]
                }
            }
        }
        (root / "jsconfig.json").write_text(json.dumps(jsconfig), encoding="utf-8")

        aliases = load_path_aliases(root)
        assert aliases.get("@components") == "src/components"


def test_load_path_aliases_conventional_monorepo():
    """Verify automatic discovery of packages in packages/* declaring a name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        ui_dir = root / "packages" / "ui"
        ui_dir.mkdir(parents=True)
        (ui_dir / "package.json").write_text(json.dumps({
            "name": "@repo/ui",
            "version": "1.0.0"
        }), encoding="utf-8")

        core_dir = root / "packages" / "core"
        core_dir.mkdir(parents=True)
        (core_dir / "package.json").write_text(json.dumps({
            "name": "@repo/core",
            "version": "1.0.0"
        }), encoding="utf-8")

        aliases = load_path_aliases(root)
        assert aliases.get("@repo/ui") == "packages/ui"
        assert aliases.get("@repo/core") == "packages/core"


def test_load_path_aliases_npm_workspaces():
    """Verify package discovery based on root package.json workspaces array."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        (root / "package.json").write_text(json.dumps({
            "name": "root-monorepo",
            "private": True,
            "workspaces": ["libs/*", "apps/*"]
        }), encoding="utf-8")

        lib_dir = root / "libs" / "design"
        lib_dir.mkdir(parents=True)
        (lib_dir / "package.json").write_text(json.dumps({
            "name": "@company/design",
            "version": "2.0.0"
        }), encoding="utf-8")

        app_dir = root / "apps" / "web"
        app_dir.mkdir(parents=True)
        (app_dir / "package.json").write_text(json.dumps({
            "name": "@company/web",
            "version": "1.0.0"
        }), encoding="utf-8")

        aliases = load_path_aliases(root)
        assert aliases.get("@company/design") == "libs/design"
        assert aliases.get("@company/web") == "apps/web"


def test_load_path_aliases_pnpm_workspace():
    """Verify package discovery from pnpm-workspace.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        (root / "pnpm-workspace.yaml").write_text(
            "packages:\n  - 'modules/*'\n  - 'services/*'\n",
            encoding="utf-8"
        )

        mod_dir = root / "modules" / "auth"
        mod_dir.mkdir(parents=True)
        (mod_dir / "package.json").write_text(json.dumps({
            "name": "@pnpm/auth"
        }), encoding="utf-8")

        srv_dir = root / "services" / "gateway"
        srv_dir.mkdir(parents=True)
        (srv_dir / "package.json").write_text(json.dumps({
            "name": "@pnpm/gateway"
        }), encoding="utf-8")

        aliases = load_path_aliases(root)
        assert aliases.get("@pnpm/auth") == "modules/auth"
        assert aliases.get("@pnpm/gateway") == "services/gateway"


def test_load_path_aliases_node_modules_ignored():
    """Ensure package.json files within node_modules or build artifacts are ignored."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        nm_dir = root / "packages" / "ui" / "node_modules" / "subdep"
        nm_dir.mkdir(parents=True)
        (nm_dir / "package.json").write_text(json.dumps({
            "name": "should-be-ignored"
        }), encoding="utf-8")

        ui_dir = root / "packages" / "ui"
        (ui_dir / "package.json").write_text(json.dumps({
            "name": "@repo/ui"
        }), encoding="utf-8")

        aliases = load_path_aliases(root)
        assert "@repo/ui" in aliases
        assert "should-be-ignored" not in aliases


def test_hybrid_monorepo_and_tsconfig():
    """Verify coexistence of monorepo packages and tsconfig.json path aliases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Monorepo packages
        ui_dir = root / "packages" / "ui"
        ui_dir.mkdir(parents=True)
        (ui_dir / "package.json").write_text(json.dumps({"name": "@repo/ui"}), encoding="utf-8")

        # tsconfig.json
        tsconfig = {
            "compilerOptions": {
                "paths": {
                    "@/*": ["src/*"],
                    "@custom-alias/*": ["custom/path/*"]
                }
            }
        }
        (root / "tsconfig.json").write_text(json.dumps(tsconfig), encoding="utf-8")

        aliases = load_path_aliases(root)
        assert aliases.get("@repo/ui") == "packages/ui"
        assert aliases.get("@") == "src"
        assert aliases.get("@custom-alias") == "custom/path"


def test_symbol_resolver_resolve_alias():
    """Verify SymbolResolver.resolve_alias rewriting behavior for monorepo and tsconfig paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Monorepo package
        ui_dir = root / "packages" / "ui"
        ui_dir.mkdir(parents=True)
        (ui_dir / "package.json").write_text(json.dumps({"name": "@repo/ui"}), encoding="utf-8")

        # tsconfig.json
        tsconfig = {
            "compilerOptions": {
                "paths": {
                    "@/*": ["src/*"]
                }
            }
        }
        (root / "tsconfig.json").write_text(json.dumps(tsconfig), encoding="utf-8")

        db_path = root / "test.db"
        store = GraphStore(db_path)
        resolver = SymbolResolver(store, workspace_root=root)

        # Exact match package alias
        assert resolver.resolve_alias("@repo/ui") == "packages/ui"

        # Subpath in package alias
        assert resolver.resolve_alias("@repo/ui/Button") == "packages/ui/Button"
        assert resolver.resolve_alias("@repo/ui/components/Navbar") == "packages/ui/components/Navbar"

        # tsconfig path alias
        assert resolver.resolve_alias("@/components/Button") == "src/components/Button"

        # External package (not an alias)
        assert resolver.resolve_alias("react") == "react"
        assert resolver.resolve_alias("lodash/debounce") == "lodash/debounce"

        # Prefix collision safety: @repo/ui-other must NOT match @repo/ui
        assert resolver.resolve_alias("@repo/ui-other") == "@repo/ui-other"
        assert resolver.resolve_alias("@repo/ui-other/Button") == "@repo/ui-other/Button"


def test_cross_package_symbol_resolution():
    """Verify SymbolResolver.resolve_all_symbols successfully resolves cross-package calls."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Monorepo setup
        ui_dir = root / "packages" / "ui"
        ui_dir.mkdir(parents=True)
        (ui_dir / "package.json").write_text(json.dumps({"name": "@repo/ui"}), encoding="utf-8")

        app_dir = root / "apps" / "web"
        app_dir.mkdir(parents=True)
        (app_dir / "package.json").write_text(json.dumps({"name": "@repo/web"}), encoding="utf-8")

        db_path = root / "test.db"
        store = GraphStore(db_path)

        # Target button component in @repo/ui
        button_fn = Node(
            id="func:packages/ui/Button.tsx:Button",
            name="Button",
            node_type=NodeType.FUNCTION,
            path="packages/ui/Button.tsx"
        )

        # Caller in @repo/web
        caller_fn = Node(
            id="func:apps/web/App.tsx:render",
            name="render",
            node_type=NodeType.FUNCTION,
            path="apps/web/App.tsx"
        )

        # Import statement in caller file
        imp = Node(
            id="import:apps/web/App.tsx:@repo/ui/Button",
            name="@repo/ui/Button",
            node_type=NodeType.IMPORT,
            path="apps/web/App.tsx"
        )

        # Call placeholder edge
        call_edge = Edge(
            source_id="func:apps/web/App.tsx:render",
            target_id="func_call:Button",
            edge_type=EdgeType.CALLS,
            provenance="syntactic_ast"
        )

        store.insert_batch([button_fn, caller_fn, imp], [call_edge])

        resolver = SymbolResolver(store, workspace_root=root)
        stats = resolver.resolve_all_symbols()

        assert stats["resolved"] >= 1

        neighbors = store.get_neighbors("func:apps/web/App.tsx:render", direction="out")
        called_ids = [n["id"] for n in neighbors]
        assert "func:packages/ui/Button.tsx:Button" in called_ids
