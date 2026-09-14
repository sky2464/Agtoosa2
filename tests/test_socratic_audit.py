"""Unit tests for DEV-036: Socratic Architecture Audit & 1-Click Blueprints."""

import json
from pathlib import Path
import pytest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.review.socratic_audit import SocraticAuditEngine, GodNode
from agtoosa.cli.main import main


@pytest.fixture
def audit_store(tmp_path: Path):
    db_path = tmp_path / ".agtoosa" / "graph.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = GraphStore(db_path)

    # 1. God node setup (e.g. CentralHub called by many nodes)
    hub = Node(id="code:CentralHub", name="CentralHub", node_type=NodeType.CLASS, path="core/hub.py")
    callers = [
        Node(id=f"code:Service_{i}", name=f"Service_{i}", node_type=NodeType.CLASS, path=f"services/s_{i}.py")
        for i in range(6)
    ]
    nodes = [hub] + callers

    edges = [
        Edge(source_id=f"code:Service_{i}", target_id="code:CentralHub", edge_type=EdgeType.CALLS)
        for i in range(6)
    ]

    # 2. Cycle setup (Service_0 <-> Service_1)
    edges.append(Edge(source_id="code:Service_0", target_id="code:Service_1", edge_type=EdgeType.CALLS))
    edges.append(Edge(source_id="code:Service_1", target_id="code:Service_0", edge_type=EdgeType.CALLS))

    # 3. Cross-modality doc setup (Doc referencing code symbol with NO test)
    doc_node = Node(id="doc:specs/payment.md", name="payment.md", node_type=NodeType.DOC, path="specs/payment.md")
    untested_fn = Node(id="code:process_payment", name="process_payment", node_type=NodeType.FUNCTION, path="pay/process.py")
    nodes.extend([doc_node, untested_fn])

    edges.append(Edge(source_id="doc:specs/payment.md", target_id="code:process_payment", edge_type=EdgeType.REFERENCES))

    store.insert_batch(nodes, edges)
    return store, tmp_path


def test_god_node_detection(audit_store):
    store, root = audit_store
    engine = SocraticAuditEngine(store, root)

    god_nodes = engine.detect_god_nodes(degree_threshold=5)
    assert len(god_nodes) >= 1
    hub = next(g for g in god_nodes if g.name == "CentralHub")
    assert hub.in_degree == 6
    assert hub.category == "AFFERENT_HUB"
    assert "Socratic Inquiry" in hub.socratic_prompt
    assert hub.decoupling_blueprint is not None


def test_cross_modality_couplings(audit_store):
    store, root = audit_store
    engine = SocraticAuditEngine(store, root)

    couplings = engine.audit_cross_modality_couplings()
    assert len(couplings) >= 1
    c = couplings[0]
    assert c.target_code_name == "process_payment"
    assert c.has_test_coverage is False
    assert c.risk_level == "HIGH"
    assert "Socratic Inquiry" in c.socratic_prompt


def test_audit_report_generation(audit_store):
    store, root = audit_store
    engine = SocraticAuditEngine(store, root)

    out_file = root / "GRAPH_REPORT.md"
    res = engine.write_report(output_path=out_file, format="markdown")

    assert out_file.exists()
    assert res["total_alarms"] >= 2

    content = out_file.read_text(encoding="utf-8")
    assert "Socratic Architecture Audit Report" in content
    assert "CentralHub" in content
    assert "AFFERENT_HUB" in content
    assert "process_payment" in content


def test_cli_audit(audit_store, capsys):
    store, root = audit_store

    exit_code = main(["-C", str(root), "audit", "--json"])
    assert exit_code == 0

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["total_alarms"] >= 2
    assert len(report["god_nodes"]) >= 1
