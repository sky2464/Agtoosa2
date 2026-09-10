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

    # 2. Try prefixed domain entity IDs
    for prefix in ("story:", "task:", "criterion:", "adr:", "file:"):
        prefixed_node = store.get_node(f"{prefix}{clean_q}")
        if prefixed_node:
            return prefixed_node

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
    """Compute the upstream blast radius using in-database Recursive CTE for ultra-fast traversal."""
    target_node = resolve_node(store, target_query)
    if not target_node:
        return None

    target_id = target_node["id"]
    safe_depth = max(1, min(max_depth, 10))

    query_sql = """
    WITH RECURSIVE impact_cte(curr_id, depth, rel_type, via_id) AS (
        SELECT source_id, 1, edge_type, target_id
        FROM edges
        WHERE target_id = ?

        UNION

        SELECT e.source_id, ic.depth + 1, e.edge_type, e.target_id
        FROM edges e
        JOIN impact_cte ic ON e.target_id = ic.curr_id
        WHERE ic.depth < ?
    )
    SELECT ic.curr_id AS id, n.name, n.node_type, n.path, MIN(ic.depth) AS depth, ic.rel_type, ic.via_id
    FROM impact_cte ic
    JOIN nodes n ON ic.curr_id = n.id
    WHERE ic.curr_id != ?
    GROUP BY ic.curr_id
    ORDER BY depth ASC, n.name ASC;
    """

    with store._get_connection() as conn:
        rows = conn.execute(query_sql, (target_id, safe_depth, target_id)).fetchall()
        impacted_nodes = [
            {
                "id": r["id"],
                "name": r["name"],
                "node_type": r["node_type"],
                "path": r["path"],
                "depth": r["depth"],
                "relationship": r["rel_type"],
                "via": r["via_id"]
            }
            for r in rows
        ]

    return {
        "target": target_node,
        "impacted_count": len(impacted_nodes),
        "impacted": impacted_nodes
    }
