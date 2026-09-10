"""Tests for High-Scale Performance & Streaming (DEV-008)."""

from pathlib import Path
import pytest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.query import compute_impact
from agtoosa.core.context_compiler import ContextCompiler


def test_streaming_nodes_and_edges(tmp_path: Path):
    db_path = tmp_path / "scale.db"
    store = GraphStore(db_path)

    # Insert 150 nodes and 149 edges
    nodes = []
    edges = []
    for i in range(150):
        nid = f"func:mod{i}:run"
        nodes.append(Node(id=nid, name=f"run{i}", node_type=NodeType.FUNCTION, path=f"mod{i}.py"))
        if i > 0:
            edges.append(Edge(source_id=f"func:mod{i-1}:run", target_id=nid, edge_type=EdgeType.CALLS))

    store.insert_batch(nodes, edges)

    # Stream nodes in chunks of 30
    node_chunks = list(store.stream_nodes(chunk_size=30))
    assert len(node_chunks) == 5
    all_streamed_nodes = [n for chunk in node_chunks for n in chunk]
    assert len(all_streamed_nodes) == 150
    assert {n["name"] for n in all_streamed_nodes} == {f"run{i}" for i in range(150)}

    # Stream edges in chunks of 30
    edge_chunks = list(store.stream_edges(chunk_size=30))
    assert len(edge_chunks) == 5  # 149 items in chunks of 30 => 5 chunks
    all_streamed_edges = [e for chunk in edge_chunks for e in chunk]
    assert len(all_streamed_edges) == 149
    assert all_streamed_edges[0]["source_id"] == "func:mod0:run"


def test_recursive_cte_compute_impact(tmp_path: Path):
    db_path = tmp_path / "impact.db"
    store = GraphStore(db_path)

    # A -> B -> C -> D
    nodes = [
        Node(id="func:a", name="func_a", node_type=NodeType.FUNCTION, path="a.py"),
        Node(id="func:b", name="func_b", node_type=NodeType.FUNCTION, path="b.py"),
        Node(id="func:c", name="func_c", node_type=NodeType.FUNCTION, path="c.py"),
        Node(id="func:d", name="func_d", node_type=NodeType.FUNCTION, path="d.py"),
        Node(id="func:iso", name="func_iso", node_type=NodeType.FUNCTION, path="iso.py"),
    ]
    edges = [
        Edge(source_id="func:a", target_id="func:b", edge_type=EdgeType.CALLS),
        Edge(source_id="func:b", target_id="func:c", edge_type=EdgeType.CALLS),
        Edge(source_id="func:c", target_id="func:d", edge_type=EdgeType.CALLS),
    ]
    store.insert_batch(nodes, edges)

    # Upstream blast radius if func_c is modified:
    # func_b calls func_c (depth 1)
    # func_a calls func_b (depth 2)
    impact_d1 = compute_impact(store, "func_c", max_depth=1)
    assert impact_d1 is not None
    reached_d1 = {item["id"] for item in impact_d1["impacted"]}
    assert reached_d1 == {"func:b"}
    assert impact_d1["impacted_count"] == 1

    # With depth 2, both func:b and func:a are impacted
    impact_d2 = compute_impact(store, "func_c", max_depth=2)
    assert impact_d2 is not None
    reached_d2 = {item["id"] for item in impact_d2["impacted"]}
    assert reached_d2 == {"func:b", "func:a"}
    assert impact_d2["impacted_count"] == 2


def test_recursive_cte_cycle_handling(tmp_path: Path):
    db_path = tmp_path / "cycle.db"
    store = GraphStore(db_path)

    # Cycle: X -> Y -> Z -> X
    nodes = [
        Node(id="func:x", name="func_x", node_type=NodeType.FUNCTION, path="x.py"),
        Node(id="func:y", name="func_y", node_type=NodeType.FUNCTION, path="y.py"),
        Node(id="func:z", name="func_z", node_type=NodeType.FUNCTION, path="z.py"),
    ]
    edges = [
        Edge(source_id="func:x", target_id="func:y", edge_type=EdgeType.CALLS),
        Edge(source_id="func:y", target_id="func:z", edge_type=EdgeType.CALLS),
        Edge(source_id="func:z", target_id="func:x", edge_type=EdgeType.CALLS),
    ]
    store.insert_batch(nodes, edges)

    # CTE should terminate without infinite loop and find cycle partners
    impact = compute_impact(store, "func_y", max_depth=5)
    assert impact is not None
    reached = {item["id"] for item in impact["impacted"]}
    assert reached == {"func:x", "func:z"}


def test_single_pass_fts_in_context_compiler(tmp_path: Path):
    db_path = tmp_path / "compiler.db"
    store = GraphStore(db_path)

    nodes = [
        Node(id="func:auth:login_user", name="login_user", node_type=NodeType.FUNCTION, path="auth.py", docstring="Authenticates user credentials"),
        Node(id="func:billing:charge_card", name="charge_card", node_type=NodeType.FUNCTION, path="billing.py", docstring="Processes credit card transaction"),
        Node(id="class:auth:TokenValidator", name="TokenValidator", node_type=NodeType.CLASS, path="validator.py", docstring="Validates JWT bearer token"),
    ]
    store.insert_batch(nodes, [])

    compiler = ContextCompiler(store)
    story = {"name": "User Authentication", "docstring": "Allow users to login securely with credentials"}
    criteria = [{"name": "AC-1", "docstring": "Card payment charge"}]
    tasks = []

    found = compiler._find_related_code_symbols(story, criteria, tasks)
    found_ids = {s["id"] for s in found}

    assert "func:auth:login_user" in found_ids
    assert "func:billing:charge_card" in found_ids
