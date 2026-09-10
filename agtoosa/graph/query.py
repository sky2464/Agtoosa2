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


def compute_impact(store: GraphStore, target_query: str, max_depth: int = 3, federated: bool = True) -> Optional[Dict[str, Any]]:
    """Compute the upstream blast radius across local and federated repositories."""
    import json
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
    SELECT ic.curr_id AS id, n.name, n.node_type, n.path, n.metadata_json, MIN(ic.depth) AS depth, ic.rel_type, ic.via_id
    FROM impact_cte ic
    JOIN nodes n ON ic.curr_id = n.id
    WHERE ic.curr_id != ?
    GROUP BY ic.curr_id
    ORDER BY depth ASC, n.name ASC;
    """

    with store._get_connection() as conn:
        rows = conn.execute(query_sql, (target_id, safe_depth, target_id)).fetchall()
        impacted_nodes = []
        for r in rows:
            meta = {}
            try:
                meta = json.loads(r["metadata_json"] or "{}")
            except Exception:
                pass

            repo = meta.get("repo", "local")
            if not federated and (repo != "local" or r["id"].startswith("repo:")):
                continue

            impacted_nodes.append({
                "id": r["id"],
                "name": r["name"],
                "node_type": r["node_type"],
                "path": r["path"],
                "depth": r["depth"],
                "relationship": r["rel_type"],
                "via": r["via_id"],
                "repo": repo
            })

    repos_impacted = sorted(list(set(imp["repo"] for imp in impacted_nodes if imp["repo"] != "local")))

    return {
        "target": target_node,
        "impacted_count": len(impacted_nodes),
        "impacted": impacted_nodes,
        "federated_repos_impacted": repos_impacted
    }


def hybrid_search(
    store: GraphStore,
    query: str,
    top_k: int = 10,
    rrf_k: int = 60
) -> List[Dict[str, Any]]:
    """Hybrid GraphRAG search combining FTS5 BM25 lexical ranking and dense vector semantic similarity using Reciprocal Rank Fusion (RRF)."""
    from agtoosa.graph.embeddings import SemanticEmbeddingEngine

    clean_q = query.strip()
    if not clean_q:
        return []

    # 1. Lexical search via SQLite FTS5
    fts_results = store.query_fts(clean_q, limit=max(top_k * 3, 20))
    fts_map: Dict[str, Tuple[int, Dict[str, Any]]] = {}
    for rank, item in enumerate(fts_results, start=1):
        fts_map[item["id"]] = (rank, item)

    # 2. Dense semantic vector similarity search
    engine = SemanticEmbeddingEngine()
    vec_results = engine.search(store, clean_q, top_k=max(top_k * 3, 20))
    vec_map: Dict[str, Tuple[int, float, Dict[str, Any]]] = {}
    for item in vec_results:
        vec_map[item["node"]["id"]] = (item["rank"], item["score"], item["node"])

    # 3. Reciprocal Rank Fusion (RRF)
    all_candidate_ids = set(fts_map.keys()) | set(vec_map.keys())
    if not all_candidate_ids:
        return []

    fused: List[Dict[str, Any]] = []
    for cid in all_candidate_ids:
        fts_rank = fts_map[cid][0] if cid in fts_map else None
        vec_rank = vec_map[cid][0] if cid in vec_map else None
        vec_score = vec_map[cid][1] if cid in vec_map else 0.0

        rrf_score = 0.0
        if fts_rank is not None:
            rrf_score += 1.0 / (rrf_k + fts_rank)
        if vec_rank is not None:
            rrf_score += 1.0 / (rrf_k + vec_rank)

        # Resolve node metadata
        node = None
        if cid in vec_map:
            node = vec_map[cid][2]
        elif cid in fts_map:
            node = store.get_node(cid) or fts_map[cid][1]
        else:
            node = store.get_node(cid)

        if not node:
            continue

        match_source = "hybrid" if (fts_rank and vec_rank) else ("lexical" if fts_rank else "semantic")

        fused.append({
            "node": node,
            "rrf_score": round(rrf_score, 6),
            "vector_score": round(vec_score, 4),
            "fts_rank": fts_rank,
            "vector_rank": vec_rank,
            "match_source": match_source
        })

    # Sort descending by RRF score, tie-breaking by vector score
    fused.sort(key=lambda x: (x["rrf_score"], x["vector_score"]), reverse=True)
    return fused[:top_k]
