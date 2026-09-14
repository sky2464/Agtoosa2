"""Automated tests for Stage 20 (DEV-020: Dead Code & Zombie Symbol Pruning)."""

import argparse
import json
from pathlib import Path
import pytest

from agtoosa.graph.store import GraphStore
from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.refactor.dead_code import DeadCodePruner, DeadCodeReport, format_dead_code_text
from agtoosa.cli.refactor_cmd import cmd_refactor_dead_code
from agtoosa.mcp.server import MCPServer


def _make_node(nid: str, name: str, ntype: str, path: str, start: int = 1, end: int = 10):
    return Node(id=nid, name=name, node_type=NodeType(ntype), path=path, start_line=start, end_line=end)


def test_no_dead_code_all_connected(tmp_path: Path):
    """A fully connected graph should report zero dead code."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    main = _make_node("func:main", "main", "function", "main.py")
    helper = _make_node("func:helper", "helper", "function", "utils.py")
    store.insert_batch(
        [main, helper],
        [Edge(source_id=main.id, target_id=helper.id, edge_type=EdgeType.CALLS, provenance="ast")]
    )

    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()

    # 'main' is an entrypoint (name match), 'helper' is called by main
    assert report.total_dead_candidates == 0
    assert len(report.zombies) == 0


def test_detect_uncalled_private_function(tmp_path: Path):
    """A private function with zero callers should be flagged as high-confidence dead code."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    public_fn = _make_node("func:main", "main", "function", "app.py")
    private_fn = _make_node("func:_orphan", "_orphan_helper", "function", "utils.py", 10, 25)

    # No edges — _orphan_helper is never called
    store.insert_batch([public_fn, private_fn], [])

    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()

    assert report.total_dead_candidates >= 1
    zombie = next(z for z in report.zombies if z.name == "_orphan_helper")
    assert zombie.confidence == "high"
    assert zombie.estimated_lines == 16  # lines 10-25
    assert zombie.safe_to_delete is True
    assert "Zero incoming callers" in zombie.reason
    assert len(zombie.deletion_steps) >= 3


def test_detect_uncalled_public_function(tmp_path: Path):
    """A public function with zero callers should be flagged but with lower confidence."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    orphan = _make_node("func:orphan", "compute_legacy_score", "function", "scoring.py", 1, 30)

    store.insert_batch([orphan], [])

    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()

    assert report.total_dead_candidates >= 1
    zombie = next(z for z in report.zombies if z.name == "compute_legacy_score")
    assert zombie.confidence == "medium"  # Public function, but zero callers


def test_skip_test_functions(tmp_path: Path):
    """Test functions (test_*) should be excluded from dead code detection."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    test_fn = _make_node("func:test_something", "test_something", "function", "tests/test_app.py")

    store.insert_batch([test_fn], [])

    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()

    # test_something should be excluded (both by name prefix and path pattern)
    assert report.total_dead_candidates == 0


def test_skip_dunder_methods(tmp_path: Path):
    """Dunder methods (__init__, __repr__, etc.) should be excluded."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    init = _make_node("func:init", "__init__", "function", "models.py")
    repr_m = _make_node("func:repr", "__repr__", "function", "models.py")

    store.insert_batch([init, repr_m], [])

    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()

    assert report.total_dead_candidates == 0


def test_skip_cli_handlers(tmp_path: Path):
    """CLI handler functions (cmd_*) should be excluded from dead code detection."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    handler = _make_node("func:cmd_build", "cmd_build", "function", "cli/commands.py")

    store.insert_batch([handler], [])

    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()

    assert report.total_dead_candidates == 0


def test_confidence_filter(tmp_path: Path):
    """min_confidence filter should exclude lower-confidence results."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    high = _make_node("func:_private", "_private_impl", "function", "core.py", 1, 10)
    med = _make_node("func:pub", "compute_something", "function", "engine.py", 1, 20)
    low = _make_node("class:MyClass", "MyClass", "class", "models.py", 1, 50)

    store.insert_batch([high, med, low], [])

    pruner = DeadCodePruner(store, tmp_path)

    # All confidence levels
    full_report = pruner.analyze(min_confidence="low")
    # Only medium and high
    med_report = pruner.analyze(min_confidence="medium")
    # Only high
    high_report = pruner.analyze(min_confidence="high")

    assert full_report.total_dead_candidates >= med_report.total_dead_candidates
    assert med_report.total_dead_candidates >= high_report.total_dead_candidates


def test_called_function_not_flagged(tmp_path: Path):
    """A function that IS called should never appear as dead code."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    caller = _make_node("func:main", "main", "function", "app.py")
    callee = _make_node("func:process", "process_data", "function", "engine.py")

    store.insert_batch(
        [caller, callee],
        [Edge(source_id=caller.id, target_id=callee.id, edge_type=EdgeType.CALLS, provenance="ast")]
    )

    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()

    dead_names = [z.name for z in report.zombies]
    assert "process_data" not in dead_names


def test_downstream_callees_warning(tmp_path: Path):
    """Dead functions that call other things should warn about potential cascade."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    dead = _make_node("func:_dead", "_dead_fn", "function", "legacy.py", 1, 20)
    downstream = _make_node("func:_util", "_util_helper", "function", "legacy.py", 25, 35)

    store.insert_batch(
        [dead, downstream],
        [Edge(source_id=dead.id, target_id=downstream.id, edge_type=EdgeType.CALLS, provenance="ast")]
    )

    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()

    zombie = next(z for z in report.zombies if z.name == "_dead_fn")
    assert any("downstream" in s.lower() or "callee" in s.lower() for s in zombie.deletion_steps)


def test_format_text_output(tmp_path: Path):
    """The text formatter should produce readable output."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    orphan = _make_node("func:_orphan", "_orphan_fn", "function", "lib.py", 5, 20)

    store.insert_batch([orphan], [])

    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()
    text = format_dead_code_text(report)

    assert "Dead Code" in text
    assert "Zombie Symbol" in text or "Zombie" in text
    assert "_orphan_fn" in text


def test_empty_graph(tmp_path: Path):
    """Empty graph should report zero dead code with clean output."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)

    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()

    assert report.total_symbols_analyzed == 0
    assert report.total_dead_candidates == 0

    text = format_dead_code_text(report)
    assert "No dead code" in text


def test_cli_refactor_dead_code(tmp_path: Path, capsys):
    """Test CLI 'agtoosa refactor dead-code' command."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    orphan = _make_node("func:_orphan", "_orphan_util", "function", "utils.py", 1, 15)
    store.insert_batch([orphan], [])

    args = argparse.Namespace(json=False, min_confidence="low")
    exit_code = cmd_refactor_dead_code(args, tmp_path)
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Dead Code" in captured
    assert "_orphan_util" in captured

    # Test JSON output
    args_json = argparse.Namespace(json=True, min_confidence="low")
    exit_code_json = cmd_refactor_dead_code(args_json, tmp_path)
    assert exit_code_json == 0
    data = json.loads(capsys.readouterr().out)
    assert "total_dead_candidates" in data
    assert "zombies" in data
    assert len(data["zombies"]) >= 1


def test_mcp_detect_dead_code(tmp_path: Path):
    """Test MCPServer agtoosa_detect_dead_code tool."""
    server = MCPServer(tmp_path)
    res_str = server.handle_tool_call("agtoosa_detect_dead_code", {})
    data = json.loads(res_str)
    assert "total_dead_candidates" in data
    assert "zombies" in data


def test_mcp_detect_dead_code_with_filter(tmp_path: Path):
    """Test MCPServer agtoosa_detect_dead_code with confidence filter."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    orphan = _make_node("func:_priv", "_private_thing", "function", "internal.py", 1, 10)
    store.insert_batch([orphan], [])

    server = MCPServer(tmp_path)
    res_str = server.handle_tool_call("agtoosa_detect_dead_code", {"min_confidence": "high"})
    data = json.loads(res_str)
    assert data["total_dead_candidates"] >= 1
    assert all(z["confidence"] == "high" for z in data["zombies"])


def test_report_to_dict_serialization(tmp_path: Path):
    """Report should be fully JSON-serializable."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    orphan = _make_node("func:_dead", "_dead_fn", "function", "legacy.py", 1, 10)
    store.insert_batch([orphan], [])

    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()
    report_dict = report.to_dict()

    # Must be JSON-serializable without exceptions
    serialized = json.dumps(report_dict)
    deserialized = json.loads(serialized)

    assert deserialized["total_symbols_analyzed"] == report.total_symbols_analyzed
    assert deserialized["total_dead_candidates"] == report.total_dead_candidates
    assert len(deserialized["zombies"]) == len(report.zombies)


def test_format_dead_code_compact_vs_verbose(tmp_path: Path):
    """DEV-051: Default output displays compact table; verbose mode includes deletion steps."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    orphan = _make_node("func:_orphan", "_orphan_fn", "function", "lib.py", 5, 20)
    store.insert_batch([orphan], [])

    pruner = DeadCodePruner(store, tmp_path)
    report = pruner.analyze()

    compact_text = format_dead_code_text(report, verbose=False)
    assert "CONFIDENCE" in compact_text
    assert "SYMBOL" in compact_text
    assert "Safe to Delete" in compact_text
    assert "Deletion Steps:" not in compact_text

    verbose_text = format_dead_code_text(report, verbose=True)
    assert "Detailed Deletion Guidelines" in verbose_text
    assert "Deletion Steps:" in verbose_text


def test_format_diffstat():
    """DEV-051: format_diffstat should generate git-style diff bars and summary totals."""
    from agtoosa.refactor.dead_code import format_diffstat

    diffs = {
        "src/utils.py": "--- a/src/utils.py\n+++ b/src/utils.py\n@@ -1,5 +1,1 @@\n-line1\n-line2\n-line3\n+new_line",
        "src/core.py": "--- a/src/core.py\n+++ b/src/core.py\n@@ -10,5 +10,1 @@\n-dead1\n-dead2",
    }
    stat = format_diffstat(diffs)
    assert "src/utils.py" in stat
    assert "src/core.py" in stat
    assert "Total: 2 file(s) affected" in stat
    assert "━" in stat


def test_cli_dry_run_diff_gating(tmp_path: Path, capsys):
    """DEV-051: CLI dry-run shows diffstat by default, and only outputs full diff when --diff is set."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    file_path = tmp_path / "mod.py"
    file_path.write_text("def _helper():\n    pass\n\ndef main():\n    pass\n")

    orphan = _make_node("func:_helper", "_helper", "function", "mod.py", 1, 2)
    store.insert_batch([orphan], [])

    # Dry run without --diff
    args_dry = argparse.Namespace(json=False, min_confidence="high", dry_run=True, diff=False, apply=False, verbose=False)
    exit_code = cmd_refactor_dead_code(args_dry, tmp_path)
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Dry Run Preview" in captured
    assert "💡 Tip: Pass --diff" in captured
    assert "@@" not in captured

    # Dry run with --diff
    args_diff = argparse.Namespace(json=False, min_confidence="high", dry_run=True, diff=True, apply=False, verbose=False)
    exit_code = cmd_refactor_dead_code(args_diff, tmp_path)
    assert exit_code == 0
    captured_diff = capsys.readouterr().out
    assert "Full Unified Diffs:" in captured_diff
    assert "--- mod.py ---" in captured_diff

