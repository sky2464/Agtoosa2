# DEV-055: Causal Architecture Inference and Pearl's Do-Calculus

> **Cycle:** DEV-055  
> **Milestone:** Milestone 18 (v0.9.5) — Mathematical Foundations & Formal Invariants  
> **Status:** ✅ Implemented & Verified  
> **Type:** Causal Inference & Observability Intelligence  

---

## 1. Problem Statement

Modern observability tools and telemetry overlays measure **observational correlation** rather than **causal impact**:
$$P(\text{Failure}_Y \mid \text{Latency}_X > \tau)$$
In complex distributed architectures, this creates severe confounding errors:
- **Shared Resource Confounding (Simpson's Paradox)**: When a PostgreSQL connection pool $Z$ becomes saturated, Service $X$ and Service $Y$ both experience high latency and failure rates. Observational monitoring flags $X \to Y$ as an error cascade, even when $X$ and $Y$ are completely independent.
- **Spurious Root-Cause Attribution**: On-call engineers and autonomous PR repair agents waste hours investigating symptom services rather than the true causal origin.

DEV-055 implements Judea Pearl's **Structural Causal Models (SCMs)** and **$do$-calculus**, allowing Agtoosa2 to evaluate interventional distributions $P(Y \mid \text{do}(X = x))$ by conditioning on mathematically proven **back-door adjustment sets**.

---

## Acceptance Criteria (EARS Syntax)

- **AC-1 (Structural Causal Model DAG)**: WHEN analyzing service call graphs and distributed traces, the engine SHALL construct an acyclic causal DAG $\mathcal{G} = (V, E)$ modeling parent-child dataflow dependencies.
- **AC-2 (Pearl's Back-Door Admissibility Verification)**: WHEN evaluating a causal effect $X \to Y$ under conditioning set $Z$, the engine SHALL verify:
  1. No node in $Z$ is a causal descendant of $X$.
  2. $Z$ blocks ($d$-separates) every path between $X$ and $Y$ containing an arrow into $X$ (back-door paths).
- **AC-3 (Minimal Adjustment Set Discovery)**: WHEN an adjustment set is requested for $(X, Y)$, the engine SHALL automatically identify a minimal admissible set $Z^*$ from non-descendant parents or common ancestors.
- **AC-4 (Average Causal Effect & Confounding Detection)**: WHEN observational trace frequencies are evaluated, the engine SHALL compute the Average Causal Effect (ACE):
  $$\text{ACE}(X \to Y) = \mathbb{E}[Y \mid \text{do}(X = 1)] - \mathbb{E}[Y \mid \text{do}(X = 0)]$$
  and flag confounding when $|\text{ACE} - \text{ObsDiff}| > 0.05$.

---

## 2. Invariants & Mathematical Formulation

### 2.1 Observational vs Interventional Distributions
- **Observational Distribution**:
  $$P(Y = y \mid X = x) = \sum_z P(Y = y \mid X = x, Z = z) P(Z = z \mid X = x)$$
- **Interventional Distribution (Pearl's do-operator)**:
  $$P(Y = y \mid \text{do}(X = x)) = \sum_z P(Y = y \mid X = x, Z = z) P(Z = z)$$
Notice that in the interventional equation, $P(Z = z)$ replaces $P(Z = z \mid X = x)$, severing the back-door arrows entering $X$ without perturbing the rest of the causal mechanisms.

### 2.2 The Back-Door Criterion (Pearl 1993)
A set of variables $Z$ satisfies the back-door criterion relative to an ordered pair $(X, Y)$ in a DAG $\mathcal{G}$ if:
1. No node in $Z$ is a descendant of $X$:
   $$Z \cap \text{Desc}(X) = \emptyset$$
2. $Z$ blocks every path between $X$ and $Y$ that contains an arrow into $X$.

### 2.3 d-Separation & Path Blocking Rules
A path $p$ is blocked by $Z$ if and only if:
1. $p$ contains a **chain** ($i \to m \to j$) or a **fork** ($i \leftarrow m \to j$) such that the middle node $m \in Z$.
2. $p$ contains a **collider** ($i \to c \leftarrow j$) such that neither the collider $c$ nor any descendant of $c$ is in $Z$ ($\text{Desc}(c) \cup \{c\} \cap Z = \emptyset$).

### 2.4 Average Causal Effect (ACE)
Given binary event states (1 = error/degraded, 0 = normal):
$$\text{ACE}(X \to Y) = P(Y = 1 \mid \text{do}(X = 1)) - P(Y = 1 \mid \text{do}(X = 0))$$
If $\text{ACE} \approx 0$ while the naive observational difference $P(Y = 1 \mid X = 1) - P(Y = 1 \mid X = 0) \gg 0$, the relationship is proven to be **spurious confounding**.

---

## 3. Interfaces & Surface Area

### 3.1 Python Engine (`agtoosa/observability/causal.py`)
```python
class CausalEngine:
    def __init__(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]): ...
    def get_descendants(self, node: str) -> Set[str]: ...
    def is_backdoor_admissible(self, x: str, y: str, z_set: Set[str]) -> Tuple[bool, Optional[str]]: ...
    def find_minimal_adjustment_set(self, x: str, y: str) -> Optional[Set[str]]: ...
    def compute_causal_effect(
        self,
        x: str,
        y: str,
        contingency_table: List[Dict[str, Any]]
    ) -> Dict[str, Any]: ...
```

---

## 4. Verification & Testing Strategy

- `tests/test_causal.py`:
  - `test_fork_confounding_resolution`: Simulates fork graph $Z \to X$ and $Z \to Y$ (shared database overload). Verifies that conditioning on $Z$ proves $X$ does not cause $Y$ ($\text{ACE} = 0.0$), while naive observational difference is $> 0.40$ (confounding successfully detected).
  - `test_collider_conditioning_rejection`: Validates collider structure $X \to W \leftarrow Y$, confirming $W$ is not a back-door path into $X$.
