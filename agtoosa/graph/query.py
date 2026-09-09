"""Graph investigation and traversal algorithms: explain, path, and impact."""

from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.graph.store import GraphStore


def resolve_node(store: GraphStore, query: str) -> Optional[Dict[str, Any]]:
    """Resolve a target query string to a specific node."""
    clean_q = query.strip()

    # 1. Try exact node ID match
    node = store.get_node(clean_q)
    if node:
        return node

    # 2. Try file:<clean_q>
    file_node = store.get_node(f"file:{clean_q}")
    if file_node:
        return file_node

    # 3. Try exact path match in nodes table
    with store._get_connection() as conn:
        row = conn.execute("SELECT id FROM nodes WHERE path = ? AND node_type = 'file';", (clean_q,)).fetchone()
        if row:
            return store.get_node(row[0])

        # Try exact name match
        row = conn.execute("SELECT id FROM nodes WHERE name = ? ORDER BY (node_type = 'class') DESC, (node_type = 'function') DESC LIMIT 1;", (clean_q,)).fetchone()
        if row:
            return store.get_node(row[0])

    # 4. Fallback to FTS match
    results = store.query_fts(clean_q, limit=5)
    if results:
        for r in results:
            if r["name"].lower() == clean_q.lower():
                return store.get_node(r["id"])
        return store.get_node(results[0]["id"])

    return None


def explain_node(store: GraphStore, target: str) -> Optional[Dict[str, Any]]:
    """Explain a symbol or file: definition, incoming callers, outgoing callees, and imports."""
    node = resolve_node(store, target)
    if not node:
        return None

    neighbors = store.get_neighbors(node["id"], direction="both")

    incoming = []
    outgoing = []

    for n in neighbors:
        direction = n.get("direction")
        edge_type = n.get("edge_type")
        item = {
            "id": n["id"],
            "name": n["name"],
            "type": n["node_type"],
            "path": n["path"],
            "edge_type": edge_type
        }
        if direction == "in":
            incoming.append(item)
        else:
            outgoing.append(item)

    return {
        "node": node,
        "incoming": incoming,
        "outgoing": outgoing
    }


def find_path(store: GraphStore, source_query: str, target_query: str, max_depth: int = 5) -> Optional[List[Dict[str, Any]]]:
    """Find the shortest directed path between two entities using BFS."""
    source_node = resolve_node(store, source_query)
    target_node = resolve_node(store, target_query)

    if not source_node or not target_node:
        return None

    if source_node["id"] == target_node["id"]:
        return [{"node": source_node, "edge": None}]

    queue = deque([([source_node["id"]], [])])  # (node_path, edge_path)
    visited: Set[str] = {source_node["id"]}

    while queue:
        current_path, current_edges = queue.popleft()
        curr_id = current_path[-1]

        if len(current_path) > max_depth:
            continue

        neighbors = store.get_neighbors(curr_id, direction="out")
        for neighbor in neighbors:
            nxt_id = neighbor["id"]
            edge_info = {
                "source": curr_id,
                "target": nxt_id,
                "edge_type": neighbor["edge_type"]
            }

            if nxt_id == target_node["id"]:
                full_node_ids = current_path + [nxt_id]
                full_edges = current_edges + [edge_info]
                # Reconstruct full path
                res = []
                for idx, nid in enumerate(full_node_ids):
                    n_data = store.get_node(nid) or {"id": nid, "name": nid}
                    e_data = full_edges[idx - 1] if idx > 0 else None
                    res.append({"node": n_data, "edge": e_data})
                return res

            if nxt_id not in visited:
                visited.add(nxt_id)
                queue.append((current_path + [nxt_id], current_edges + [edge_info]))

    return None


def compute_impact(store: GraphStore, target_query: str, max_depth: int = 3) -> Optional[Dict[str, Any]]:
    """Compute the upstream blast radius (who calls or depends on target)."""
    target_node = resolve_node(store, target_query)
    if not target_node:
        return None

    queue = deque([(target_node["id"], 0)])
    visited: Set[str] = {target_node["id"]}

    impacted_nodes: List[Dict[str, Any]] = []

    while queue:
        curr_id, depth = queue.popleft()
        if depth >= max_depth:
            continue

        # Ingress: who points to curr_id?
        in_neighbors = store.get_neighbors(curr_id, direction="in")
        for neighbor in in_neighbors:
            nxt_id = neighbor["id"]
            if nxt_id not in visited:
                visited.add(nxt_id)
                impacted_nodes.append({
                    "id": neighbor["id"],
                    "name": neighbor["name"],
                    "node_type": neighbor["node_type"],
                    "path": neighbor["path"],
                    "depth": depth + 1,
                    "relationship": neighbor["edge_type"],
                    "via": curr_id
                })
                queue.append((nxt_id, depth + 1))

    return {
        "target": target_node,
        "impacted_count": len(impacted_nodes),
        "impacted": impacted_nodes
    }
