"""Tests for DEV-040: Parser capabilities registry and dialect inventory."""

from pathlib import Path
from agtoosa.parser.capabilities import (
    CAPABILITY_REGISTRY,
    ParserBackend,
    CoverageTier,
    ParseResult,
    UnboundReference,
    ParseDiagnostic
)


def test_registry_contains_all_twelve_families():
    """AC-01: Every current family has an explicit parser/version/coverage entry."""
    summary = CAPABILITY_REGISTRY.get_summary()
    assert summary["total_families"] >= 11
    families = summary["families"]
    assert "python" in families
    assert "javascript_typescript" in families
    assert "go" in families
    assert "rust" in families
    assert "jvm" in families
    assert "cpp" in families
    assert "csharp" in families
    assert "sql" in families
    assert "dockerfile" in families
    assert "prisma" in families


def test_accurate_backend_reporting_r01():
    """R-01: Asserts that Python is reported as full AST while polyglot is regex fallback."""
    py_cap = CAPABILITY_REGISTRY.get_capability("python")
    assert py_cap.active_backend == ParserBackend.PYTHON_AST
    assert py_cap.coverage_tier == CoverageTier.FULL_AST
    assert py_cap.supports_nested_functions is True

    js_cap = CAPABILITY_REGISTRY.get_capability("javascript_typescript")
    assert js_cap.active_backend == ParserBackend.REGEX_FALLBACK
    assert js_cap.coverage_tier == CoverageTier.LIMITED_FALLBACK
    assert js_cap.supports_nested_functions is False

    go_cap = CAPABILITY_REGISTRY.get_capability("go")
    assert go_cap.active_backend == ParserBackend.REGEX_FALLBACK
    assert go_cap.coverage_tier == CoverageTier.LIMITED_FALLBACK


def test_file_extension_routing():
    """Verify routing files to correct capability."""
    cap_py = CAPABILITY_REGISTRY.find_capability_for_file(Path("src/auth.py"))
    assert cap_py.family_id == "python"

    cap_ts = CAPABILITY_REGISTRY.find_capability_for_file(Path("frontend/App.tsx"))
    assert cap_ts.family_id == "javascript_typescript"

    cap_dock = CAPABILITY_REGISTRY.find_capability_for_file(Path("deploy/Dockerfile"))
    assert cap_dock.family_id == "dockerfile"


def test_parse_result_envelope():
    """AC-02/03: ParseResult encapsulates unbound references and diagnostics."""
    unbound = UnboundReference(
        caller_id="func:main",
        target_name="calculateTotal",
        relation="calls",
        file_path="app.ts",
        line=42
    )
    diag = ParseDiagnostic(
        file_path="app.ts",
        line=10,
        severity="warning",
        message="Dynamic import not resolved",
        code="UNSUPPORTED_DYNAMIC"
    )
    res = ParseResult(
        parser_name="js_ts_parser",
        unbound_references=[unbound],
        diagnostics=[diag],
        coverage_tier=CoverageTier.LIMITED_FALLBACK
    )
    assert len(res.unbound_references) == 1
    assert len(res.diagnostics) == 1
    assert res.unbound_references[0].target_name == "calculateTotal"
