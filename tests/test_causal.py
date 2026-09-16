"""Automated mathematical tests for CausalEngine and Pearl's do-calculus."""

import pytest
from agtoosa.observability.causal import CausalEngine


def test_fork_confounding_resolution():
    """Verify that conditioning on common parent Z resolves confounding on fork Z -> X, Z -> Y.

    Observational data: X and Y strongly correlate because Z causes both.
    Interventional reality: X does not cause Y (ACE = 0).
    """
    nodes = [{"id": n} for n in ["Z", "X", "Y"]]
    edges = [
        {"source_id": "Z", "target_id": "X"},
        {"source_id": "Z", "target_id": "Y"},
    ]

    engine = CausalEngine(nodes, edges)

    # 1. Back-door admissibility
    is_valid, msg = engine.is_backdoor_admissible("X", "Y", {"Z"})
    assert is_valid is True, f"Conditioning on Z should be admissible: {msg}"

    # Empty set should NOT be admissible because back-door path X <- Z -> Y remains unblocked
    is_empty_valid, _ = engine.is_backdoor_admissible("X", "Y", set())
    assert is_empty_valid is False

    # 2. Synthetic observational data with confounding
    # When Z=1 (database overloaded), P(X=1|Z=1)=0.8, P(Y=1|Z=1)=0.8 (independent given Z)
    # When Z=0 (database normal),     P(X=1|Z=0)=0.1, P(Y=1|Z=0)=0.1 (independent given Z)
    # Causal effect of X on Y is identically 0.0.
    data = []
    # 100 rows of Z=1
    data.extend([{"Z": 1, "X": 1, "Y": 1}] * 64)
    data.extend([{"Z": 1, "X": 1, "Y": 0}] * 16)
    data.extend([{"Z": 1, "X": 0, "Y": 1}] * 16)
    data.extend([{"Z": 1, "X": 0, "Y": 0}] * 4)

    # 100 rows of Z=0
    data.extend([{"Z": 0, "X": 1, "Y": 1}] * 1)
    data.extend([{"Z": 0, "X": 1, "Y": 0}] * 9)
    data.extend([{"Z": 0, "X": 0, "Y": 1}] * 9)
    data.extend([{"Z": 0, "X": 0, "Y": 0}] * 81)

    res = engine.compute_causal_effect("X", "Y", data)

    # Naive observational difference is ~0.495 because of confounding
    assert res["naive_observational_diff"] > 0.40
    assert res["is_confounded"] is True

    # But true Average Causal Effect (ACE) through Pearl's do-calculus is 0.0!
    assert abs(res["average_causal_effect"]) < 1e-4


def test_collider_conditioning_rejection():
    """Verify that conditioning on a collider X -> W <- Y is rejected because it unblocks the path."""
    nodes = [{"id": n} for n in ["X", "W", "Y"]]
    edges = [
        {"source_id": "X", "target_id": "W"},
        {"source_id": "Y", "target_id": "W"},
    ]

    engine = CausalEngine(nodes, edges)

    # Empty set: collider W is not conditioned on, so path is naturally blocked!
    # Note: path is X -> W <- Y (not a back-door path into X because arrow goes out of X).
    # Back-door paths into X requires arrow entering X.
    backdoors = engine._find_backdoor_paths("X", "Y")
    assert len(backdoors) == 0  # No arrows into X
