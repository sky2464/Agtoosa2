"""Automated mathematical tests for the Spectral and Algebraic Graph Engine."""

import pytest
from agtoosa.graph.spectral import SpectralEngine


def test_spectral_barbell_cheeger_cut():
    """Verify Cheeger cut on a barbell graph (two triangles joined by a bridge).

    Graph: Triangle 1 (A-B-C), Triangle 2 (D-E-F), Bridge (C-D).
    """
    nodes = [{"id": n} for n in ["A", "B", "C", "D", "E", "F"]]
    edges = [
        # Triangle 1
        {"source_id": "A", "target_id": "B"},
        {"source_id": "B", "target_id": "C"},
        {"source_id": "C", "target_id": "A"},
        # Bridge
        {"source_id": "C", "target_id": "D"},
        # Triangle 2
        {"source_id": "D", "target_id": "E"},
        {"source_id": "E", "target_id": "F"},
        {"source_id": "F", "target_id": "D"},
    ]

    engine = SpectralEngine(nodes, edges)
    fiedler_res = engine.compute_fiedler_cut()

    assert fiedler_res["is_connected"] is True
    assert fiedler_res["algebraic_connectivity"] > 0.0

    # Verify Cheeger's Inequality: lambda_2 / 2 <= h(G) <= sqrt(2 * lambda_2) + eps
    cond = fiedler_res["cheeger_conductance"]
    l2 = fiedler_res["algebraic_connectivity"]
    assert cond >= (l2 / 2.0) - 1e-4
    assert cond <= fiedler_res["cheeger_upper_bound"] + 1e-4

    # The cut partition should cleanly separate Triangle 1 from Triangle 2
    part1, part2 = fiedler_res["cut_partition"]
    t1 = {"A", "B", "C"}
    t2 = {"D", "E", "F"}
    assert (set(part1) == t1 and set(part2) == t2) or (set(part1) == t2 and set(part2) == t1)


def test_spectral_radius_directed_cycle():
    """Verify Perron-Frobenius spectral radius on a directed cycle A -> B -> C -> D -> A."""
    nodes = [{"id": n} for n in ["A", "B", "C", "D"]]
    edges = [
        {"source_id": "A", "target_id": "B"},
        {"source_id": "B", "target_id": "C"},
        {"source_id": "C", "target_id": "D"},
        {"source_id": "D", "target_id": "A"},
    ]

    engine = SpectralEngine(nodes, edges)
    sr = engine.compute_spectral_radius()

    # The spectral radius of a simple directed cycle with unit weights is exactly 1.0
    assert abs(sr["spectral_radius"] - 1.0) < 1e-3
    assert abs(sr["epidemic_threshold"] - 1.0) < 1e-3


def test_resolvent_blast_radius():
    """Verify continuous resolvent perturbation kernel decays along directed path."""
    nodes = [{"id": n} for n in ["A", "B", "C", "D"]]
    edges = [
        {"source_id": "A", "target_id": "B"},
        {"source_id": "B", "target_id": "C"},
        {"source_id": "C", "target_id": "D"},
    ]

    engine = SpectralEngine(nodes, edges)
    res = engine.compute_resolvent_impact("D")  # D is called by C, which is called by B, which is called by A

    # Downstream callers should have decaying shockwave intensity
    impacted = {item["id"]: item["shockwave_intensity"] for item in res["impacted"]}
    assert "C" in impacted
    assert "B" in impacted
    assert "A" in impacted
    assert impacted["C"] > impacted["B"] > impacted["A"]


def test_minimum_feedback_arc_set():
    """Verify Eades-Lin-Smyth FAS breaks cycles to form a strict DAG."""
    nodes = [{"id": n} for n in ["A", "B", "C"]]
    edges = [
        {"source_id": "A", "target_id": "B"},
        {"source_id": "B", "target_id": "C"},
        {"source_id": "C", "target_id": "A"},  # Back edge causing cycle
    ]

    engine = SpectralEngine(nodes, edges)
    fas = engine.compute_minimum_feedback_arc_set()

    assert fas["feedback_arc_count"] == 1
    # Exactly 1 feedback edge removed breaks the cycle
    assert len(fas["feedback_arcs"]) == 1


def test_transitive_reduction():
    """Verify Hasse diagram computation strips redundant transitive edges."""
    nodes = [{"id": n} for n in ["A", "B", "C"]]
    edges = [
        {"source_id": "A", "target_id": "B"},
        {"source_id": "B", "target_id": "C"},
        {"source_id": "A", "target_id": "C"},  # Redundant transitive edge
    ]

    engine = SpectralEngine(nodes, edges)
    tr = engine.compute_transitive_reduction()

    assert tr["redundant_edge_count"] == 1
    assert tr["redundant_edges"][0] == {"source": "A", "target": "C"}
    assert tr["essential_edge_count"] == 2


def test_von_neumann_entropy():
    """Verify Von Neumann entropy increases with structural heterogeneity."""
    nodes1 = [{"id": n} for n in ["A", "B"]]
    edges1 = [{"source_id": "A", "target_id": "B"}]
    e1 = SpectralEngine(nodes1, edges1).compute_von_neumann_entropy()

    # More nodes with varying connectivity has higher entropy
    nodes2 = [{"id": n} for n in ["A", "B", "C", "D", "E", "F"]]
    edges2 = [
        {"source_id": "A", "target_id": "B"},
        {"source_id": "A", "target_id": "C"},
        {"source_id": "A", "target_id": "D"},
        {"source_id": "B", "target_id": "E"},
    ]
    e2 = SpectralEngine(nodes2, edges2).compute_von_neumann_entropy()

    assert e2 > e1
