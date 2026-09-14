"""Tests for DEV-043: Versioned Explainable Interfaces & Contract Integrity."""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import pytest

from agtoosa.core.model import (
    ContractEnvelope,
    Citation,
    EvidenceClass,
    ResolutionStatus,
    Node,
    NodeType
)
from agtoosa.graph.embeddings import HashedFeatureEmbeddingEngine, SemanticEmbeddingEngine
from agtoosa.graph.store import GraphStore
from agtoosa.cli.graph_cmd import cmd_graph_capabilities, cmd_graph_verify


def test_contract_envelope_serialization():
    citation = Citation(
        path="agtoosa/parser/resolver.py",
        start_line=10,
        end_line=25,
        content_hash="abc123hash",
        snapshot_id="snap-001"
    )
    envelope = ContractEnvelope(
        contract_version="1.0.0",
        snapshot_id="snap-001",
        freshness="fresh",
        completeness="complete",
        resolution_status=ResolutionStatus.RESOLVED,
        data={"symbol": "SymbolResolver"},
        candidates=[{"id": "class:SymbolResolver", "path": "agtoosa/parser/resolver.py"}],
        citations=[citation],
        diagnostics=[]
    )

    d = envelope.to_dict()
    assert d["contract_version"] == "1.0.0"
    assert d["snapshot_id"] == "snap-001"
    assert d["freshness"] == "fresh"
    assert d["completeness"] == "complete"
    assert d["resolution_status"] == "resolved"
    assert len(d["citations"]) == 1
    assert d["citations"][0]["content_hash"] == "abc123hash"
    assert len(d["candidates"]) == 1
    assert d["candidates"][0]["id"] == "class:SymbolResolver"


def test_hashed_feature_embedding_labelling():
    """Verify embeddings are accurately identified as feature-hashed n-grams (R-08)."""
    engine = HashedFeatureEmbeddingEngine(dimension=64)
    assert engine.ALGORITHM == "feature_hashing_token_ngram"
    assert engine.EMBEDDING_TYPE == "hashed_feature"

    # Backward compatibility alias
    assert SemanticEmbeddingEngine is HashedFeatureEmbeddingEngine


def test_cmd_graph_capabilities(capsys):
    args_text = SimpleNamespace(json=False)
    exit_code = cmd_graph_capabilities(args_text, Path("."))
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Agtoosa2 Language & Parser Capabilities" in captured.out
    assert "Python" in captured.out
    assert "JavaScript / TypeScript" in captured.out

    args_json = SimpleNamespace(json=True)
    exit_code = cmd_graph_capabilities(args_json, Path("."))
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "summary" in data
    assert "capabilities" in data
    assert data["summary"]["total_families"] >= 10


def test_cmd_graph_verify_flow(capsys):
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        agtoosa_dir = workspace / ".agtoosa"
        agtoosa_dir.mkdir(parents=True)
        db_path = agtoosa_dir / "graph.db"

        # 1. Verification fails when graph.db is missing
        db_path_missing = workspace / ".agtoosa" / "nonexistent.db"
        args_json = SimpleNamespace(json=True)
        # Point to empty workspace without db
        workspace_empty = Path(temp_dir) / "empty"
        workspace_empty.mkdir()
        code = cmd_graph_verify(args_json, workspace_empty)
        assert code == 1
        captured = capsys.readouterr()
        res = json.loads(captured.out)
        assert res["freshness"] == "stale"
        assert res["resolution_status"] == "unresolved"

        # 2. Build a valid snapshot with a test source file
        src_file = workspace / "sample.py"
        src_file.write_text("def hello(): pass\n")

        from agtoosa.parser import ParserEngine
        store = GraphStore(db_path)
        engine = ParserEngine()
        engine.index_workspace(workspace, store)

        # 3. Verify on fresh graph succeeds
        code = cmd_graph_verify(args_json, workspace)
        assert code == 0
        captured = capsys.readouterr()
        res = json.loads(captured.out)
        assert res["freshness"] == "fresh"
        assert res["data"]["verified_files"] >= 1

        # 4. Modify source file -> verification detects stale drift
        src_file.write_text("def hello_modified(): pass\n")
        code = cmd_graph_verify(args_json, workspace)
        assert code == 1
        captured = capsys.readouterr()
        res = json.loads(captured.out)
        assert res["freshness"] == "stale"
        assert "sample.py" in res["data"]["stale_files"]
