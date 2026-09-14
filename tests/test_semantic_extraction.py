"""Unit tests for DEV-035: Zero-Trust Multi-Agent Semantic Extraction & Hallucination Guard."""

import json
from pathlib import Path
import pytest

from agtoosa.core.model import Node, NodeType
from agtoosa.graph.store import GraphStore
from agtoosa.semantic.guard import (
    ProvenanceConfidence,
    levenshtein_distance,
    HallucinationGuard,
    SemanticExtractionEngine,
)
from agtoosa.cli.main import main


def test_levenshtein_distance():
    assert levenshtein_distance("kitten", "sitting") == 3
    assert levenshtein_distance("AuthService", "AuthService") == 0
    assert levenshtein_distance("validate_token", "verify_token") == 6
    assert levenshtein_distance("verifyJwtToken", "validate_token") > 0


@pytest.fixture
def test_env(tmp_path: Path):
    db_path = tmp_path / ".agtoosa" / "graph.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = GraphStore(db_path)

    # Insert known ground-truth code symbols
    code_nodes = [
        Node(id="code:AuthService", name="AuthService", node_type=NodeType.CLASS, path="auth/service.py"),
        Node(id="code:validate_token", name="validate_token", node_type=NodeType.FUNCTION, path="auth/service.py"),
        Node(id="code:UserRepository", name="UserRepository", node_type=NodeType.CLASS, path="db/repo.py"),
    ]
    store.insert_batch(code_nodes, [])

    # Create documentation directory
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    doc1 = docs_dir / "architecture.md"
    doc1.write_text(
        "# Authentication Architecture\n\n"
        "The system authenticates users via `AuthService` and calls `validate_token`.\n"
        "Legacy services attempted calling `verifyJwtToken` which is an invalid hallucination.\n"
    )

    return store, tmp_path, docs_dir


def test_hallucination_guard_grounding(test_env):
    store, root, _ = test_env
    guard = HallucinationGuard(store)

    # Test 1: Grounded valid symbol
    val_valid = guard.validate_edge("doc:architecture.md", "code:AuthService", "references")
    assert val_valid.is_valid is True
    assert val_valid.status == "VERIFIED_GROUNDED"

    # Test 2: Hallucinated / non-existent symbol
    val_hallucinated = guard.validate_edge("doc:architecture.md", "code:verifyJwtToken", "references")
    assert val_hallucinated.is_valid is False
    assert val_hallucinated.status == "HALLUCINATED_UNVERIFIED"
    assert val_hallucinated.suggested_target is not None


def test_semantic_extraction_incremental_cache(test_env):
    store, root, docs_dir = test_env
    engine = SemanticExtractionEngine(store, root)

    doc_file = docs_dir / "architecture.md"

    # First run (uncached)
    res1 = engine.extract_document(doc_file, strict_grounding=False)
    assert res1["cached"] is False
    assert res1["nodes_created"] == 1
    assert res1["edges_created"] >= 1
    assert res1["hallucinations_blocked"] >= 1

    # Second run (cached)
    res2 = engine.extract_document(doc_file, strict_grounding=False)
    assert res2["cached"] is True


def test_batch_extraction_and_cli(test_env, capsys):
    store, root, docs_dir = test_env

    # Run CLI: agtoosa extract semantic
    exit_code = main(["-C", str(root), "extract", "semantic", "-d", str(docs_dir), "--json"])
    assert exit_code == 0

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["total_files"] == 1
    assert report["edges_created"] >= 1
    assert report["hallucinations_blocked"] >= 1
