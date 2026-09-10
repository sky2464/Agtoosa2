"""Automated tests for Stage 19 (DEV-019: Automated Cycle Decoupler Engine)."""

import argparse
import json
from pathlib import Path
import pytest

from agtoosa.graph.store import GraphStore
from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.refactor.decoupler import CycleDecouplerEngine
from agtoosa.cli.refactor_cmd import cmd_refactor_decouple
from agtoosa.mcp.server import MCPServer


def test_acyclic_graph_decoupler(tmp_path: Path):
    """An acyclic DAG should report 0 cycles and 0 decoupling strategies."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    n1 = Node(id="func:a", name="fn_a", node_type=NodeType.FUNCTION, path="a.py", start_line=1, end_line=10)
    n2 = Node(id="func:b", name="fn_b", node_type=NodeType.FUNCTION, path="b.py", start_line=1, end_line=10)
    store.insert_batch([n1, n2], [Edge(source_id=n1.id, target_id=n2.id, edge_type=EdgeType.CALLS, provenance="ast")])

    engine = CycleDecouplerEngine(store, tmp_path)
    report = engine.analyze_cycles()

    assert report.total_cycles_detected == 0
    assert len(report.strategies) == 0


def test_dependency_inversion_strategy(tmp_path: Path):
    """A cycle between two services should produce a DEPENDENCY_INVERSION blueprint."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    svc_a = Node(id="class:svc_a", name="OrderService", node_type=NodeType.CLASS, path="services/order.py", start_line=1, end_line=50)
    svc_b = Node(id="class:svc_b", name="PaymentService", node_type=NodeType.CLASS, path="services/payment.py", start_line=1, end_line=50)

    # Cyclic calls: OrderService -> PaymentService -> OrderService
    edges = [
        Edge(source_id=svc_a.id, target_id=svc_b.id, edge_type=EdgeType.CALLS, provenance="ast"),
        Edge(source_id=svc_b.id, target_id=svc_a.id, edge_type=EdgeType.CALLS, provenance="ast"),
    ]
    store.insert_batch([svc_a, svc_b], edges)

    engine = CycleDecouplerEngine(store, tmp_path)
    report = engine.analyze_cycles()

    assert report.total_cycles_detected >= 1
    assert len(report.strategies) >= 1
    strat = report.strategies[0]
    assert strat.strategy_type in ("DEPENDENCY_INVERSION", "SHARED_KERNEL")
    assert "Protocol" in strat.generated_code_stub or "class" in strat.generated_code_stub
    assert len(strat.refactor_steps) >= 3


def test_shared_kernel_strategy(tmp_path: Path):
    """A cycle involving a data model should recommend SHARED_KERNEL extraction."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    controller = Node(id="class:ctrl", name="UserController", node_type=NodeType.CLASS, path="controllers/user.py", start_line=1, end_line=30)
    model = Node(id="class:model", name="UserModel", node_type=NodeType.CLASS, path="models/user_model.py", start_line=1, end_line=30)

    edges = [
        Edge(source_id=controller.id, target_id=model.id, edge_type=EdgeType.CALLS, provenance="ast"),
        Edge(source_id=model.id, target_id=controller.id, edge_type=EdgeType.CALLS, provenance="ast"),
    ]
    store.insert_batch([controller, model], edges)

    engine = CycleDecouplerEngine(store, tmp_path)
    report = engine.analyze_cycles()

    assert report.total_cycles_detected >= 1
    strat = report.strategies[0]
    assert strat.strategy_type == "SHARED_KERNEL"
    assert "Shared Kernel" in strat.rationale


def test_cli_refactor_decouple(tmp_path: Path, capsys):
    """Test CLI 'agtoosa refactor decouple' command."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    n1 = Node(id="func:x", name="fn_x", node_type=NodeType.FUNCTION, path="x.py", start_line=1, end_line=10)
    n2 = Node(id="func:y", name="fn_y", node_type=NodeType.FUNCTION, path="y.py", start_line=1, end_line=10)
    store.insert_batch([n1, n2], [
        Edge(source_id=n1.id, target_id=n2.id, edge_type=EdgeType.CALLS, provenance="ast"),
        Edge(source_id=n2.id, target_id=n1.id, edge_type=EdgeType.CALLS, provenance="ast")
    ])

    args = argparse.Namespace(json=False)
    exit_code = cmd_refactor_decouple(args, tmp_path)
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Automated Cycle Decoupler" in captured
    assert "Proposed Decoupling Blueprints" in captured

    # Test JSON output
    args_json = argparse.Namespace(json=True)
    exit_code_json = cmd_refactor_decouple(args_json, tmp_path)
    assert exit_code_json == 0
    data = json.loads(capsys.readouterr().out)
    assert "total_cycles_detected" in data
    assert len(data["strategies"]) >= 1


def test_mcp_suggest_cycle_decoupling(tmp_path: Path):
    """Test MCPServer agtoosa_suggest_cycle_decoupling tool."""
    server = MCPServer(tmp_path)
    res_str = server.handle_tool_call("agtoosa_suggest_cycle_decoupling", {})
    data = json.loads(res_str)
    assert "total_cycles_detected" in data
