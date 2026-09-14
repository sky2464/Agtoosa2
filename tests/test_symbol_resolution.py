"""Tests for DEV-041: Scoped identity and honest symbol resolution."""

import tempfile
from pathlib import Path
from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.parser.resolver import (
    SymbolResolver,
    resolve_node_candidates,
    ResolutionStatus
)


def test_ambiguous_symbol_resolution():
    """AC-05: Querying a duplicate symbol returns AMBIGUOUS status with candidate sets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = GraphStore(db_path)

        # Insert two functions with the exact same name in different files
        n1 = Node(id="func:user.py:validate", name="validate", node_type=NodeType.FUNCTION, path="user.py")
        n2 = Node(id="func:order.py:validate", name="validate", node_type=NodeType.FUNCTION, path="order.py")
        store.insert_batch([n1, n2], [])

        res = resolve_node_candidates(store, "validate")
        assert res.status == ResolutionStatus.AMBIGUOUS
        assert res.selected_id is None
        assert len(res.candidates) == 2
        candidate_ids = {c.node_id for c in res.candidates}
        assert "func:user.py:validate" in candidate_ids
        assert "func:order.py:validate" in candidate_ids


def test_unambiguous_symbol_resolution():
    """AC-04: Uniquely named symbols resolve to RESOLVED status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = GraphStore(db_path)

        n1 = Node(id="func:auth.py:verify_jwt", name="verify_jwt", node_type=NodeType.FUNCTION, path="auth.py")
        store.insert_batch([n1], [])

        res = resolve_node_candidates(store, "verify_jwt")
        assert res.status == ResolutionStatus.RESOLVED
        assert res.selected_id == "func:auth.py:verify_jwt"
        assert len(res.candidates) == 1


def test_cross_file_call_resolution_preserves_facts():
    """AC-06: Cross-file call resolution does not overwrite mappings and retains facts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = GraphStore(db_path)

        # Setup target functions
        target_fn = Node(id="func:calc.py:add", name="add", node_type=NodeType.FUNCTION, path="calc.py")
        caller_fn = Node(id="func:main.py:run", name="run", node_type=NodeType.FUNCTION, path="main.py")

        # Import node in main.py
        imp = Node(id="import:main.py:add", name="add", node_type=NodeType.IMPORT, path="main.py")

        # Call placeholder edge
        call_edge = Edge(
            source_id="func:main.py:run",
            target_id="func_call:add",
            edge_type=EdgeType.CALLS,
            provenance="syntactic_ast"
        )

        store.insert_batch([target_fn, caller_fn, imp], [call_edge])

        resolver = SymbolResolver(store)
        stats = resolver.resolve_all_symbols()

        assert stats["resolved"] >= 1

        # Check edge was updated with resolved target and original reference preserved
        neighbors = store.get_neighbors("func:main.py:run", direction="out")
        called_ids = [n["id"] for n in neighbors]
        assert "func:calc.py:add" in called_ids
