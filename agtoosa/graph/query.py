"""Graph investigation and traversal algorithms: explain, path, and impact."""

from collections import deque
import json
from typing import Any, Dict, List, Optional, Set, Tuple


from agtoosa.graph.store import GraphStore


from agtoosa.parser.resolver import resolve_node_candidates, ResolutionStatus, ResolutionResult


def resolve_node(store: GraphStore, query: str) -> Optional[Dict[str, Any]]:
    """Resolve a target query string to a specific node using honest candidate resolution (DEV-041)."""
    res = resolve_node_candidates(store, query)
    if res.status == ResolutionStatus.RESOLVED and res.selected_id:
        return store.get_node(res.selected_id)
    # If ambiguous, fall back to first candidate but include candidate list in metadata
    if res.candidates:
        node = store.get_node(res.candidates[0].node_id)
        if node:
            node = dict(node)
            node["_resolution_status"] = res.status.value
            node["_candidates"] = [c.node_id for c in res.candidates]
            return node
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


def compute_impact(
    store: GraphStore,
    target_query: str,
    max_depth: int = 3,
    federated: bool = True,
    production: bool = False
) -> Optional[Dict[str, Any]]:
    """Compute the upstream blast radius across local and federated repositories with optional runtime traffic weighting."""
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
        impacted_nodes: List[Dict[str, Any]] = []
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
                "id": str(r["id"]),
                "name": str(r["name"]),
                "node_type": str(r["node_type"]),
                "path": str(r["path"]) if r["path"] is not None else None,
                "depth": int(r["depth"]) if r["depth"] is not None else 1,
                "relationship": str(r["rel_type"]) if r["rel_type"] is not None else None,
                "via": str(r["via_id"]) if r["via_id"] is not None else None,
                "repo": str(repo)
            })

    repos_impacted = sorted(list(set(str(imp["repo"]) for imp in impacted_nodes if imp["repo"] != "local")))

    prod_summary = None
    if production:
        all_telem = store.get_all_telemetry()
        target_telem = all_telem.get(target_id, {})
        target_calls = target_telem.get("call_count", 0)

        total_traffic = target_calls
        weighted_traffic_score = float(target_calls)
        active_callers = 0
        dormant_callers = 0

        for imp in impacted_nodes:
            t = all_telem.get(str(imp["id"]), {})
            calls = t.get("call_count", 0)
            avg_ms = t.get("avg_duration_ms", 0.0)
            err_rate = t.get("error_rate", 0.0)

            imp["call_count"] = calls
            imp["avg_duration_ms"] = round(avg_ms, 2)
            imp["error_rate"] = round(err_rate, 4)
            imp["is_active"] = calls > 0

            total_traffic += calls
            depth = max(1, int(imp["depth"]))
            weighted_traffic_score += (calls * (1.0 + 2.0 * err_rate)) / (depth ** 1.5)

            if calls > 0:
                active_callers += 1
            else:
                dormant_callers += 1

        # Determine Production Risk Tier
        if total_traffic >= 10000 or any(float(i.get("error_rate", 0)) >= 0.15 and int(i.get("call_count", 0)) >= 100 for i in impacted_nodes):
            risk_tier = "P0_CRITICAL"
        elif total_traffic >= 1000:
            risk_tier = "P1_HIGH"
        elif total_traffic >= 100:
            risk_tier = "P2_MODERATE"
        elif total_traffic > 0:
            risk_tier = "P3_LOW"
        else:
            risk_tier = "P4_DORMANT"

        # Sort impacted nodes by traffic volume descending
        impacted_nodes.sort(key=lambda x: (int(x.get("call_count", 0)), -int(x.get("depth", 1))), reverse=True)

        prod_summary = {
            "risk_tier": risk_tier,
            "total_traffic_at_risk": total_traffic,
            "target_traffic": target_calls,
            "traffic_weighted_score": round(weighted_traffic_score, 2),
            "active_callers_count": active_callers,
            "dormant_callers_count": dormant_callers
        }

    return {
        "target": target_node,
        "impacted_count": len(impacted_nodes),
        "impacted": impacted_nodes,
        "federated_repos_impacted": repos_impacted,
        "production_blast_radius": prod_summary
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


def query_routes(store: GraphStore, method: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query all detected HTTP API endpoints and their bound handler functions."""
    with store._get_connection() as conn:
        query_sql = "SELECT id, name, path, start_line, metadata_json FROM nodes WHERE node_type = 'endpoint'"
        params = []
        if method:
            query_sql += " AND id LIKE ?"
            params.append(f"endpoint:{method.upper()}:%")
        query_sql += " ORDER BY path, name;"

        rows = conn.execute(query_sql, params).fetchall()
        results = []
        for r in rows:
            meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
            ep_id = r["id"]

            # Find bound handler via routes_to edge
            handler_edge = conn.execute(
                "SELECT target_id, metadata_json FROM edges WHERE source_id = ? AND edge_type = 'routes_to';",
                (ep_id,)
            ).fetchone()

            handler_node = None
            injected_deps = []
            if handler_edge:
                handler_node = store.get_node(handler_edge["target_id"])
                # Find any injected dependencies for this handler
                if handler_node:
                    inj_edges = conn.execute(
                        "SELECT target_id, metadata_json FROM edges WHERE source_id = ? AND edge_type = 'injects';",
                        (handler_node["id"],)
                    ).fetchall()
                    for ie in inj_edges:
                        dep_meta = json.loads(ie["metadata_json"]) if ie["metadata_json"] else {}
                        injected_deps.append({
                            "target_id": ie["target_id"],
                            "param": dep_meta.get("param"),
                            "provider": dep_meta.get("provider")
                        })

            results.append({
                "id": ep_id,
                "name": r["name"],
                "http_method": meta.get("http_method", ep_id.split(":")[1] if ":" in ep_id else "UNKNOWN"),
                "path": meta.get("path", ep_id.split(":", 2)[-1] if ":" in ep_id else ""),
                "framework": meta.get("framework", "unknown"),
                "file_path": r["path"],
                "start_line": r["start_line"],
                "handler": handler_node,
                "injected_dependencies": injected_deps
            })
        return results


def query_di(store: GraphStore, symbol: str) -> Dict[str, Any]:
    """Query dependency injection dependencies and consumers for a symbol."""
    target_node = resolve_node(store, symbol)
    if not target_node:
        # Fallback: check symbol placeholder (e.g. symbol:name)
        with store._get_connection() as conn:
            row = conn.execute("SELECT id, name, node_type, path FROM nodes WHERE name = ? LIMIT 1;", (symbol,)).fetchone()
            if row:
                target_node = dict(row)

    if not target_node:
        return {"target": None, "injected_into_target": [], "consumers_injecting_target": []}

    target_id = target_node["id"]
    target_name = target_node.get("name", symbol)
    with store._get_connection() as conn:
        # What does target_id inject?
        outgoing_inj = conn.execute(
            "SELECT target_id, metadata_json FROM edges WHERE source_id = ? AND edge_type = 'injects';",
            (target_id,)
        ).fetchall()
        injected = []
        for row in outgoing_inj:
            meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
            provider_node = store.get_node(row["target_id"])
            injected.append({
                "target_id": row["target_id"],
                "param": meta.get("param"),
                "provider": meta.get("provider"),
                "node": provider_node
            })

        # Who injects target_id or symbol placeholder?
        incoming_inj = conn.execute(
            "SELECT source_id, metadata_json FROM edges WHERE (target_id = ? OR target_id = ?) AND edge_type = 'injects';",
            (target_id, f"symbol:{target_name}")
        ).fetchall()
        consumers = []
        for row in incoming_inj:
            meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
            caller_node = store.get_node(row["source_id"])
            consumers.append({
                "source_id": row["source_id"],
                "param": meta.get("param"),
                "caller": caller_node
            })

        return {
            "target": target_node,
            "injected_into_target": injected,
            "consumers_injecting_target": consumers
        }


def query_events(store: GraphStore, topic: Optional[str] = None) -> Dict[str, Any]:
    """Query message queue topics, publishers, subscribers, and event lineage."""
    with store._get_connection() as conn:
        if topic:
            # Query specific topic or matching pattern
            rows = conn.execute(
                "SELECT id, name, node_type, path, start_line, metadata_json FROM nodes "
                "WHERE node_type = 'topic' AND (name = ? OR id = ? OR name LIKE ?) ORDER BY name ASC;",
                (topic, f"topic:{topic}", f"%{topic}%")
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, node_type, path, start_line, metadata_json FROM nodes "
                "WHERE node_type = 'topic' ORDER BY name ASC;"
            ).fetchall()

        topics_data = []
        orphan_count = 0
        total_publishers = 0
        total_subscribers = 0

        for r in rows:
            top_id = r["id"]
            meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
            broker = meta.get("broker", "unknown")

            # Fetch publishers (edges with target_id = top_id and edge_type = 'publishes')
            pub_edges = conn.execute(
                "SELECT source_id, metadata_json FROM edges WHERE target_id = ? AND edge_type = 'publishes';",
                (top_id,)
            ).fetchall()

            publishers = []
            for pe in pub_edges:
                p_meta = json.loads(pe["metadata_json"]) if pe["metadata_json"] else {}
                p_node = store.get_node(pe["source_id"])
                publishers.append({
                    "id": pe["source_id"],
                    "node": p_node,
                    "metadata": p_meta
                })
                total_publishers += 1

            # Fetch subscribers (edges with target_id = top_id and edge_type = 'subscribes')
            sub_edges = conn.execute(
                "SELECT source_id, metadata_json FROM edges WHERE target_id = ? AND edge_type = 'subscribes';",
                (top_id,)
            ).fetchall()

            subscribers = []
            for se in sub_edges:
                s_meta = json.loads(se["metadata_json"]) if se["metadata_json"] else {}
                s_node = store.get_node(se["source_id"])
                subscribers.append({
                    "id": se["source_id"],
                    "node": s_node,
                    "metadata": s_meta
                })
                total_subscribers += 1

            is_orphan = len(publishers) == 0 or len(subscribers) == 0
            orphan_reason = None
            if len(publishers) == 0 and len(subscribers) == 0:
                orphan_reason = "isolated"
                orphan_count += 1
            elif len(publishers) == 0:
                orphan_reason = "no_publishers"
                orphan_count += 1
            elif len(subscribers) == 0:
                orphan_reason = "no_subscribers"
                orphan_count += 1

            topics_data.append({
                "id": top_id,
                "name": r["name"],
                "broker": broker,
                "path": r["path"],
                "start_line": r["start_line"],
                "publishers": publishers,
                "subscribers": subscribers,
                "is_orphan": is_orphan,
                "orphan_reason": orphan_reason
            })

        return {
            "total_topics": len(topics_data),
            "total_publishers": total_publishers,
            "total_subscribers": total_subscribers,
            "orphan_count": orphan_count,
            "topics": topics_data
        }


def query_topology(store: GraphStore, service: Optional[str] = None) -> Dict[str, Any]:
    """Query runtime distributed service topology, cross-service RPC/HTTP links, and latency bottlenecks."""
    import json
    with store._get_connection() as conn:
        svc_rows = conn.execute(
            "SELECT id, name, node_type, path, metadata_json FROM nodes WHERE node_type = 'service';"
        ).fetchall()

        edge_rows = conn.execute(
            "SELECT source_id, target_id, edge_type, provenance, metadata_json FROM edges WHERE edge_type = 'network_calls';"
        ).fetchall()

    services_map: Dict[str, Dict[str, Any]] = {}
    for r in svc_rows:
        meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
        services_map[r["id"]] = {
            "id": r["id"],
            "name": r["name"],
            "path": r["path"],
            "metadata": meta,
            "incoming": [],
            "outgoing": [],
            "total_ingress_calls": 0,
            "total_egress_calls": 0
        }

    edges_list: List[Dict[str, Any]] = []
    for er in edge_rows:
        meta = json.loads(er["metadata_json"]) if er["metadata_json"] else {}
        calls = meta.get("call_count", 0)
        avg_lat = meta.get("avg_duration_ms", 0.0)
        p95_lat = meta.get("p95_duration_ms", avg_lat)
        err_rate = meta.get("error_rate", 0.0)

        edge_info = {
            "source_id": er["source_id"],
            "target_id": er["target_id"],
            "call_count": calls,
            "total_duration_ms": meta.get("total_duration_ms", 0.0),
            "avg_duration_ms": avg_lat,
            "p50_duration_ms": meta.get("p50_duration_ms", avg_lat),
            "p95_duration_ms": p95_lat,
            "p99_duration_ms": meta.get("p99_duration_ms", p95_lat),
            "error_count": meta.get("error_count", 0),
            "error_rate": err_rate,
            "protocols": meta.get("protocols", []),
            "operations": meta.get("operations", [])
        }
        edges_list.append(edge_info)

        if er["source_id"] in services_map:
            services_map[er["source_id"]]["outgoing"].append(edge_info)
            services_map[er["source_id"]]["total_egress_calls"] += calls

        if er["target_id"] in services_map:
            services_map[er["target_id"]]["incoming"].append(edge_info)
            services_map[er["target_id"]]["total_ingress_calls"] += calls

    # Filter by specific service if requested
    target_service_id = None
    if service:
        clean_name = service.lower().replace("service:", "")
        for sid, sdata in services_map.items():
            if sdata["name"].lower() == clean_name or sid.lower() == f"service:{clean_name}":
                target_service_id = sid
                break

    if target_service_id:
        connected_ids = {target_service_id}
        for e in edges_list:
            if e["source_id"] == target_service_id:
                connected_ids.add(e["target_id"])
            if e["target_id"] == target_service_id:
                connected_ids.add(e["source_id"])

        services_map = {sid: sdata for sid, sdata in services_map.items() if sid in connected_ids}
        edges_list = [
            e for e in edges_list
            if e["source_id"] in connected_ids and e["target_id"] in connected_ids
        ]

    # Detect Latency Bottlenecks (p95 >= 300ms or high average latency)
    bottlenecks = [
        e for e in edges_list
        if e["p95_duration_ms"] >= 300.0 or e["avg_duration_ms"] >= 200.0
    ]
    bottlenecks.sort(key=lambda x: x["p95_duration_ms"], reverse=True)

    # Detect Error Hotspots (error_rate >= 0.05 or error_count > 0)
    error_hotspots = [
        e for e in edges_list
        if e["error_rate"] >= 0.05 or e["error_count"] > 0
    ]
    error_hotspots.sort(key=lambda x: x["error_rate"], reverse=True)

    # Detect Circular Service Dependencies (A -> B -> A)
    circular_deps = []
    edge_pairs = set((e["source_id"], e["target_id"]) for e in edges_list)
    for (src, tgt) in edge_pairs:
        if src.startswith("service:") and tgt.startswith("service:") and src < tgt:
            if (tgt, src) in edge_pairs:
                circular_deps.append({
                    "service_a": src,
                    "service_b": tgt,
                    "description": f"Bidirectional network call dependency between {src} and {tgt}"
                })

    return {
        "services": list(services_map.values()),
        "network_edges": edges_list,
        "bottlenecks": bottlenecks,
        "error_hotspots": error_hotspots,
        "circular_dependencies": circular_deps,
        "total_services": len(services_map),
        "total_network_edges": len(edges_list),
        "total_calls": sum(e["call_count"] for e in edges_list)
    }



