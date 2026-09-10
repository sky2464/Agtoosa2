"""Automated tests for Stage 17 (DEV-017: Runtime Observability & Dynamic Heatmaps)."""

import argparse
import json
from pathlib import Path
import pytest

from agtoosa.graph.store import GraphStore
from agtoosa.core.model import Node, NodeType
from agtoosa.observability.ingester import TelemetryIngester, HeatmapNode
from agtoosa.cli.observability_cmd import cmd_telemetry
from agtoosa.mcp.server import MCPServer


@pytest.fixture
def sample_store(tmp_path: Path) -> GraphStore:
    db_path = tmp_path / ".agtoosa/graph.db"
    store = GraphStore(db_path)
    # Seed nodes
    nodes = [
        Node(
            id="function:app/auth.py:login",
            name="login",
            node_type=NodeType.FUNCTION,
            path="app/auth.py",
            start_line=10,
            end_line=25,
            docstring="Authenticate user"
        ),
        Node(
            id="function:app/db.py:query_users",
            name="query_users",
            node_type=NodeType.FUNCTION,
            path="app/db.py",
            start_line=30,
            end_line=50,
            docstring="Query users from database"
        ),
        Node(
            id="function:app/payment.py:charge",
            name="charge",
            node_type=NodeType.FUNCTION,
            path="app/payment.py",
            start_line=5,
            end_line=35,
            docstring="Process payment charge"
        ),
    ]
    store.insert_batch(nodes, [])
    return store


def test_ingest_generic_metrics(sample_store: GraphStore, tmp_path: Path):
    """Test ingestion of generic runtime metrics JSON."""
    metrics_file = tmp_path / "metrics.json"
    metrics_file.write_text(json.dumps({
        "metrics": [
            {"target": "login", "calls": 1500, "duration_ms": 7500.0, "errors": 15},
            {"target": "query_users", "calls": 5000, "duration_ms": 25000.0, "errors": 0},
        ]
    }), encoding="utf-8")

    ingester = TelemetryIngester(sample_store, tmp_path)
    res = ingester.ingest_file(metrics_file)

    assert res["ingested_records"] == 2
    login_telem = sample_store.get_telemetry_for_node("function:app/auth.py:login")
    assert login_telem is not None
    assert login_telem["call_count"] == 1500
    assert login_telem["avg_duration_ms"] == 5.0
    assert login_telem["error_count"] == 15
    assert login_telem["error_rate"] == 0.01


def test_ingest_otel_spans(sample_store: GraphStore, tmp_path: Path):
    """Test ingestion of OpenTelemetry trace spans with latency and error statuses."""
    otel_file = tmp_path / "otel_traces.json"
    otel_file.write_text(json.dumps({
        "resourceSpans": [
            {
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "name": "charge",
                                "startTimeUnixNano": 1000000000,
                                "endTimeUnixNano": 1150000000,  # 150ms
                                "status": {"code": 2},  # Error
                                "attributes": [{"key": "code.function", "value": {"stringValue": "charge"}}]
                            },
                            {
                                "name": "charge",
                                "startTimeUnixNano": 2000000000,
                                "endTimeUnixNano": 2050000000,  # 50ms
                                "status": {"code": 1},  # OK
                                "attributes": [{"key": "code.function", "value": {"stringValue": "charge"}}]
                            }
                        ]
                    }
                ]
            }
        ]
    }), encoding="utf-8")

    ingester = TelemetryIngester(sample_store, tmp_path)
    res = ingester.ingest_file(otel_file)

    assert res["format"] == "otel"
    charge_telem = sample_store.get_telemetry_for_node("function:app/payment.py:charge")
    assert charge_telem is not None
    assert charge_telem["call_count"] == 2
    assert charge_telem["avg_duration_ms"] == 100.0  # (150 + 50) / 2
    assert charge_telem["error_count"] == 1
    assert charge_telem["error_rate"] == 0.5


def test_ingest_pyspy_flamegraph(sample_store: GraphStore, tmp_path: Path):
    """Test ingestion of Py-Spy / speedscope flamegraph JSON frames."""
    flame_file = tmp_path / "flamegraph.json"
    flame_file.write_text(json.dumps({
        "version": "0.1.2",
        "frames": [
            {
                "name": "login",
                "file": "app/auth.py",
                "line": 12,
                "hits": 340,
                "selfTime": 1700.0
            }
        ]
    }), encoding="utf-8")

    ingester = TelemetryIngester(sample_store, tmp_path)
    res = ingester.ingest_file(flame_file)

    assert res["format"] == "pyspy"
    login_telem = sample_store.get_telemetry_for_node("function:app/auth.py:login")
    assert login_telem is not None
    assert login_telem["call_count"] == 340


def test_compute_heatmaps(sample_store: GraphStore, tmp_path: Path):
    """Verify calculation of composite heat scores and levels."""
    # Seed telemetry
    sample_store.save_telemetry_batch([
        {
            "node_id": "function:app/payment.py:charge",
            "call_count": 1000,
            "total_duration_ms": 50000.0,
            "avg_duration_ms": 50.0,
            "p95_duration_ms": 80.0,
            "error_count": 250,  # 25% error rate -> CRITICAL
            "error_rate": 0.25,
        },
        {
            "node_id": "function:app/db.py:query_users",
            "call_count": 10000,
            "total_duration_ms": 20000.0,
            "avg_duration_ms": 2.0,
            "p95_duration_ms": 3.0,
            "error_count": 0,
            "error_rate": 0.0,
        },
    ])

    ingester = TelemetryIngester(sample_store, tmp_path)
    heatmaps = ingester.compute_heatmaps(top_k=10)

    assert len(heatmaps) == 2
    # The error-ridden and high-latency charge function should have high heat
    charge_heat = next(h for h in heatmaps if h.node_id == "function:app/payment.py:charge")
    assert charge_heat.heat_level in ("CRITICAL", "HIGH")
    assert 0.0 <= charge_heat.composite_heat <= 1.0


def test_telemetry_cli_commands(sample_store: GraphStore, tmp_path: Path, capsys):
    """Test 'agtoosa telemetry' CLI commands."""
    metrics_file = tmp_path / "metrics.json"
    metrics_file.write_text(json.dumps({
        "metrics": [
            {"target": "login", "calls": 500, "duration_ms": 1000.0, "errors": 0}
        ]
    }), encoding="utf-8")

    # 1. Ingest
    args_ingest = argparse.Namespace(
        telem_action="ingest",
        file=str(metrics_file),
        format="generic"
    )
    assert cmd_telemetry(args_ingest, tmp_path) == 0
    captured = capsys.readouterr().out
    assert "Ingestion Complete" in captured

    # 2. Status
    args_status = argparse.Namespace(telem_action="status", json=False)
    assert cmd_telemetry(args_status, tmp_path) == 0
    captured_status = capsys.readouterr().out
    assert "Tracked Symbols / Nodes: 1" in captured_status

    # 3. Heatmap
    args_heat = argparse.Namespace(telem_action="heatmap", top=10, json=False)
    assert cmd_telemetry(args_heat, tmp_path) == 0
    captured_heat = capsys.readouterr().out
    assert "Runtime Execution Heatmap" in captured_heat
    assert "login" in captured_heat

    # 4. Clear
    args_clear = argparse.Namespace(telem_action="clear")
    assert cmd_telemetry(args_clear, tmp_path) == 0
    assert len(sample_store.get_all_telemetry()) == 0


def test_mcp_get_telemetry_heatmap(sample_store: GraphStore, tmp_path: Path):
    """Test MCPServer agtoosa_get_telemetry_heatmap tool."""
    server = MCPServer(tmp_path)
    res_str = server.handle_tool_call("agtoosa_get_telemetry_heatmap", {"top": 10})
    data = json.loads(res_str)
    assert isinstance(data, list)
