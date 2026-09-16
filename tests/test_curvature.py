"""Automated mathematical tests for CurvatureEngine and Discrete Differential Geometry."""

import pytest
from agtoosa.graph.curvature import CurvatureEngine


def test_clique_positive_curvature():
    """Verify that every edge in a complete graph K_4 has positive Forman-Ricci curvature."""
    nodes = [{"id": n} for n in ["A", "B", "C", "D"]]
    edges = [
        {"source_id": "A", "target_id": "B"},
        {"source_id": "A", "target_id": "C"},
        {"source_id": "A", "target_id": "D"},
        {"source_id": "B", "target_id": "C"},
        {"source_id": "B", "target_id": "D"},
        {"source_id": "C", "target_id": "D"},
    ]

    engine = CurvatureEngine(nodes, edges)
    res = engine.compute_forman_ricci_curvature()

    assert res["bottleneck_count"] == 0
    assert res["cluster_edge_count"] == 6

    # For K_4: deg(u)=3, deg(v)=3, triangles=2
    # Ric_F = 4 - 3 - 3 + 3*2 = +4
    for e in res["all_curvatures"]:
        assert e["curvature"] == 4


def test_bridge_negative_curvature():
    """Verify that a bridge edge connecting two triangles has negative Forman-Ricci curvature."""
    nodes = [{"id": n} for n in ["A", "B", "C", "D", "E", "F"]]
    edges = [
        # Triangle 1
        {"source_id": "A", "target_id": "B"},
        {"source_id": "B", "target_id": "C"},
        {"source_id": "C", "target_id": "A"},
        # Bridge edge between C and D
        {"source_id": "C", "target_id": "D"},
        # Triangle 2
        {"source_id": "D", "target_id": "E"},
        {"source_id": "E", "target_id": "F"},
        {"source_id": "F", "target_id": "D"},
    ]

    engine = CurvatureEngine(nodes, edges)
    res = engine.compute_forman_ricci_curvature()

    # For bridge (C, D): deg(C)=3, deg(D)=3, triangles=0
    # Ric_F(C, D) = 4 - 3 - 3 + 0 = -2 (negative curvature bottleneck!)
    bridge = next(e for e in res["all_curvatures"] if set([e["source"], e["target"]]) == {"C", "D"})
    assert bridge["curvature"] == -2
    assert res["bottleneck_count"] >= 1
    assert res["top_bottlenecks"][0]["curvature"] == -2


def test_tree_gromov_hyperbolicity():
    """Verify that a tree graph has Gromov delta-hyperbolicity delta = 0."""
    nodes = [{"id": n} for n in ["Root", "Child1", "Child2", "Leaf11", "Leaf12"]]
    edges = [
        {"source_id": "Root", "target_id": "Child1"},
        {"source_id": "Root", "target_id": "Child2"},
        {"source_id": "Child1", "target_id": "Leaf11"},
        {"source_id": "Child1", "target_id": "Leaf12"},
    ]

    engine = CurvatureEngine(nodes, edges)
    res = engine.compute_gromov_hyperbolicity()

    assert res["delta"] == 0.0
    assert res["is_tree_like"] is True
