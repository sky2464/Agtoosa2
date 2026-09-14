"""First-party deterministic community detection using modularity optimization (DEV-048).

Replaces the previous union-find connected-components fallback with a true modularity
optimizer so that minimal-dependency and optional-dependency installs answer the same
question (modularity clustering vs reachability).
"""

from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any, Optional
import math


def compute_modularity(
    adjacency: Dict[str, Set[str]],
    partition: List[Set[str]],
    total_edges: int
) -> float:
    """Compute Newman's modularity Q for a given partition of an undirected graph.

    Q = sum_c [ (e_c / m) - (a_c / (2m))^2 ]
    where:
      m = total edges
      e_c = number of edges within community c
      a_c = sum of degrees of nodes in community c
    """
    if total_edges <= 0 or not partition:
        return 0.0

    m2 = 2 * total_edges
    q = 0.0

    for community in partition:
        if not community:
            continue
        e_c = 0
        a_c = 0
        for u in community:
            neighbors = adjacency.get(u, set())
            a_c += len(neighbors)
            for v in neighbors:
                if v in community:
                    e_c += 1
        # Each internal edge was counted twice
        e_c = e_c // 2
        q += (e_c / total_edges) - ((a_c / m2) ** 2)

    return q


def detect_communities_modularity(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    node_map: Optional[Dict[str, Dict[str, Any]]] = None,
    prefer_networkx: bool = True
) -> Dict[str, Any]:
    """Detect communities using greedy modularity optimization.

    Guarantees consistent community detection semantics across all install profiles.
    Returns:
      {
        "is_available": bool,
        "algorithm": str,
        "modularity": float,
        "communities": List[Dict[str, Any]],
        "reason": Optional[str]
      }
    """
    if not node_map:
        node_map = {n["id"]: n for n in nodes}

    # Build undirected adjacency excluding self-loops
    adj: Dict[str, Set[str]] = defaultdict(set)
    valid_node_ids = set(node_map.keys())

    edge_set = set()
    for e in edges:
        src = e.get("source_id") or e.get("source")
        tgt = e.get("target_id") or e.get("target")
        if src in valid_node_ids and tgt in valid_node_ids and src != tgt:
            pair = tuple(sorted([src, tgt]))
            if pair not in edge_set:
                edge_set.add(pair)
                adj[src].add(tgt)
                adj[tgt].add(src)

    m = len(edge_set)
    n = len(valid_node_ids)

    if n < 3 or m < 2:
        return {
            "is_available": False,
            "algorithm": "none",
            "modularity": 0.0,
            "communities": [],
            "reason": "Graph too small or too sparse for modularity clustering (requires >= 3 nodes and >= 2 edges)"
        }

    # Try networkx greedy_modularity_communities if requested and available
    if prefer_networkx:
        try:
            import networkx as nx
            g = nx.Graph()
            for nid in valid_node_ids:
                g.add_node(nid)
            for u, v in edge_set:
                g.add_edge(u, v)

            nx_comms = list(nx.community.greedy_modularity_communities(g))
            if nx_comms:
                partition = [set(c) for c in nx_comms]
                q = compute_modularity(adj, partition, m)
                return _format_result(partition, q, "greedy_modularity_networkx", node_map)
        except Exception:
            pass

    # Pure-Python Clauset-Newman-Moore style greedy modularity optimizer
    # Start with each node in its own community
    # Greedily merge pair that maximizes Delta Q
    partition = _pure_python_greedy_modularity(valid_node_ids, adj, edge_set)
    q = compute_modularity(adj, partition, m)

    return _format_result(partition, q, "greedy_modularity_core", node_map)


def _pure_python_greedy_modularity(
    node_ids: Set[str],
    adj: Dict[str, Set[str]],
    edge_set: Set[Tuple[str, ...]]
) -> List[Set[str]]:
    """Greedy agglomerative modularity clustering in pure standard-library Python.

    Maintains deterministic execution by sorting node IDs and tie-breaking consistently.
    """
    m = len(edge_set)
    m2 = 2 * m

    # Initial state: each connected node is in its own community
    # Nodes with 0 edges are left in singleton communities
    active_nodes = [nid for nid in sorted(node_ids) if len(adj.get(nid, set())) > 0]
    isolated_nodes = [nid for nid in sorted(node_ids) if len(adj.get(nid, set())) == 0]

    # Map community_id -> set of member nodes
    comm_members: Dict[int, Set[str]] = {i: {nid} for i, nid in enumerate(active_nodes)}
    # Map node -> community_id
    node_comm: Dict[str, int] = {nid: i for i, nid in enumerate(active_nodes)}

    # Track degree sums a_i = degree of community i
    deg: Dict[int, int] = {i: len(adj[nid]) for i, nid in comm_members.items() for nid in comm_members[i]}

    # Track shared edges between communities: w_ij
    shared_edges: Dict[Tuple[int, int], int] = defaultdict(int)
    for u, v in edge_set:
        c_u = node_comm[u]
        c_v = node_comm[v]
        if c_u != c_v:
            key = tuple(sorted([c_u, c_v]))
            shared_edges[key] += 1

    # Agglomerate while positive Delta Q exists
    while True:
        best_delta = 0.0
        best_pair: Optional[Tuple[int, int]] = None

        # Calculate Delta Q for each adjacent community pair:
        # Delta Q = 2 * (e_ij / m - (deg_i * deg_j) / (2 * m^2))
        for (c1, c2), w_12 in list(shared_edges.items()):
            if w_12 <= 0:
                continue
            delta_q = (w_12 / m) - ((deg[c1] * deg[c2]) / (2 * (m ** 2)))
            if delta_q > best_delta:
                best_delta = delta_q
                best_pair = (c1, c2)
            elif delta_q == best_delta and best_pair is not None:
                # Deterministic tie-breaking
                if (c1, c2) < best_pair:
                    best_pair = (c1, c2)

        if not best_pair or best_delta <= 0:
            break

        c_target, c_source = best_pair
        # Merge c_source into c_target
        comm_members[c_target].update(comm_members[c_source])
        for nid in comm_members[c_source]:
            node_comm[nid] = c_target
        deg[c_target] += deg[c_source]
        del comm_members[c_source]
        del deg[c_source]

        # Update shared edges
        new_shared = defaultdict(int)
        for (c1, c2), w in shared_edges.items():
            if c1 == c_source:
                c1 = c_target
            if c2 == c_source:
                c2 = c_target
            if c1 != c2:
                key = tuple(sorted([c1, c2]))
                new_shared[key] += w
        shared_edges = new_shared

    partition = list(comm_members.values())
    if isolated_nodes:
        # Group isolated nodes or keep as separate singletons
        for iso in isolated_nodes:
            partition.append({iso})

    return partition


def _format_result(
    partition: List[Set[str]],
    modularity: float,
    algorithm: str,
    node_map: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Format partition into standard community dictionaries."""
    results = []
    # Sort communities by size descending, then by lowest member ID for determinism
    sorted_partition = sorted(partition, key=lambda c: (-len(c), sorted(list(c))[0] if c else ""))

    for idx, comm in enumerate(sorted_partition, start=1):
        member_types = defaultdict(int)
        for nid in comm:
            ntype = node_map.get(nid, {}).get("node_type", "unknown")
            member_types[ntype] += 1

        sample = [node_map.get(nid, {}).get("name", nid) for nid in sorted(list(comm))[:5]]
        results.append({
            "community_id": idx,
            "size": len(comm),
            "node_types": dict(member_types),
            "members": sorted(list(comm)),
            "sample_members": sample
        })

    return {
        "is_available": True,
        "algorithm": algorithm,
        "modularity": round(modularity, 4),
        "communities": results,
        "reason": None
    }
