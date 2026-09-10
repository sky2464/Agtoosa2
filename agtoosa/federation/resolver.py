"""Cross-repository contract linker: connects consumer code calls to federated endpoints."""

from __future__ import annotations
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore


class CrossRepoLinker:
    """Scans consumer code for HTTP/RPC/GraphQL calls and connects them to provider endpoints."""

    def __init__(self, store: GraphStore):
        self.store = store

    def link_cross_repo_dependencies(self, workspace_root: Path) -> List[Edge]:
        """Scan workspace files and link API calls to known endpoints in the graph store."""
        # 1. Gather all endpoints from the graph store
        endpoints: Dict[str, Dict[str, Any]] = {}
        with self.store._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, name, path, metadata_json
                FROM nodes
                WHERE node_type = 'function' AND (
                    id LIKE '%endpoint:%' OR id LIKE '%rpc:%' OR id LIKE '%graphql:%'
                );
            """).fetchall()

            for r in rows:
                meta = {}
                try:
                    import json
                    meta = json.loads(r["metadata_json"] or "{}")
                except Exception:
                    pass

                route = meta.get("route")
                method = meta.get("method")
                rpc_method = meta.get("method") if meta.get("protocol") == "grpc" else None

                endpoints[r["id"]] = {
                    "id": r["id"],
                    "name": r["name"],
                    "route": route,
                    "method": method,
                    "rpc_method": rpc_method,
                    "repo": meta.get("repo", "local")
                }

        if not endpoints:
            return []

        # 2. Build fast lookup maps
        route_to_endpoint: Dict[str, str] = {}
        rpc_to_endpoint: Dict[str, str] = {}
        for ep_id, ep_info in endpoints.items():
            if ep_info.get("route"):
                # Normalize route: remove trailing slashes
                clean_route = ep_info["route"].rstrip("/")
                route_to_endpoint[clean_route] = ep_id
            if ep_info.get("rpc_method"):
                rpc_to_endpoint[ep_info["rpc_method"]] = ep_id

        # 3. Find client functions in local nodes
        client_nodes = []
        with self.store._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, name, path, start_line, end_line
                FROM nodes
                WHERE node_type = 'function' AND id NOT LIKE 'repo:%' AND id NOT LIKE 'endpoint:%' AND id NOT LIKE 'rpc:%';
            """).fetchall()
            client_nodes = [dict(r) for r in rows]

        edges: List[Edge] = []
        seen_edges: Set[Tuple[str, str]] = set()

        # 4. Group by file to read file content once
        files_to_check: Dict[str, List[Dict[str, Any]]] = {}
        for cn in client_nodes:
            p = cn["path"]
            if p not in files_to_check:
                files_to_check[p] = []
            files_to_check[p].append(cn)

        # Regexes for HTTP routes and RPC calls
        http_pattern = re.compile(r"""(?:fetch|get|post|put|delete|patch|request|axios|url)\s*[(:=]\s*["']([^"']+)["']""", re.IGNORECASE)

        for rel_path, funcs in files_to_check.items():
            full_path = workspace_root / rel_path
            if not full_path.exists() or not full_path.is_file():
                continue

            try:
                content = full_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
            except Exception:
                continue

            for fn in funcs:
                s_line = max(1, (fn.get("start_line") or 1))
                e_line = min(len(lines), (fn.get("end_line") or len(lines)))
                fn_text = "\n".join(lines[s_line - 1:e_line])

                # Check HTTP route matches
                for m in http_pattern.finditer(fn_text):
                    url_or_route = m.group(1).split("?")[0].rstrip("/")
                    # Find matching endpoint
                    matched_ep_id = None
                    for known_route, ep_id in route_to_endpoint.items():
                        if url_or_route == known_route or url_or_route.endswith(known_route):
                            matched_ep_id = ep_id
                            break

                    if matched_ep_id and (fn["id"], matched_ep_id) not in seen_edges:
                        seen_edges.add((fn["id"], matched_ep_id))
                        edges.append(Edge(
                            source_id=fn["id"],
                            target_id=matched_ep_id,
                            edge_type=EdgeType.CALLS,
                            provenance="federated_contract",
                            metadata={"cross_repo": True, "route": url_or_route}
                        ))

                # Check gRPC method invocations
                for rpc_name, ep_id in rpc_to_endpoint.items():
                    if f".{rpc_name}(" in fn_text:
                        if (fn["id"], ep_id) not in seen_edges:
                            seen_edges.add((fn["id"], ep_id))
                            edges.append(Edge(
                                source_id=fn["id"],
                                target_id=ep_id,
                                edge_type=EdgeType.CALLS,
                                provenance="federated_contract",
                                metadata={"cross_repo": True, "rpc": rpc_name}
                            ))

        return edges
