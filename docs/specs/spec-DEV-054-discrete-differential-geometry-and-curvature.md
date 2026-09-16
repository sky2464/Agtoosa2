# DEV-054: Discrete Differential Geometry and Forman-Ricci Curvature

> **Cycle:** DEV-054  
> **Milestone:** Milestone 18 (v0.9.5) — Mathematical Foundations & Formal Invariants  
> **Status:** ✅ Implemented & Verified  
> **Type:** Discrete Differential Geometry & Topological Invariants  

---

## 1. Problem Statement

In large software architectures, degree centrality and PageRank identify popular nodes, but fail to detect **fragile architectural choke points**:
- **Fragile Bridges**: An edge connecting two high-degree modules may carry massive cross-modular coupling stress without appearing abnormal under standard node-level metrics. When modified, this bridge triggers cascading systemic failures.
- **Euclidean Metric Distortion**: Codebases are deeply hierarchical (AST trees, package hierarchies, inheritance graphs). Forcing tree-like metrics into flat Euclidean assumptions creates severe metric distortion.

DEV-054 introduces **Discrete Differential Geometry** to Agtoosa2 by implementing **Forman-Ricci Curvature** $\mathbf{Ric}_F(e)$ and **Gromov $\delta$-Hyperbolicity**, classifying every dependency edge as either an architectural choke point or a cohesive cluster edge.

---

## Acceptance Criteria (EARS Syntax)

- **AC-1 (Forman-Ricci Edge Curvature)**: WHEN graph metrics or architectural health audits are executed, the engine SHALL compute the Forman-Ricci discrete curvature for every non-containment edge:
  $$\mathbf{Ric}_F(e) = 4 - d(u) - d(v) + 3 \times \Delta(e)$$
- **AC-2 (Negative Curvature Choke Point Detection)**: WHEN an edge exhibits negative curvature $\mathbf{Ric}_F(e) < 0$, the engine SHALL classify the edge as an architectural bottleneck/bridge and report it in health summaries.
- **AC-3 (Positive Curvature Cluster Identification)**: WHEN an edge exhibits positive curvature $\mathbf{Ric}_F(e) > 0$, the engine SHALL classify it as embedded within a cohesive, redundant module cluster.
- **AC-4 (Gromov $\delta$-Hyperbolicity Evaluation)**: WHEN assessing topological tree-likeness, the engine SHALL compute the 4-point Gromov condition $\delta(x, y, z, w)$ over geodesic path distances.

---

## 2. Invariants & Mathematical Formulation

### 2.1 Forman-Ricci Discrete Curvature
Forman (2003) adapted Riemannian Ricci curvature to CW cellular complexes. On a discrete software graph with edge $e = (u, v)$:
$$\mathbf{Ric}_F(e) = \omega(e) \left( \frac{\omega(u)}{\omega(e)} + \frac{\omega(v)}{\omega(e)} - \sum_{e_u \sim e, e_u \neq e} \frac{\omega(u)}{\sqrt{\omega(e)\omega(e_u)}} - \sum_{e_v \sim e, e_v \neq e} \frac{\omega(v)}{\sqrt{\omega(e)\omega(e_v)}} \right) + 3 \Delta(e)$$
For unweighted graphs, this reduces to the combinatorial closed-form:
$$\mathbf{Ric}_F(e) = 4 - d(u) - d(v) + 3 \Delta(e)$$
where:
- $d(u), d(v)$ are the degrees of nodes $u$ and $v$.
- $\Delta(e) = |N(u) \cap N(v)|$ is the number of shared triangles (common neighbors) supported by edge $e$.

### 2.2 Geometric & Architectural Significance
- **$\mathbf{Ric}_F(e) \ll 0$ (Negative Curvature)**: Dispersive geometry (hyperbolic saddle). Geodesics diverge away from $e$. The edge acts as a narrow conduit between distinct modules, carrying extreme traffic without redundant alternate paths.
- **$\mathbf{Ric}_F(e) > 0$ (Positive Curvature)**: Convergent geometry (spherical). Geodesics converge through $e$. The edge resides within a tightly coupled, redundant clique where multiple triangles provide alternative routes.

### 2.3 Gromov $\delta$-Hyperbolicity
A metric space $(X, d)$ is Gromov $\delta$-hyperbolic if for all quadruples $x, y, z, w \in X$:
$$d(x, y) + d(z, w) \le \max\Big(d(x, z) + d(y, w), \, d(x, w) + d(y, z)\Big) + 2\delta$$
Let $S_{(1)} \ge S_{(2)} \ge S_{(3)}$ be the sorted values of the three pairwise distance sums. The hyperbolicity of the quadruple is:
$$\delta(x, y, z, w) = \frac{S_{(1)} - S_{(2)}}{2}$$
- Strictly tree-like architectures have $\delta = 0$.
- Bounded $\delta \le 1.5$ confirms the architecture can be embedded into hyperbolic space $\mathbb{H}^3$ (Poincaré Ball) with minimal isometric distortion.

---

## 3. Interfaces & Surface Area

### 3.1 Python Engine (`agtoosa/graph/curvature.py`)
```python
class CurvatureEngine:
    def __init__(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]): ...
    def compute_forman_ricci_curvature(self) -> Dict[str, Any]: ...
    def compute_gromov_hyperbolicity(self, sample_size: int = 50) -> Dict[str, Any]: ...
```

### 3.2 Metrics Integration (`agtoosa/graph/metrics.py`)
`MetricsEngine.compute_all` includes:
- `curvature.bottleneck_count`: Total edges with $\mathbf{Ric}_F(e) < 0$.
- `curvature.average_curvature`: Mean Ricci curvature across the topology.
- `curvature.top_bottlenecks`: Top 10 most severe negative curvature choke points.
Surfaced in `agtoosa graph report` text and markdown formats.

---

## 4. Verification & Testing Strategy

- `tests/test_curvature.py`:
  - `test_clique_positive_curvature`: Proves every edge in complete graph $K_4$ has $\mathbf{Ric}_F(e) = +4$.
  - `test_bridge_negative_curvature`: Proves the bridge between two triangles has $\mathbf{Ric}_F(e) = -2$ and is flagged as a top bottleneck.
  - `test_tree_gromov_hyperbolicity`: Proves a tree graph has exact Gromov $\delta = 0$.
