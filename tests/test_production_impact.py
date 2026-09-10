"""Automated tests for Stage 18 (DEV-018: Production Blast Radius)."""

import argparse
import json
from pathlib import Path
import pytest

from agtoosa.graph.store import GraphStore
from agtoosa.core.model import Node, Edge, NodeType
from agtoosa.graph.query import compute_impact
from agtoosa.cli.graph_cmd import cmd_graph_impact
from agtoosa.mcp.server import MCPServer


@pytest.fixture
def production_store(tmp_path: Path) -> GraphStore:
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)

    # Core target
    target = Node(
        id="function:api/order.py:process_payment",
        name="process_payment",
        node_type=NodeType.FUNCTION,
        path="api/order.py",
        start_line=10,
        end_line=50
    )
    # Callers
    caller_checkout = Node(
        id="function:web/checkout.py:submit_order",
        name="submit_order",
        node_type=NodeType.FUNCTION,
        path="web/checkout.py",
        start_line=20,
        end_line=80
    )
    caller_batch = Node(
        id="function:jobs/cron.py:retry_payments",
        name="retry_payments",
        node_type=NodeType.FUNCTION,
        path="jobs/cron.py",
        start_line=5,
        end_line=40
    )
    caller_dormant = Node(
        id="function:legacy/old_flow.py:v1_pay",
        name="v1_pay",
        node_type=NodeType.FUNCTION,
        path="legacy/old_flow.py",
        start_line=1,
        end_line=20
    )

    edges = [
        Edge(source_id=caller_checkout.id, target_id=target.id, edge_type="calls", provenance="ast"),
        Edge(source_id=caller_batch.id, target_id=target.id, edge_type="calls", provenance="ast"),
        Edge(source_id=caller_dormant.id, target_id=target.id, edge_type="calls", provenance="ast"),
    ]

    store.insert_batch([target, caller_checkout, caller_batch, caller_dormant], edges)

    # Seed runtime telemetry
    store.save_telemetry_batch([
        {
            "node_id": target.id,
            "call_count": 50000,
            "avg_duration_ms": 12.5,
            "error_count": 10,
            "error_rate": 0.0002
        },
        {
            "node_id": caller_checkout.id,
            "call_count": 45000,
            "avg_duration_ms": 45.0,
            "error_count": 50,
            "error_rate": 0.0011
        },
        {
            "node_id": caller_batch.id,
            "call_count": 5000,
            "avg_duration_ms": 120.0,
            "error_count": 800,  # 16% error rate -> high error caller!
            "error_rate": 0.16
        },
        # caller_dormant has 0 recorded telemetry
    ])

    return store


def test_production_blast_radius_calculation(production_store: GraphStore):
    """Verify traffic-weighted blast radius calculation, risk tier, and caller sorting."""
    res = compute_impact(
        production_store,
        "process_payment",
        production=True
    )
    assert res is not None
    assert res["impacted_count"] == 3
    assert res["production_blast_radius"] is not None

    pbr = res["production_blast_radius"]
    assert pbr["risk_tier"] == "P0_CRITICAL"
    assert pbr["total_traffic_at_risk"] >= 100000  # 50k + 45k + 5k
    assert pbr["active_callers_count"] == 2
    assert pbr["dormant_callers_count"] == 1

    # Callers should be sorted by traffic descending
    impacted = res["impacted"]
    assert impacted[0]["id"] == "function:web/checkout.py:submit_order"
    assert impacted[0]["call_count"] == 45000
    assert impacted[1]["id"] == "function:jobs/cron.py:retry_payments"
    assert impacted[1]["call_count"] == 5000
    assert impacted[2]["id"] == "function:legacy/old_flow.py:v1_pay"
    assert impacted[2]["call_count"] == 0
    assert not impacted[2]["is_active"]


def test_dormant_production_blast_radius(tmp_path: Path):
    """If a symbol has no recorded traffic, it should receive P4_DORMANT tier."""
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    n1 = Node(id="func:a", name="fn_a", node_type=NodeType.FUNCTION, path="a.py", start_line=1, end_line=10)
    n2 = Node(id="func:b", name="fn_b", node_type=NodeType.FUNCTION, path="b.py", start_line=1, end_line=10)
    store.insert_batch([n1, n2], [Edge(source_id=n2.id, target_id=n1.id, edge_type="calls", provenance="ast")])

    res = compute_impact(store, "fn_a", production=True)
    assert res is not None
    pbr = res["production_blast_radius"]
    assert pbr["risk_tier"] == "P4_DORMANT"
    assert pbr["total_traffic_at_risk"] == 0
    assert pbr["active_callers_count"] == 0
    assert pbr["dormant_callers_count"] == 1


def test_cli_graph_impact_production(production_store: GraphStore, tmp_path: Path, capsys):
    """Test CLI 'agtoosa graph impact <target> --production' output."""
    args = argparse.Namespace(
        target="process_payment",
        depth=3,
        federated=False,
        production=True,
        json=False
    )
    exit_code = cmd_graph_impact(args, tmp_path)
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Production Telemetry Weighted" in captured
    assert "Production Risk Tier" in captured
    assert "P0_CRITICAL" in captured
    assert "submit_order" in captured

    # Test JSON output
    args_json = argparse.Namespace(
        target="process_payment",
        depth=3,
        federated=False,
        production=True,
        json=True
    )
    exit_code_json = cmd_graph_impact(args_json, tmp_path)
    assert exit_code_json == 0
    data = json.loads(capsys.readouterr().out)
    assert "production_blast_radius" in data
    assert data["production_blast_radius"]["risk_tier"] == "P0_CRITICAL"


def test_mcp_query_impact_production(production_store: GraphStore, tmp_path: Path):
    """Test MCPServer agtoosa_query_impact with production=True."""
    server = MCPServer(tmp_path)
    res_str = server.handle_tool_call(
        "agtoosa_query_impact",
        {"target": "process_payment", "production": True}
    )
    data = json.loads(res_str)
    assert "production_blast_radius" in data
    assert data["production_blast_radius"]["total_traffic_at_risk"] >= 100000
