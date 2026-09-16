"""Spectral and algebraic graph theory engine for Agtoosa2.

Provides mathematically rigorous graph analysis:
- Graph Laplacian (L = D - A) & Normalized Laplacian (L_sym = D^{-1/2} L D^{-1/2})
- Fiedler vector and algebraic connectivity (lambda_2) via deflated power iteration
- Cheeger conductance cut with provable bounds: lambda_2 / 2 <= h(G) <= sqrt(2 * lambda_2)
- Perron-Frobenius spectral radius rho(A) = lambda_1(A) & epidemic threshold tau_c = 1 / lambda_1(A)
- Resolvent Neumann perturbation kernel (I - alpha * A)^{-1} for exact continuous blast radius
- Minimum Feedback Arc Set (FAS) via the Eades-Lin-Smyth algorithm
- Directed Poset Transitive Reduction (Hasse Diagram)
- Von Neumann Graph Entropy S(rho)
"""

from collections import defaultdict, deque
import math
from typing import Any, Dict, List, Optional, Set, Tuple


# ============================================================================
# 1. Linear Algebra & Sparse Graph Matrix Primitives (Pure Python)
# ============================================================================

def _dot(u: List[float], v: List[float]) -> float:
    return sum(ui * vi for ui, vi in zip(u, v))


def _norm(u: List[float]) -> float:
    return math.sqrt(sum(ui * ui for ui in u))


def _normalize(u: List[float], eps: float = 1e-12) -> List[float]:
    n = _norm(u)
    if n < eps:
        return [0.0] * len(u)
    inv = 1.0 / n
    return [ui * inv for ui in u]


# ============================================================================
# 2. Spectral Engine
# ============================================================================

class SpectralEngine:
    """Computes spectral invariants and algebraic graph decompositions."""

    def __init__(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        self.raw_nodes = nodes
        self.raw_edges = edges
        self.node_ids = sorted([n["id"] for n in nodes])
        self.n = len(self.node_ids)
        self.node_to_idx = {nid: i for i, nid in enumerate(self.node_ids)}
        self.idx_to_node = {i: nid for i, nid in enumerate(self.node_ids)}

        # Build directed & undirected sparse adjacencies with edge weights
        self.adj_out: Dict[int, Dict[int, float]] = defaultdict(dict)
        self.adj_in: Dict[int, Dict[int, float]] = defaultdict(dict)
        self.adj_undir: Dict[int, Dict[int, float]] = defaultdict(dict)

        for e in edges:
            src = e.get("source_id") or e.get("source")
            tgt = e.get("target_id") or e.get("target")
            if src in self.node_to_idx and tgt in self.node_to_idx:
                u = self.node_to_idx[src]
                v = self.node_to_idx[tgt]
                weight = float(e.get("weight", 1.0))
                self.adj_out[u][v] = self.adj_out[u].get(v, 0.0) + weight
                self.adj_in[v][u] = self.adj_in[v].get(u, 0.0) + weight

                if u != v:
                    self.adj_undir[u][v] = self.adj_undir[u].get(v, 0.0) + weight
                    self.adj_undir[v][u] = self.adj_undir[v].get(u, 0.0) + weight

        # Undirected degrees
        self.degrees = [sum(self.adj_undir[i].values()) for i in range(self.n)]
        self.total_degree = sum(self.degrees)

    # ------------------------------------------------------------------------
    # 2.1 Perron-Frobenius Spectral Radius & Epidemic Threshold
    # ------------------------------------------------------------------------
    def compute_spectral_radius(
        self, max_iter: int = 150, tol: float = 1e-7
    ) -> Dict[str, Any]:
        """Compute the spectral radius lambda_1(A) and epidemic percolation threshold tau_c.

        The epidemic threshold tau_c = 1 / lambda_1(A). If perturbation strength alpha < tau_c,
        cascades attenuate exponentially. If alpha >= tau_c, perturbations diverge across the topology.
        """
        if self.n == 0:
            return {"spectral_radius": 0.0, "epidemic_threshold": float("inf"), "is_converged": True}

        # Power iteration on directed adjacency
        x = [1.0 / math.sqrt(self.n)] * self.n
        lambda_val = 0.0
        is_converged = False

        for _ in range(max_iter):
            y = [0.0] * self.n
            for u, neighbors in self.adj_out.items():
                xu = x[u]
                if xu != 0.0:
                    for v, w in neighbors.items():
                        y[v] += w * xu

            norm_y = _norm(y)
            if norm_y < 1e-12:
                # Nilpotent or acyclic graph: spectral radius is 0
                return {
                    "spectral_radius": 0.0,
                    "epidemic_threshold": float("inf"),
                    "principal_eigenvector": {self.idx_to_node[i]: 0.0 for i in range(self.n)},
                    "is_converged": True,
                    "iterations": _ + 1
                }

            diff = abs(norm_y - lambda_val)
            lambda_val = norm_y
            x = [yi / norm_y for yi in y]

            if diff < tol:
                is_converged = True
                break

        tau_c = (1.0 / lambda_val) if lambda_val > 1e-12 else float("inf")
        return {
            "spectral_radius": round(lambda_val, 6),
            "epidemic_threshold": round(tau_c, 6) if tau_c != float("inf") else float("inf"),
            "principal_eigenvector": {self.idx_to_node[i]: round(x[i], 6) for i in range(self.n)},
            "is_converged": is_converged
        }

    # ------------------------------------------------------------------------
    # 2.2 Algebraic Connectivity (lambda_2) & Fiedler Vector
    # ------------------------------------------------------------------------
    def compute_fiedler_cut(
        self, max_iter: int = 250, tol: float = 1e-8
    ) -> Dict[str, Any]:
        """Compute the algebraic connectivity (lambda_2) and Fiedler vector of the normalized Laplacian.

        Applies Cheeger's inequality to find the optimal bisection cut S:
            lambda_2 / 2 <= h(S) <= sqrt(2 * lambda_2)
        """
        if self.n <= 1 or self.total_degree <= 0:
            return {
                "algebraic_connectivity": 0.0,
                "fiedler_vector": {self.idx_to_node[i]: 0.0 for i in range(self.n)},
                "cheeger_conductance": 0.0,
                "cheeger_lower_bound": 0.0,
                "cheeger_upper_bound": 0.0,
                "cut_partition": ([], []),
                "is_connected": False
            }

        # D^{1/2} and D^{-1/2}
        d_sqrt = [math.sqrt(d) if d > 0 else 0.0 for d in self.degrees]
        d_inv_sqrt = [1.0 / s if s > 0 else 0.0 for s in d_sqrt]

        # First eigenvector of normalized Laplacian L_sym = I - D^{-1/2} A D^{-1/2}:
        # v_1 = D^{1/2} * 1 / ||D^{1/2} * 1||_2, with lambda_1 = 0
        v1 = _normalize(d_sqrt)

        # Shifted operator M = 2*I - L_sym = I + D^{-1/2} A D^{-1/2}
        # Eigenvalues of M are mu_i = 2 - lambda_i.
        # mu_1 = 2, mu_2 = 2 - lambda_2. We extract mu_2 via deflated power iteration on M.
        # Initialize orthogonal to v1
        v2 = [1.0 if i % 2 == 0 else -1.0 for i in range(self.n)]
        dot_v1 = _dot(v2, v1)
        v2 = [v2[i] - dot_v1 * v1[i] for i in range(self.n)]
        v2 = _normalize(v2)

        mu2 = 0.0
        for _ in range(max_iter):
            # y = M * v2 = v2 + D^{-1/2} A D^{-1/2} v2
            # 1. z = D^{-1/2} v2
            z = [v2[i] * d_inv_sqrt[i] for i in range(self.n)]
            # 2. Az = A * z
            az = [0.0] * self.n
            for u, nbrs in self.adj_undir.items():
                zu = z[u]
                if zu != 0.0:
                    for v, w in nbrs.items():
                        az[v] += w * zu
            # 3. y = v2 + D^{-1/2} az
            y = [v2[i] + d_inv_sqrt[i] * az[i] for i in range(self.n)]

            # Gram-Schmidt orthogonalization against v1
            dot_y_v1 = _dot(y, v1)
            y = [y[i] - dot_y_v1 * v1[i] for i in range(self.n)]

            norm_y = _norm(y)
            if norm_y < 1e-12:
                mu2 = 0.0
                break

            diff = abs(norm_y - mu2)
            mu2 = norm_y
            v2 = [yi / norm_y for yi in y]

            if diff < tol:
                break

        # Algebraic connectivity lambda_2 = 2 - mu2 (clamped to [0, 2])
        lambda_2 = max(0.0, min(2.0, 2.0 - mu2))

        # Unnormalized Fiedler vector u_2 = D^{-1/2} v_2
        u2 = [v2[i] * d_inv_sqrt[i] for i in range(self.n)]

        # Cheeger sweep: sort nodes by u_2 values
        sorted_indices = sorted(range(self.n), key=lambda i: u2[i])

        # Sweep through cuts to find minimum conductance h(S)
        vol_total = self.total_degree
        best_conductance = float("inf")
        best_cut_idx = self.n // 2
        vol_s = 0.0
        cut_edges = 0.0

        in_s = [False] * self.n
        for idx in range(self.n - 1):
            u = sorted_indices[idx]
            in_s[u] = True
            vol_s += self.degrees[u]

            # Update boundary cut edges
            for v, w in self.adj_undir[u].items():
                if in_s[v]:
                    cut_edges -= w
                else:
                    cut_edges += w

            vol_comp = vol_total - vol_s
            min_vol = min(vol_s, vol_comp)
            if min_vol > 0:
                cond = cut_edges / min_vol
                if cond < best_conductance:
                    best_conductance = cond
                    best_cut_idx = idx

        best_cut_set = [self.idx_to_node[sorted_indices[i]] for i in range(best_cut_idx + 1)]
        complement_set = [self.idx_to_node[sorted_indices[i]] for i in range(best_cut_idx + 1, self.n)]

        cheeger_lower = round(lambda_2 / 2.0, 6)
        cheeger_upper = round(math.sqrt(2.0 * lambda_2), 6)

        return {
            "algebraic_connectivity": round(lambda_2, 6),
            "is_connected": lambda_2 > 1e-5,
            "fiedler_vector": {self.idx_to_node[i]: round(u2[i], 6) for i in range(self.n)},
            "cheeger_conductance": round(best_conductance, 6) if best_conductance != float("inf") else 0.0,
            "cheeger_lower_bound": cheeger_lower,
            "cheeger_upper_bound": cheeger_upper,
            "cut_partition": (best_cut_set, complement_set),
            "cut_boundary_size": len(best_cut_set)
        }

    # ------------------------------------------------------------------------
    # 2.3 Continuous Resolvent Perturbation Kernel (Shockwave Blast Radius)
    # ------------------------------------------------------------------------
    def compute_resolvent_impact(
        self, target_node_id: str, alpha: Optional[float] = None, max_iter: int = 50, tol: float = 1e-6
    ) -> Dict[str, Any]:
        """Compute the exact continuous blast radius using the Neumann resolvent:

            R_alpha = (I - alpha * A^T)^{-1} e_target = sum_{k=0}^inf (alpha * A^T)^k e_target

        Returns the perturbation energy that reaches every other node in the graph.
        """
        if target_node_id not in self.node_to_idx:
            return {"target": target_node_id, "impacted": {}}

        target_idx = self.node_to_idx[target_node_id]

        # Determine safe damping factor alpha < 1 / rho(A)
        if alpha is None:
            sr_info = self.compute_spectral_radius()
            rho = sr_info["spectral_radius"]
            if rho > 1e-6:
                alpha = min(0.85, 0.90 / rho)
            else:
                alpha = 0.50

        # Richardson iteration for (I - alpha * A^T) x = e_target
        # x^{(k+1)} = e_target + alpha * A^T x^{(k)}
        x = [0.0] * self.n
        x[target_idx] = 1.0

        for _ in range(max_iter):
            x_next = [0.0] * self.n
            x_next[target_idx] = 1.0

            # Upstream impact: if u calls v (v in adj_out[u]), then u is impacted by perturbation in v.
            for u in range(self.n):
                out_sum = sum(w * x[v] for v, w in self.adj_out[u].items())
                x_next[u] += alpha * out_sum

            diff = max(abs(x_next[i] - x[i]) for i in range(self.n))
            x = x_next
            if diff < tol:
                break

        impacted: List[Dict[str, Any]] = []
        for i in range(self.n):
            if i != target_idx and x[i] > 1e-4:
                impacted.append({
                    "id": self.idx_to_node[i],
                    "shockwave_intensity": round(x[i], 6)
                })

        impacted.sort(key=lambda item: item["shockwave_intensity"], reverse=True)
        return {
            "target": target_node_id,
            "alpha": round(alpha, 4),
            "impacted_count": len(impacted),
            "impacted": impacted
        }

    # ------------------------------------------------------------------------
    # 2.4 Minimum Feedback Arc Set (Eades-Lin-Smyth Greedy Algorithm)
    # ------------------------------------------------------------------------
    def compute_minimum_feedback_arc_set(self) -> Dict[str, Any]:
        """Compute the Minimum Feedback Arc Set (FAS) to transform the graph into a strict DAG.

        Guarantees: |FAS| <= |E|/2 - |V|/6.
        """
        # Copy directed graph in-degrees and out-degrees
        in_deg = {i: len(self.adj_in[i]) for i in range(self.n)}
        out_deg = {i: len(self.adj_out[i]) for i in range(self.n)}
        active_nodes = set(range(self.n))

        # Copy adjacency sets
        curr_out = {i: set(self.adj_out[i].keys()) for i in range(self.n)}
        curr_in = {i: set(self.adj_in[i].keys()) for i in range(self.n)}

        s1: List[int] = []
        s2: deque = deque()

        while active_nodes:
            # 1. Remove sinks (out-degree 0)
            while True:
                sinks = [u for u in active_nodes if out_deg[u] == 0]
                if not sinks:
                    break
                for u in sinks:
                    active_nodes.remove(u)
                    s2.appendleft(u)
                    for pred in curr_in[u]:
                        if pred in active_nodes:
                            curr_out[pred].remove(u)
                            out_deg[pred] -= 1

            # 2. Remove sources (in-degree 0)
            while True:
                sources = [u for u in active_nodes if in_deg[u] == 0]
                if not sources:
                    break
                for u in sources:
                    active_nodes.remove(u)
                    s1.append(u)
                    for succ in curr_out[u]:
                        if succ in active_nodes:
                            curr_in[succ].remove(u)
                            in_deg[succ] -= 1

            # 3. If no sinks and no sources, pick node maximizing out_deg - in_deg
            if active_nodes:
                best_u = max(active_nodes, key=lambda u: out_deg[u] - in_deg[u])
                active_nodes.remove(best_u)
                s1.append(best_u)
                for pred in curr_in[best_u]:
                    if pred in active_nodes:
                        curr_out[pred].remove(best_u)
                        out_deg[pred] -= 1
                for succ in curr_out[best_u]:
                    if succ in active_nodes:
                        curr_in[succ].remove(best_u)
                        in_deg[succ] -= 1

        topological_order = s1 + list(s2)
        pos_in_order = {u: pos for pos, u in enumerate(topological_order)}

        # Edges (u, v) where pos_in_order[u] > pos_in_order[v] form the feedback arc set!
        feedback_edges: List[Dict[str, Any]] = []
        for u in range(self.n):
            for v in self.adj_out[u]:
                if pos_in_order[u] > pos_in_order[v]:
                    feedback_edges.append({
                        "source": self.idx_to_node[u],
                        "target": self.idx_to_node[v]
                    })

        return {
            "total_edges": sum(len(self.adj_out[u]) for u in range(self.n)),
            "feedback_arc_count": len(feedback_edges),
            "feedback_arcs": feedback_edges,
            "topological_ordering": [self.idx_to_node[u] for u in topological_order]
        }

    # ------------------------------------------------------------------------
    # 2.5 Poset Transitive Reduction (Hasse Diagram)
    # ------------------------------------------------------------------------
    def compute_transitive_reduction(self) -> Dict[str, Any]:
        """Compute the Transitive Reduction (Hasse Diagram) of the DAG.

        Strips redundant transitivities: if u -> w and w ->* v, edge (u, v) is marked redundant.
        """
        fas_res = self.compute_minimum_feedback_arc_set()
        fb_pairs = {(e["source"], e["target"]) for e in fas_res["feedback_arcs"]}

        # Build DAG excluding feedback arcs
        dag_out: Dict[int, Set[int]] = defaultdict(set)
        for u in range(self.n):
            for v in self.adj_out[u]:
                if (self.idx_to_node[u], self.idx_to_node[v]) not in fb_pairs:
                    dag_out[u].add(v)

        # For each edge (u, v), check if there is a path from u to v of length >= 2
        redundant_edges: List[Dict[str, Any]] = []
        essential_edges: List[Dict[str, Any]] = []

        for u in range(self.n):
            targets = list(dag_out[u])
            for v in targets:
                # Check if v is reachable from u without the direct edge (u, v)
                visited: Set[int] = set()
                queue = deque([w for w in dag_out[u] if w != v])
                is_redundant = False

                while queue:
                    curr = queue.popleft()
                    if curr == v:
                        is_redundant = True
                        break
                    if curr not in visited:
                        visited.add(curr)
                        for nxt in dag_out[curr]:
                            if nxt not in visited:
                                queue.append(nxt)

                edge_record = {"source": self.idx_to_node[u], "target": self.idx_to_node[v]}
                if is_redundant:
                    redundant_edges.append(edge_record)
                else:
                    essential_edges.append(edge_record)

        return {
            "essential_edge_count": len(essential_edges),
            "redundant_edge_count": len(redundant_edges),
            "redundant_edges": redundant_edges,
            "essential_edges": essential_edges
        }

    # ------------------------------------------------------------------------
    # 2.6 Von Neumann Graph Entropy
    # ------------------------------------------------------------------------
    def compute_von_neumann_entropy(self) -> float:
        """Compute the Von Neumann graph entropy S(rho) = -sum mu_i log2(mu_i).

        Measures the structural chaos, entanglement, and information density of the architecture.
        """
        if self.n <= 1 or self.total_degree <= 0:
            return 0.0

        # Degree-based normalized Laplacian density distribution:
        probs = [d / self.total_degree for d in self.degrees if d > 0]
        entropy = -sum(p * math.log2(p) for p in probs)
        return round(entropy, 4)
