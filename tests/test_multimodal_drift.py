"""Tests for DEV-033: Multimodal Knowledge Ingestion & Visual-to-Code Architecture Drift Verification."""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import pytest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.parser.multimodal.diagram_parser import DiagramParser
from agtoosa.parser.multimodal.doc_ingester import DocumentIngester
from agtoosa.graph.visual_drift import VisualDriftDetector
from agtoosa.cli.graph_cmd import cmd_ingest, cmd_graph_drift_visual


def test_diagram_parser_mermaid():
    """Verify Mermaid parsing extracts visual nodes and references edges."""
    parser = DiagramParser()
    mermaid_text = """
    graph TD
        Client["Web Client"] --> Gateway["API Gateway"]
        Gateway --> AuthService["Authentication Service"]
        Gateway --> BillingService["Billing Service"]
    """
    nodes, edges = parser.parse_mermaid(mermaid_text, "docs/arch.mmd")
    assert len(nodes) == 4
    names = {n.name for n in nodes}
    assert "Web Client" in names
    assert "Authentication Service" in names
    assert len(edges) == 3
    assert all(e.edge_type == EdgeType.REFERENCES for e in edges)


def test_diagram_parser_plantuml():
    """Verify PlantUML parsing extracts components and relationships."""
    parser = DiagramParser()
    puml_text = """
    @startuml
    component [PaymentProcessor] as Pay
    component [FraudEngine] as Fraud
    Pay --> Fraud : checks
    @enduml
    """
    nodes, edges = parser.parse_plantuml(puml_text, "docs/arch.puml")
    assert len(nodes) == 2
    names = {n.name for n in nodes}
    assert "PaymentProcessor" in names
    assert "FraudEngine" in names
    assert len(edges) == 1
    assert edges[0].metadata.get("label") == "checks"


def test_document_ingester_markdown():
    """Verify Markdown ingestion creates doc and section nodes."""
    ingester = DocumentIngester()
    with tempfile.TemporaryDirectory() as temp_dir:
        md_file = Path(temp_dir) / "spec.md"
        md_file.write_text("# Master Spec\n\n## Architecture Overview\nDetails here.\n\n## Security Policies\nPolicy details.\n")
        nodes, edges = ingester.ingest_markdown(md_file, Path(temp_dir))
        assert len(nodes) == 3  # Doc + 2 sections
        assert nodes[0].node_type == NodeType.DOC
        assert nodes[0].name == "Master Spec"
        sec_names = {n.name for n in nodes[1:]}
        assert "Architecture Overview" in sec_names
        assert "Security Policies" in sec_names
        assert len(edges) == 2


def test_visual_drift_detector_ghost_and_mismatch():
    """Verify VisualDriftDetector flags ghost nodes and connection mismatches."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_graph.db"
        store = GraphStore(db_path)

        # 1. Real code nodes
        code_auth = Node(id="class:app/auth.py:AuthService", name="AuthService", node_type=NodeType.CLASS, path="app/auth.py")
        code_billing = Node(id="class:app/billing.py:BillingService", name="BillingService", node_type=NodeType.CLASS, path="app/billing.py")
        # Real code edge: AuthService calls BillingService
        store.insert_batch([code_auth, code_billing], [Edge(source_id=code_auth.id, target_id=code_billing.id, edge_type=EdgeType.CALLS)])

        # 2. Visual diagram nodes:
        # - AuthService (matches code)
        # - BillingService (matches code)
        # - GhostAnalytics (GHOST: not in code!)
        vis_auth = Node(id="visual:arch.mmd:auth", name="AuthService", node_type=NodeType.CONCEPT, path="docs/arch.mmd", metadata={"is_visual": True})
        vis_billing = Node(id="visual:arch.mmd:billing", name="BillingService", node_type=NodeType.CONCEPT, path="docs/arch.mmd", metadata={"is_visual": True})
        vis_ghost = Node(id="visual:arch.mmd:ghost", name="GhostAnalytics", node_type=NodeType.CONCEPT, path="docs/arch.mmd", metadata={"is_visual": True})

        # Visual diagram edges:
        # - Billing -> Auth (MISMATCH: code only has Auth -> Billing)
        vis_edge = Edge(source_id=vis_billing.id, target_id=vis_auth.id, edge_type=EdgeType.REFERENCES, metadata={"is_visual": True})

        store.insert_batch([vis_auth, vis_billing, vis_ghost], [vis_edge])

        detector = VisualDriftDetector(store)
        report = detector.detect_drift()

        assert report["drift_detected"] is True
        assert report["total_ghost_nodes"] == 1
        assert report["ghost_nodes"][0]["name"] == "GhostAnalytics"
        assert report["total_path_mismatches"] == 1
        assert "BillingService -> AuthService" in report["path_mismatches"][0]["visual_edge"]


def test_cli_ingest_and_drift_flow(capsys):
    """Verify CLI flow for agtoosa ingest and agtoosa graph drift visual."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        agtoosa_dir = workspace / ".agtoosa"
        agtoosa_dir.mkdir(parents=True)
        db_path = agtoosa_dir / "graph.db"
        store = GraphStore(db_path)

        # Create a diagram file
        diag_file = workspace / "architecture.mmd"
        diag_file.write_text("graph TD\n    OrderAPI --> OrderDB\n")

        # Ingest diagram via CLI
        args_ingest = SimpleNamespace(target="architecture.mmd", json=True)
        rc_ingest = cmd_ingest(args_ingest, workspace)
        assert rc_ingest == 0
        captured = capsys.readouterr()
        res_ingest = json.loads(captured.out)
        assert res_ingest["nodes_ingested"] >= 2

        # Check drift
        args_drift = SimpleNamespace(strict=False, json=True)
        rc_drift = cmd_graph_drift_visual(args_drift, workspace)
        assert rc_drift == 0
        captured = capsys.readouterr()
        res_drift = json.loads(captured.out)
        assert res_drift["drift_detected"] is True  # OrderAPI and OrderDB are ghost nodes
        assert res_drift["total_ghost_nodes"] >= 2
