"""Tests for DEV-057: Enterprise polyglot noise exclusion, dynamic semantics, and metric fidelity."""

import json
import tempfile
from pathlib import Path

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.metrics import MetricsEngine
from agtoosa.parser.scanner import (
    scan_workspace,
    DEFAULT_IGNORE_DIRS,
    DEFAULT_IGNORE_EXTENSIONS,
    DEFAULT_IGNORE_FILENAMES,
)
from agtoosa.parser.resolver import load_path_aliases, SymbolResolver
from agtoosa.parser.js_ts_parser import JavaScriptTypeScriptParser
from agtoosa.parser.python_parser import PythonASTParser


def test_multi_ecosystem_noise_exclusions():
    """AC-1: Verify that scan_workspace prunes all multi-ecosystem package caches, build outputs, lockfiles, media, and ML weights."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create valid source files
        (root / "src").mkdir()
        valid_py = root / "src" / "main.py"
        valid_py.write_text("print('hello')", encoding="utf-8")
        valid_ts = root / "src" / "app.ts"
        valid_ts.write_text("export const x = 1;", encoding="utf-8")

        # Create noisy directories that must be excluded
        for noise_dir in ["node_modules", "vendor", "Pods", ".gradle", ".next", ".turbo", "coverage", ".pnpm-store"]:
            d = root / noise_dir
            d.mkdir(parents=True)
            (d / "dummy.py").write_text("should be ignored", encoding="utf-8")

        # Create lockfiles that must be excluded
        for lockfile in ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "go.sum", "Cargo.lock"]:
            lf = root / lockfile
            lf.write_text("lock data", encoding="utf-8")

        # Create binary/media/ML asset files that must be excluded
        for noise_file in ["logo.svg", "banner.webp", "weights.safetensors", "model.onnx", "dataset.parquet", "checkpoint.pt"]:
            nf = root / "src" / noise_file
            nf.write_text("binary noise data", encoding="utf-8")

        scanned = scan_workspace(root)
        scanned_rel = [str(p.relative_to(root)) for p in scanned]

        # Valid source files must be preserved
        assert "src/main.py" in scanned_rel
        assert "src/app.ts" in scanned_rel

        # Noise files must all be filtered out
        for path_str in scanned_rel:
            assert not path_str.startswith("node_modules")
            assert not path_str.startswith("vendor")
            assert not path_str.startswith("Pods")
            assert not path_str.startswith(".gradle")
            assert not path_str.startswith(".next")
            assert not path_str.startswith(".turbo")
            assert not path_str.startswith("coverage")
            assert not path_str.startswith(".pnpm-store")
            assert not any(path_str.endswith(ext) for ext in [".svg", ".webp", ".safetensors", ".onnx", ".parquet", ".pt"])
            assert Path(path_str).name.lower() not in DEFAULT_IGNORE_FILENAMES


def test_tsconfig_path_alias_resolution():
    """AC-3: Verify path alias loading and symbol alias mapping for tsconfig.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Write a sample tsconfig.json with baseUrl and paths
        tsconfig = {
            "compilerOptions": {
                "baseUrl": ".",
                "paths": {
                    "@/*": ["src/*"],
                    "@core/*": ["packages/core/*"],
                    "@utils": ["src/utils/index.ts"]
                }
            }
        }
        (root / "tsconfig.json").write_text(json.dumps(tsconfig), encoding="utf-8")

        aliases = load_path_aliases(root)
        assert "@" in aliases
        assert aliases["@"] == "src"
        assert "@core" in aliases
        assert aliases["@core"] == "packages/core"

        # Test SymbolResolver alias rewriting
        db_path = root / "test.db"
        store = GraphStore(db_path)
        resolver = SymbolResolver(store, workspace_root=root)

        assert resolver.resolve_alias("@/components/Button") == "src/components/Button"
        assert resolver.resolve_alias("@core/auth") == "packages/core/auth"
        assert resolver.resolve_alias("react") == "react"


def test_typescript_type_only_imports():
    """AC-4: Verify TypeScript `import type` emits TYPE_DEPENDS_ON edges."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        ts_file = root / "service.ts"
        ts_file.write_text(
            'import type { UserProfile } from "./models";\n'
            'import { fetchUser } from "./api";\n'
            'export const run = () => {};\n',
            encoding="utf-8"
        )

        parser = JavaScriptTypeScriptParser()
        nodes, edges = parser.parse(ts_file, root)

        type_edges = [e for e in edges if e.edge_type == EdgeType.TYPE_DEPENDS_ON]
        import_edges = [e for e in edges if e.edge_type == EdgeType.IMPORTS]

        assert len(type_edges) == 1
        assert "models" in type_edges[0].target_id
        assert type_edges[0].metadata.get("type_only") is True

        assert len(import_edges) == 1
        assert "api" in import_edges[0].target_id


def test_python_type_checking_imports():
    """AC-4: Verify Python `if TYPE_CHECKING:` emits TYPE_DEPENDS_ON edges."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        py_file = root / "service.py"
        py_file.write_text(
            'from typing import TYPE_CHECKING\n'
            'import os\n\n'
            'if TYPE_CHECKING:\n'
            '    from models import SchemaDefinition\n'
            '    import pandas as pd\n\n'
            'def handler():\n'
            '    pass\n',
            encoding="utf-8"
        )

        parser = PythonASTParser()
        nodes, edges = parser.parse(py_file, root)

        type_edges = [e for e in edges if e.edge_type == EdgeType.TYPE_DEPENDS_ON]
        runtime_import_edges = [e for e in edges if e.edge_type == EdgeType.IMPORTS]

        target_ids = [e.target_id for e in type_edges]
        assert any("models.SchemaDefinition" in tid for tid in target_ids)
        assert any("pandas" in tid for tid in target_ids)

        runtime_target_ids = [e.target_id for e in runtime_import_edges]
        assert any("os" in tid for tid in runtime_target_ids)


def test_type_only_edges_prevent_false_circular_dependency_penalties():
    """AC-4: Verify that TYPE_DEPENDS_ON edges are excluded from cycle detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = GraphStore(db_path)

        # Create two nodes: file_a and file_b
        node_a = Node(id="file:a.ts", name="a.ts", node_type=NodeType.FILE, path="a.ts")
        node_b = Node(id="file:b.ts", name="b.ts", node_type=NodeType.FILE, path="b.ts")

        # file_a runtime imports file_b
        edge_runtime = Edge(source_id="file:a.ts", target_id="file:b.ts", edge_type=EdgeType.IMPORTS)
        # file_b only TYPE_DEPENDS_ON file_a (compile-time interface reference)
        edge_type_only = Edge(source_id="file:b.ts", target_id="file:a.ts", edge_type=EdgeType.TYPE_DEPENDS_ON)

        store.insert_batch([node_a, node_b], [edge_runtime, edge_type_only])

        engine = MetricsEngine(store)
        # Detect cycles: should report 0 circular dependencies because TYPE_DEPENDS_ON is excluded
        cycles = engine.detect_cycles()
        assert len(cycles) == 0


def test_domain_vs_infra_hub_classification():
    """AC-6: Verify that MetricsEngine classifies domain hubs vs infra hubs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = GraphStore(db_path)

        # Nodes
        domain_node = Node(id="func:order.py:process_order", name="process_order", node_type=NodeType.FUNCTION, path="order.py")
        infra_node = Node(id="func:logger.py:logger", name="logger", node_type=NodeType.FUNCTION, path="logger.py")
        caller1 = Node(id="func:api.py:post_order", name="post_order", node_type=NodeType.FUNCTION, path="api.py")
        caller2 = Node(id="func:worker.py:run_job", name="run_job", node_type=NodeType.FUNCTION, path="worker.py")

        edges = [
            Edge(source_id="func:api.py:post_order", target_id="func:order.py:process_order", edge_type=EdgeType.CALLS),
            Edge(source_id="func:worker.py:run_job", target_id="func:order.py:process_order", edge_type=EdgeType.CALLS),
            Edge(source_id="func:api.py:post_order", target_id="func:logger.py:logger", edge_type=EdgeType.CALLS),
            Edge(source_id="func:worker.py:run_job", target_id="func:logger.py:logger", edge_type=EdgeType.CALLS),
        ]

        store.insert_batch([domain_node, infra_node, caller1, caller2], edges)

        engine = MetricsEngine(store)
        report = engine.compute_all()
        assert "top_domain_hubs" in report
        assert "top_infra_hubs" in report

        infra_names = [h["name"] for h in report["top_infra_hubs"]]
        domain_names = [h["name"] for h in report["top_domain_hubs"]]

        assert "logger" in infra_names
        assert "process_order" in domain_names
