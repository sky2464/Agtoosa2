# DEV-053: Information-Theoretic Submodular Context Optimization

> **Cycle:** DEV-053  
> **Milestone:** Milestone 18 (v0.9.5) — Mathematical Foundations & Formal Invariants  
> **Status:** ✅ Implemented & Verified  
> **Type:** Context Engineering & Information Theory  

---

## 1. Problem Statement

Context compilation for LLM coding agents traditionally relies on heuristic prompt packing:
- **Heuristic Truncation**: Retrieving top-$K$ lexical or vector matches and slicing at arbitrary token counts.
- **Semantic Redundancy**: When multiple retrieved functions perform similar tasks or belong to the same module, LLM context windows are flooded with redundant tokens.
- **Omission of Critical Structural Bridges**: Peripheral but architecturally critical dependencies are omitted because their isolated lexical score was lower than a redundant neighbor.

DEV-053 replaces heuristic slicing with **Budgeted Maximum Coverage** over a **Monotone Submodular Utility Function**, guaranteeing a proven $(1 - 1/e) \approx 63.2\%$ approximation ratio to the NP-hard optimal prompt pack.

---

## Acceptance Criteria (EARS Syntax)

- **AC-1 (Submodular Diminishing Returns)**: WHEN evaluating candidate context subsets, the coverage function $f(S)$ SHALL strictly satisfy monotone submodularity:
  $$\forall A \subseteq B \subset V, \forall v \notin B: \quad f(A \cup \{v\}) - f(A) \ge f(B \cup \{v\}) - f(B)$$
- **AC-2 (Budgeted Knapsack Optimization)**: WHEN a token budget $B$ is specified, the optimizer SHALL maximize the objective function without exceeding $B$ tokens:
  $$\sum_{v \in S^*} c(v) \le B$$
- **AC-3 (Theoretical Approximation Guarantee)**: WHEN the greedy ratio optimizer executes, the assembled context pack SHALL attain at least:
  $$f(S^*) \ge \left(1 - \frac{1}{e}\right) \cdot f(S_{\text{OPT}})$$
- **AC-4 (Context Compiler Integration)**: WHEN `ContextCompiler.compile_context` is called with target stories, tasks, or symbols, the engine SHALL invoke `SubmodularContextOptimizer` to select related symbols within the allotted token budget.

---

## 2. Invariants & Mathematical Formulation

### 2.1 The Budgeted Maximum Coverage Problem
Let $V = \{v_1, \dots, v_n\}$ be the universe of candidate code symbols and documentation entities.
Each candidate $v$ has token cost $c(v) \in \mathbb{Z}^+$.
Given total token budget $B$:
$$\max_{S \subseteq V} f(S) \quad \text{subject to} \quad \sum_{v \in S} c(v) \le B$$

### 2.2 Submodular Entropy & Proximity Objective Function
The objective function measures cumulative information coverage over the seed target graph $U_{\text{seed}}$:
$$f(S) = \sum_{u \in U_{\text{seed}}} w_u \cdot \log\left(1 + \sum_{v \in S} \text{Sim}(u, v) \cdot e^{-\gamma \cdot \text{dist}_G(u, v)}\right)$$
where:
- $w_u$ is the importance weight of seed $u$ (e.g., $w_{\text{target}} = 2.0, w_{\text{criteria}} = 1.5$).
- $\text{Sim}(u, v) \in [0, 1]$ is the semantic token Jaccard / cosine similarity.
- $e^{-\gamma \cdot \text{dist}_G(u, v)}$ is the graph geodesic distance decay factor ($\gamma = 0.5$).
- Because $\phi(x) = \log(1 + x)$ is strictly concave and non-decreasing, $f(S)$ is strictly monotone submodular.

### 2.3 Sviridenko's Cost-Effective Greedy Knapsack Theorem
At step $t$, the greedy algorithm computes the marginal gain per token:
$$r(v) = \frac{f(S_t \cup \{v\}) - f(S_t)}{c(v)}$$
selecting $v^* = \arg\max_{v \notin S_t, c(S_t \cup \{v\}) \le B} r(v)$.
Comparing the accumulated greedy set $S_{\text{greedy}}$ against the best single candidate $v_{\max} = \arg\max_{v, c(v) \le B} f(\{v\})$:
$$S^* = \arg\max_{S \in \{S_{\text{greedy}}, \{v_{\max}\}\}} f(S)$$
guarantees a formal approximation factor of $(1 - 1/e) \approx 0.632$ against the global theoretical optimum $S_{\text{OPT}}$.

---

## 3. Interfaces & Surface Area

### 3.1 Python Engine (`agtoosa/core/submodular.py`)
```python
def estimate_token_cost(text: str) -> int: ...

class SubmodularContextOptimizer:
    def __init__(
        self,
        seeds: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        graph_distances: Optional[Dict[Tuple[str, str], int]] = None,
        similarity_fn: Optional[Callable[[Dict[str, Any], Dict[str, Any]], float]] = None
    ): ...
    def evaluate_coverage(self, selected_indices: Set[int]) -> float: ...
    def optimize(self, budget_tokens: int) -> Dict[str, Any]: ...
```

### 3.2 Context Compiler Integration (`agtoosa/core/context_compiler.py`)
`ContextCompiler._find_related_code_symbols` automatically optimizes candidate code symbols using `SubmodularContextOptimizer` under a 1,500 token budget.

---

## 4. Verification & Testing Strategy

- `tests/test_submodular.py`:
  - `test_monotone_submodularity_property`: Formally verifies that marginal gain decreases monotonically ($A \subseteq B \implies f(A \cup \{v\}) - f(A) \ge f(B \cup \{v\}) - f(B)$).
  - `test_budget_constraint_satisfaction`: Verifies total tokens used strictly stays below budget $B$.
  - `test_approximation_ratio_bound`: Exhaustively computes all $2^N$ subsets on small benchmark graphs and proves the greedy score is $\ge 0.632 \times f(S_{\text{OPT}})$.
- `tests/test_hybrid_rag.py`:
  - Validates end-to-end prompt pack generation with submodular symbol selection.
