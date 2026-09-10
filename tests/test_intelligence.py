"""Tests for Review Intelligence & Architecture Drift Alarms (DEV-010)."""

from pathlib import Path
import pytest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.review.intelligence import ReviewIntelligenceEngine, DriftFinding
from agtoosa.review.memory import ArchitecturalMemory
from agtoosa.core.context_compiler import ContextCompiler


def test_layer_boundary_violation(tmp_path: Path):
    db_path = tmp_path / "layer.db"
    store = GraphStore(db_path)

    # Tier 3 (Core domain model) importing Tier 1 (CLI entrypoint)
    nodes = [
        Node(id="file:agtoosa/core/model.py", name="model.py", node_type=NodeType.FILE, path="agtoosa/core/model.py"),
        Node(id="file:agtoosa/cli/main.py", name="main.py", node_type=NodeType.FILE, path="agtoosa/cli/main.py"),
    ]
    edges = [
        Edge(source_id="file:agtoosa/core/model.py", target_id="file:agtoosa/cli/main.py", edge_type=EdgeType.IMPORTS)
    ]
    store.insert_batch(nodes, edges)

    engine = ReviewIntelligenceEngine(store, tmp_path)
    findings = engine.check_layer_invariants()

    assert len(findings) >= 1
    assert findings[0].category == "LAYER_VIOLATION"
    assert findings[0].severity == "ERROR"
    assert "Tier 3" in findings[0].message
    assert "Tier 1" in findings[0].message


def test_cycle_detection_alarm(tmp_path: Path):
    db_path = tmp_path / "cycle.db"
    store = GraphStore(db_path)

    # A -> B -> C -> A
    nodes = [
        Node(id="mod_a", name="mod_a", node_type=NodeType.MODULE, path="a.py"),
        Node(id="mod_b", name="mod_b", node_type=NodeType.MODULE, path="b.py"),
        Node(id="mod_c", name="mod_c", node_type=NodeType.MODULE, path="c.py"),
    ]
    edges = [
        Edge(source_id="mod_a", target_id="mod_b", edge_type=EdgeType.IMPORTS),
        Edge(source_id="mod_b", target_id="mod_c", edge_type=EdgeType.IMPORTS),
        Edge(source_id="mod_c", target_id="mod_a", edge_type=EdgeType.IMPORTS),
    ]
    store.insert_batch(nodes, edges)

    engine = ReviewIntelligenceEngine(store, tmp_path)
    findings = engine.check_cycles()

    assert len(findings) >= 1
    assert findings[0].category == "CYCLE"
    assert findings[0].severity == "ERROR"


def test_blast_radius_warning(tmp_path: Path):
    db_path = tmp_path / "blast.db"
    store = GraphStore(db_path)

    target_file = "core/utils.py"
    nodes = [
        Node(id=f"file:{target_file}", name="utils.py", node_type=NodeType.FILE, path=target_file)
    ]
    edges = []

    # 6 callers depending on target_file
    for i in range(6):
        caller_id = f"file:module_{i}.py"
        nodes.append(Node(id=caller_id, name=f"module_{i}.py", node_type=NodeType.FILE, path=f"module_{i}.py"))
        edges.append(Edge(source_id=caller_id, target_id=f"file:{target_file}", edge_type=EdgeType.IMPORTS))

    store.insert_batch(nodes, edges)

    engine = ReviewIntelligenceEngine(store, tmp_path)
    findings = engine.check_blast_radius([target_file], max_impact_threshold=5)

    assert len(findings) == 1
    assert findings[0].category == "BLAST_RADIUS"
    assert findings[0].severity == "WARNING"
    assert "6 upstream dependents" in findings[0].message


def test_review_pipeline_verdicts(tmp_path: Path):
    db_path = tmp_path / "verdict.db"
    store = GraphStore(db_path)

    # Clean workspace -> APPROVED
    clean_nodes = [
        Node(id="file:main.py", name="main.py", node_type=NodeType.FILE, path="main.py")
    ]
    store.insert_batch(clean_nodes, [])

    engine = ReviewIntelligenceEngine(store, tmp_path)
    report_clean = engine.review(modified_files=["main.py"])
    assert report_clean.verdict == "APPROVED"

    # Unindexed file -> WARNING
    report_unindexed = engine.review(modified_files=["ghost.py"])
    assert report_unindexed.verdict == "WARNING"
    assert any(f.category == "UNLINKED_CODE" for f in report_unindexed.findings)


def test_architectural_memory_and_context_injection(tmp_path: Path):
    db_path = tmp_path / "memory.db"
    store = GraphStore(db_path)

    memory = ArchitecturalMemory(store)

    # Store a design rule
    rule_node = memory.remember(
        lesson="Never allow circular dependencies between parser and core.",
        domain="parser",
        tags=["architecture", "no-cycles"]
    )
    assert rule_node.id.startswith("concept:memory:")

    # Retrieve rules
    all_rules = memory.reflect()
    assert len(all_rules) >= 1
    assert "circular dependencies" in all_rules[0]["rule"]

    # Test relevant rule query
    relevant = memory.get_relevant_rules("parser")
    assert len(relevant) >= 1

    # Verify context pack integration
    story_node = Node(id="DEV-100", name="Parser Subsystem Refactor", node_type=NodeType.STORY, path="docs/story.md")
    store.insert_batch([story_node], [])

    compiler = ContextCompiler(store)
    pack = compiler.compile_context("DEV-100")
    assert pack is not None
    assert "Architectural Invariants & Memory" in pack
    assert "Never allow circular dependencies between parser and core." in pack
