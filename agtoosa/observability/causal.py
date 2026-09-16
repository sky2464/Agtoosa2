"""Causal inference engine implementing Judea Pearl's do-calculus and Structural Causal Models (SCMs).

Distinguishes observational correlation P(Y | X) from interventional causality P(Y | do(X))
in software call graphs, telemetry, and architectural failure cascades.
"""

from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple


class CausalEngine:
    """Evaluates causal paths, back-door criteria, and interventional distributions."""

    def __init__(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        self.node_ids = set(n["id"] for n in nodes)
        self.nodes = {n["id"]: n for n in nodes}

        # Directed DAG representation: parents and children
        self.parents: Dict[str, Set[str]] = defaultdict(set)
        self.children: Dict[str, Set[str]] = defaultdict(set)
        self.undirected: Dict[str, Set[str]] = defaultdict(set)

        for e in edges:
            u = e.get("source_id") or e.get("source")
            v = e.get("target_id") or e.get("target")
            if u in self.node_ids and v in self.node_ids and u != v:
                self.children[u].add(v)
                self.parents[v].add(u)
                self.undirected[u].add(v)
                self.undirected[v].add(u)

        # Precompute descendants for all nodes
        self._descendants_cache: Dict[str, Set[str]] = {}

    def get_descendants(self, node: str) -> Set[str]:
        """Compute all causal descendants of a node (including itself)."""
        if node in self._descendants_cache:
            return self._descendants_cache[node]

        desc: Set[str] = set()
        queue = deque([node])
        while queue:
            curr = queue.popleft()
            for ch in self.children[curr]:
                if ch not in desc:
                    desc.add(ch)
                    queue.append(ch)

        self._descendants_cache[node] = desc
        return desc

    # ------------------------------------------------------------------------
    # 1. Pearl's Back-Door Criterion Verification
    # ------------------------------------------------------------------------
    def is_backdoor_admissible(self, x: str, y: str, z_set: Set[str]) -> Tuple[bool, Optional[str]]:
        """Verify if conditioning set Z satisfies Pearl's Back-Door Criterion for (X, Y):

        1. No node in Z is a descendant of X.
        2. Z blocks every path between X and Y that contains an arrow into X (back-door paths).
        """
        if x not in self.node_ids or y not in self.node_ids:
            return False, "Nodes not in graph"

        # Condition 1: No node in Z is a descendant of X
        x_desc = self.get_descendants(x)
        desc_in_z = z_set & x_desc
        if desc_in_z:
            return False, f"Condition 1 violated: {desc_in_z} contains descendants of {x}"

        # Find all paths between X and Y containing an arrow into X (i.e. parent of X on path)
        backdoor_paths = self._find_backdoor_paths(x, y)

        # Condition 2: Check that each path is d-separated / blocked by Z
        for path in backdoor_paths:
            if not self._is_path_blocked_by_z(path, z_set):
                path_str = " - ".join(path)
                return False, f"Condition 2 violated: unblocked back-door path '{path_str}'"

        return True, "Valid back-door adjustment set"

    def find_minimal_adjustment_set(self, x: str, y: str) -> Optional[Set[str]]:
        """Find a minimal valid back-door adjustment set Z for estimating P(Y | do(X))."""
        # Candidate 1: Immediate non-descendant parents of X
        direct_parents = self.parents[x]
        is_valid, _ = self.is_backdoor_admissible(x, y, direct_parents)
        if is_valid:
            return direct_parents

        # Candidate 2: Common ancestors of X and Y
        ancestors_x = self._get_ancestors(x)
        ancestors_y = self._get_ancestors(y)
        common = ancestors_x & ancestors_y
        is_valid, _ = self.is_backdoor_admissible(x, y, common)
        if is_valid:
            return common

        return None

    def _get_ancestors(self, node: str) -> Set[str]:
        anc: Set[str] = set()
        queue = deque([node])
        while queue:
            curr = queue.popleft()
            for p in self.parents[curr]:
                if p not in anc:
                    anc.add(p)
                    queue.append(p)
        return anc

    def _find_backdoor_paths(self, x: str, y: str, max_depth: int = 4, max_paths: int = 100) -> List[List[str]]:
        """Find simple undirected paths between X and Y whose first step is into X (from a parent of X)."""
        paths: List[List[str]] = []
        for p in self.parents[x]:
            if len(paths) >= max_paths:
                break
            queue = deque([([x, p], {x, p})])
            while queue and len(paths) < max_paths:
                curr_path, visited = queue.popleft()
                curr_node = curr_path[-1]

                if curr_node == y:
                    paths.append(curr_path)
                    continue

                if len(curr_path) >= max_depth:
                    continue

                for nxt in self.undirected[curr_node]:
                    if nxt not in visited:
                        queue.append((curr_path + [nxt], visited | {nxt}))
        return paths

    def _is_path_blocked_by_z(self, path: List[str], z_set: Set[str]) -> bool:
        """Check if an undirected path is blocked by conditioning set Z according to d-separation."""
        # A path is blocked if it contains:
        # 1. A non-collider (chain i -> m -> j or fork i <- m -> j) where m in Z.
        # 2. A collider (i -> c <- j) where neither c nor any descendant of c is in Z.
        for i in range(1, len(path) - 1):
            prev_node = path[i - 1]
            curr_node = path[i]
            next_node = path[i + 1]

            is_collider = (prev_node in self.parents[curr_node] and next_node in self.parents[curr_node])

            if is_collider:
                curr_desc = self.get_descendants(curr_node) | {curr_node}
                if not (curr_desc & z_set):
                    # Collider is NOT conditioned on: this blocks the path!
                    return True
            else:
                # Non-collider: blocked if conditioned on
                if curr_node in z_set:
                    return True

        return False

    # ------------------------------------------------------------------------
    # 2. Interventional Distribution & Average Causal Effect (ACE)
    # ------------------------------------------------------------------------
    def compute_causal_effect(
        self,
        x: str,
        y: str,
        contingency_table: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Estimate the Average Causal Effect (ACE) = E[Y | do(X=1)] - E[Y | do(X=0)]

        using back-door adjustment over empirical contingency observations:
            P(Y=1 | do(X=x)) = sum_z P(Y=1 | X=x, Z=z) * P(Z=z)
        """
        adj_set = self.find_minimal_adjustment_set(x, y)
        if adj_set is None:
            adj_set = set()

        # If no confounders exist (adj_set is empty), observational equals causal!
        total_obs = len(contingency_table)
        if total_obs == 0:
            return {"ace": 0.0, "adjustment_set": list(adj_set), "is_confounded": False}

        # Compute empirical counts
        z_keys = sorted(list(adj_set))

        # Stratified counts: counts[z_val][(x_val, y_val)]
        stratified_counts: Dict[Tuple, Dict[Tuple[int, int], int]] = defaultdict(lambda: defaultdict(int))
        z_counts: Dict[Tuple, int] = defaultdict(int)

        for row in contingency_table:
            z_val = tuple(row.get(zk, 0) for zk in z_keys)
            x_val = row.get(x, 0)
            y_val = row.get(y, 0)

            stratified_counts[z_val][(x_val, y_val)] += 1
            z_counts[z_val] += 1

        # Calculate P(Y=1 | do(X=1)) and P(Y=1 | do(X=0))
        p_y1_do_x1 = 0.0
        p_y1_do_x0 = 0.0

        for z_val, z_tot in z_counts.items():
            p_z = z_tot / total_obs

            # P(Y=1 | X=1, Z=z)
            n_x1 = stratified_counts[z_val][(1, 0)] + stratified_counts[z_val][(1, 1)]
            p_y1_given_x1_z = (stratified_counts[z_val][(1, 1)] / n_x1) if n_x1 > 0 else 0.0
            p_y1_do_x1 += p_y1_given_x1_z * p_z

            # P(Y=1 | X=0, Z=z)
            n_x0 = stratified_counts[z_val][(0, 0)] + stratified_counts[z_val][(0, 1)]
            p_y1_given_x0_z = (stratified_counts[z_val][(0, 1)] / n_x0) if n_x0 > 0 else 0.0
            p_y1_do_x0 += p_y1_given_x0_z * p_z

        ace = p_y1_do_x1 - p_y1_do_x0

        # Naive observational difference for comparison
        tot_x1 = sum(1 for r in contingency_table if r.get(x) == 1)
        tot_x0 = sum(1 for r in contingency_table if r.get(x) == 0)
        p_y1_x1_obs = sum(1 for r in contingency_table if r.get(x) == 1 and r.get(y) == 1) / max(1, tot_x1)
        p_y1_x0_obs = sum(1 for r in contingency_table if r.get(x) == 0 and r.get(y) == 1) / max(1, tot_x0)
        naive_diff = p_y1_x1_obs - p_y1_x0_obs

        is_confounded = abs(ace - naive_diff) > 0.05

        return {
            "source": x,
            "target": y,
            "average_causal_effect": round(ace, 4),
            "naive_observational_diff": round(naive_diff, 4),
            "is_confounded": is_confounded,
            "adjustment_set": list(adj_set),
            "p_y_do_x1": round(p_y1_do_x1, 4),
            "p_y_do_x0": round(p_y1_do_x0, 4)
        }
