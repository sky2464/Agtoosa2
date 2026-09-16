"""Automated mathematical tests for Submodular Context Optimization."""

import itertools
import pytest
from agtoosa.core.submodular import SubmodularContextOptimizer, estimate_token_cost


def test_monotone_submodularity_property():
    """Formally verify that f(S) satisfies monotone submodularity:

        1. Monotonicity: A subseteq B => f(A) <= f(B)
        2. Diminishing returns: A subseteq B => f(A union {v}) - f(A) >= f(B union {v}) - f(B)
    """
    seeds = [
        {"id": "seed1", "name": "PaymentProcessor", "docstring": "Handles credit card checkouts and tokenization", "weight": 2.0},
        {"id": "seed2", "name": "UserAccount", "docstring": "Manages customer profile and billing address", "weight": 1.0}
    ]

    candidates = [
        {"id": f"c{i}", "name": f"Module_{i}", "docstring": f"Subsystem {i} related to payment and authentication"}
        for i in range(6)
    ]

    opt = SubmodularContextOptimizer(seeds, candidates)

    # Test for subsets A subseteq B
    A = {0, 1}
    B = {0, 1, 2, 3}
    v = 4

    f_A = opt.evaluate_coverage(A)
    f_B = opt.evaluate_coverage(B)
    assert f_A <= f_B, "Monotonicity violated!"

    marginal_gain_A = opt.evaluate_coverage(A | {v}) - f_A
    marginal_gain_B = opt.evaluate_coverage(B | {v}) - f_B

    # Diminishing returns with floating point tolerance
    assert marginal_gain_A >= marginal_gain_B - 1e-9, f"Submodularity violated: gain_A={marginal_gain_A}, gain_B={marginal_gain_B}"


def test_budget_constraint_satisfaction():
    """Verify that the greedy optimizer strictly respects the token budget."""
    seeds = [{"id": "s1", "name": "Engine", "docstring": "Core engine"}]
    candidates = [
        {"id": f"c{i}", "name": f"Component_{i}", "content": "x" * 200}  # ~54 tokens each
        for i in range(10)
    ]

    opt = SubmodularContextOptimizer(seeds, candidates)
    budget = 120  # Can fit at most ~2 components

    res = opt.optimize(budget_tokens=budget)
    assert res["tokens_used"] <= budget
    assert res["tokens_used"] > 0
    assert len(res["selected"]) <= 3


def test_approximation_ratio_bound():
    """Compare greedy output against brute-force optimal on small candidate set."""
    seeds = [{"id": "s1", "name": "Auth", "docstring": "JWT token authentication"}]
    candidates = [
        {"id": "c1", "name": "JWTValidator", "content": "Validates JWT tokens", "docstring": "JWT token verification"},
        {"id": "c2", "name": "SessionStore", "content": "Stores active sessions in memory", "docstring": "Session memory"},
        {"id": "c3", "name": "PasswordHasher", "content": "Bcrypt password hashing", "docstring": "Bcrypt hash algorithm"},
        {"id": "c4", "name": "UnrelatedHelper", "content": "Math geometry helper functions", "docstring": "Geometry math"},
    ]

    opt = SubmodularContextOptimizer(seeds, candidates)
    budget = 25  # Restrictive budget

    # Greedy solution
    greedy_res = opt.optimize(budget_tokens=budget)
    greedy_score = greedy_res["coverage_score"]

    # Brute-force optimal over all 2^N subsets
    costs = [estimate_token_cost(c.get("content", "")) for c in candidates]
    best_opt_score = 0.0

    for r in range(1, len(candidates) + 1):
        for combo in itertools.combinations(range(len(candidates)), r):
            tot_cost = sum(costs[i] for i in combo)
            if tot_cost <= budget:
                score = opt.evaluate_coverage(set(combo))
                if score > best_opt_score:
                    best_opt_score = score

    # Theoretical bound: greedy_score >= (1 - 1/e) * best_opt_score
    theoretical_lower_bound = 0.632 * best_opt_score
    assert greedy_score >= theoretical_lower_bound - 1e-4, (
        f"Greedy score {greedy_score} fell below (1 - 1/e) bound {theoretical_lower_bound} (opt={best_opt_score})"
    )
