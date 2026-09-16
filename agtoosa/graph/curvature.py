"""Discrete differential geometry and curvature engine for software architecture graphs.

Computes:
- Forman-Ricci discrete curvature Ric_F(e) on graph edges to identify:
  * Negative curvature bridges (Ric_F << 0): Fragile structural bottlenecks and choke points.
  * Positive curvature clusters (Ric_F > 0): Highly redundant, cohesive module clusters.
- Gromov delta-hyperbolicity: Measures tree-likeness of the codebase dependency topology.
"""

from collections import defaultdict, deque
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class CurvatureEngine:
    """Computes discrete differential geometry invariants on software graphs."""

    def __init__(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        self.nodes = {n["id"]: n for n in nodes}
        self.node_ids = list(self.nodes.keys())
        self.n = len(self.node_ids)

        # Build undirected graph
        self.adj: Dict[str, Set[str]] = defaultdict(set)
        self.edge_set: Set[Tuple[str, str]] = set()

        for e in edges:
            u = e.get("source_id") or e.get("source")
            v = e.get("target_id") or e.get("target")
            if u in self.nodes and v in self.nodes and u != v:
                self.adj[u].add(v)
                self.adj[v].add(u)
                self.edge_set.add(tuple(sorted([u, v])))

        self.degrees = {u: len(self.adj[u]) for u in self.node_ids}

    # ------------------------------------------------------------------------
    # 1. Forman-Ricci Curvature
    # ------------------------------------------------------------------------
    def compute_forman_ricci_curvature(self) -> Dict[str, Any]:
        """Compute the Forman-Ricci discrete curvature for all edges in the graph:

            Ric_F(e) = 4 - deg(u) - deg(v) + 3 * Triangles(e)

        Interpretation:
        - Ric_F(e) < 0: Negative curvature edge acting as an architectural bottleneck/bridge.
        - Ric_F(e) > 0: Positive curvature edge embedded in a cohesive clique.
        """
        edge_curvatures: List[Dict[str, Any]] = []
        bottlenecks: List[Dict[str, Any]] = []
        clusters: List[Dict[str, Any]] = []

        for u, v in self.edge_set:
            deg_u = self.degrees[u]
            deg_v = self.degrees[v]

            # Count common neighbors (triangles containing edge e)
            common_neighbors = self.adj[u] & self.adj[v]
            triangles = len(common_neighbors)

            # Forman-Ricci curvature formula for unweighted graphs
            ric = 4 - deg_u - deg_v + 3 * triangles

            edge_record = {
                "source": u,
                "target": v,
                "source_name": self.nodes[u].get("name", u),
                "target_name": self.nodes[v].get("name", v),
                "curvature": ric,
                "triangles": triangles,
                "deg_source": deg_u,
                "deg_target": deg_v
            }
            edge_curvatures.append(edge_record)

            if ric < 0:
                bottlenecks.append(edge_record)
            elif ric > 0:
                clusters.append(edge_record)

        # Sort bottlenecks by most negative curvature first (most severe choke points)
        bottlenecks.sort(key=lambda x: x["curvature"])
        clusters.sort(key=lambda x: x["curvature"], reverse=True)

        avg_ric = sum(e["curvature"] for e in edge_curvatures) / max(1, len(edge_curvatures))

        return {
            "total_edges": len(edge_curvatures),
            "average_curvature": round(avg_ric, 3),
            "bottleneck_count": len(bottlenecks),
            "cluster_edge_count": len(clusters),
            "top_bottlenecks": bottlenecks[:10],
            "top_cluster_edges": clusters[:10],
            "all_curvatures": edge_curvatures
        }

    # ------------------------------------------------------------------------
    # 2. Gromov delta-Hyperbolicity
    # ------------------------------------------------------------------------
    def compute_gromov_hyperbolicity(self, sample_size: int = 50) -> Dict[str, Any]:
        """Compute the Gromov delta-hyperbolicity to measure tree-likeness of the architecture.

        A tree has delta = 0. Smaller delta implies strong hierarchical tree structure
        amenable to hyperbolic Poincaré embeddings.
        """
        if self.n < 4:
            return {"delta": 0.0, "is_tree_like": True, "evaluated_quadruples": 0}

        # Compute all-pairs shortest paths via BFS
        dist: Dict[str, Dict[str, int]] = {}
        for start_node in self.node_ids[:sample_size]:
            d: Dict[str, int] = {start_node: 0}
            q = deque([start_node])
            while q:
                curr = q.popleft()
                curr_d = d[curr]
                for nxt in self.adj[curr]:
                    if nxt not in d:
                        d[nxt] = curr_d + 1
                        q.append(nxt)
            dist[start_node] = d

        nodes_sample = [nid for nid in self.node_ids[:sample_size] if nid in dist]
        m = len(nodes_sample)
        if m < 4:
            return {"delta": 0.0, "is_tree_like": True, "evaluated_quadruples": 0}

        max_delta = 0.0
        count = 0

        # Sample 4-tuples
        import itertools
        for x, y, z, w in itertools.islice(itertools.combinations(nodes_sample, 4), 200):
            # Verify mutual reachability
            if (y in dist[x] and w in dist[z] and
                z in dist[x] and w in dist[y] and
                w in dist[x] and z in dist[y]):

                s1 = dist[x][y] + dist[z][w]
                s2 = dist[x][z] + dist[y][w]
                s3 = dist[x][w] + dist[y][z]

                sorted_sums = sorted([s1, s2, s3], reverse=True)
                delta_quad = (sorted_sums[0] - sorted_sums[1]) / 2.0
                if delta_quad > max_delta:
                    max_delta = delta_quad
                count += 1

        return {
            "delta": max_delta,
            "is_tree_like": max_delta <= 1.5,
            "evaluated_quadruples": count
        }
