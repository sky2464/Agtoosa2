"""Tests for DEV-048: First-party deterministic community modularity optimizer."""

import pytest
from agtoosa.graph.community import detect_communities_modularity, compute_modularity


def test_sparse_graph_reports_unavailable():
    """AC-25: Insufficient structure reports unavailable rather than invented groups."""
    nodes = [{"id": "n1", "name": "Node1", "node_type": "function"}]
    edges = []
    res = detect_communities_modularity(nodes, edges)
    assert res["is_available"] is False
    assert "too small or too sparse" in res["reason"]
    assert res["communities"] == []


def test_ground_truth_modularity_partitions():
    """AC-24/25: Verify ground-truth partitioning on a two-clique graph with a bridge."""
    # Clique 1: c1_a, c1_b, c1_c
    # Clique 2: c2_a, c2_b, c2_c
    # Bridge edge: c1_c -> c2_a
    nodes = [
        {"id": "c1_a", "name": "c1_a", "node_type": "function"},
        {"id": "c1_b", "name": "c1_b", "node_type": "function"},
        {"id": "c1_c", "name": "c1_c", "node_type": "function"},
        {"id": "c2_a", "name": "c2_a", "node_type": "class"},
        {"id": "c2_b", "name": "c2_b", "node_type": "class"},
        {"id": "c2_c", "name": "c2_c", "node_type": "class"},
    ]
    edges = [
        {"source_id": "c1_a", "target_id": "c1_b"},
        {"source_id": "c1_b", "target_id": "c1_c"},
        {"source_id": "c1_c", "target_id": "c1_a"},
        {"source_id": "c2_a", "target_id": "c2_b"},
        {"source_id": "c2_b", "target_id": "c2_c"},
        {"source_id": "c2_c", "target_id": "c2_a"},
        {"source_id": "c1_c", "target_id": "c2_a"},  # Bridge
    ]

    res = detect_communities_modularity(nodes, edges, prefer_networkx=False)
    assert res["is_available"] is True
    assert res["algorithm"] == "greedy_modularity_core"
    assert res["modularity"] > 0.1  # Clear positive modularity

    comms = res["communities"]
    assert len(comms) == 2
    # Verify the two cliques are separated
    memberships = [set(c["members"]) for c in comms]
    assert {"c1_a", "c1_b", "c1_c"} in memberships
    assert {"c2_a", "c2_b", "c2_c"} in memberships


def test_deterministic_partitions():
    """AC-25: Partitions are deterministic across multiple executions."""
    nodes = [
        {"id": f"n{i}", "name": f"Node{i}", "node_type": "function"}
        for i in range(10)
    ]
    edges = [
        {"source_id": f"n{i}", "target_id": f"n{(i+1)%5}"}
        for i in range(5)
    ] + [
        {"source_id": f"n{i}", "target_id": f"n{5 + (i+1)%5}"}
        for i in range(5, 10)
    ] + [
        {"source_id": "n0", "target_id": "n5"}
    ]

    res1 = detect_communities_modularity(nodes, edges, prefer_networkx=False)
    res2 = detect_communities_modularity(nodes, edges, prefer_networkx=False)

    assert res1["modularity"] == res2["modularity"]
    assert len(res1["communities"]) == len(res2["communities"])
    for c1, c2 in zip(res1["communities"], res2["communities"]):
        assert c1["members"] == c2["members"]
