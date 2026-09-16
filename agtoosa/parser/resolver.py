"""Scoped symbol resolution and candidate set disambiguation (DEV-041).

Addresses R-02 and R-03 by replacing flat global symbol mapping with lexical/module
scoped resolution, preserving unbound reference facts, and refusing to guess targets
when queries or references are ambiguous.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

from agtoosa.graph.store import GraphStore


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


@dataclass
class ResolutionCandidate:
    """A candidate node matching an ambiguous reference or query."""
    node_id: str
    name: str
    node_type: str
    path: str
    score: float = 1.0


@dataclass
class ResolutionResult:
    """Outcome of symbol or node resolution with full provenance."""
    status: ResolutionStatus
    selected_id: Optional[str] = None
    candidates: List[ResolutionCandidate] = field(default_factory=list)
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "selected_id": self.selected_id,
            "candidates": [
                {
                    "node_id": c.node_id,
                    "name": c.name,
                    "node_type": c.node_type,
                    "path": c.path,
                    "score": c.score
                }
                for c in self.candidates
            ],
            "reason": self.reason
        }


class SymbolResolver:
    """Resolves cross-file imports and function calls using scoped candidate sets."""

    def __init__(self, store: GraphStore):
        self.store = store

    def resolve_all_symbols(self) -> Dict[str, int]:
        """Execute scoped cross-file symbol resolution against the SQLite graph store.

        Returns counts: {'resolved': N, 'ambiguous': N, 'unresolved': N}
        """
        stats = {"resolved": 0, "ambiguous": 0, "unresolved": 0}

        with self.store._get_connection() as conn:
            # 1. Build multi-candidate symbol map
            symbol_rows = conn.execute(
                "SELECT id, name, node_type, path FROM nodes WHERE node_type IN ('class', 'function', 'endpoint', 'service');"
            ).fetchall()

            # Map: short_name -> List[ResolutionCandidate]
            candidates_by_name: Dict[str, List[ResolutionCandidate]] = defaultdict(list)
            # Map: (normalized_module_path, short_name) -> ResolutionCandidate
            scoped_candidates: Dict[Tuple[str, str], ResolutionCandidate] = {}

            for nid, name, ntype, path in symbol_rows:
                cand = ResolutionCandidate(node_id=nid, name=name, node_type=ntype, path=path or "")
                candidates_by_name[name].append(cand)
                if path:
                    mod_key = path.replace("\\", "/").rsplit(".", 1)[0]
                    scoped_candidates[(mod_key, name)] = cand

            # 2. Build import map per file: file_path -> {imported_name: target_module_or_name}
            import_rows = conn.execute(
                "SELECT id, name, path FROM nodes WHERE node_type = 'import';"
            ).fetchall()

            file_imports: Dict[str, Dict[str, str]] = defaultdict(dict)
            resolution_edges = []

            for imp_id, full_import_name, imp_path in import_rows:
                short_name = full_import_name.split(".")[-1]
                file_imports[imp_path][short_name] = full_import_name

                # Try resolving import to an exact symbol or module
                cands = candidates_by_name.get(short_name, [])
                if len(cands) == 1:
                    target_id = cands[0].node_id
                    if target_id != imp_id:
                        resolution_edges.append((imp_id, target_id, "references", "resolved", json.dumps({"resolution": "unambiguous"})))
                        stats["resolved"] += 1
                        if imp_path.startswith(("tests/", "test_")) and cands[0].node_type in ("function", "class", "service", "endpoint"):
                            resolution_edges.append((imp_id, target_id, "verifies", "test_import_proof", json.dumps({"resolution": "unambiguous"})))
                elif len(cands) > 1:
                    # Ambiguous import candidates
                    cand_ids = [c.node_id for c in cands]
                    meta = json.dumps({"status": "ambiguous", "candidates": cand_ids})
                    for c in cands:
                        resolution_edges.append((imp_id, c.node_id, "references", "ambiguous", meta))
                    stats["ambiguous"] += 1
                else:
                    stats["unresolved"] += 1

            if resolution_edges:
                conn.executemany(
                    """
                    INSERT INTO edges (source_id, target_id, edge_type, provenance, metadata_json)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    resolution_edges
                )

            # 3. Resolve function calls with honest scoping and reference fact preservation
            call_edges = conn.execute(
                "SELECT rowid, source_id, target_id, metadata_json FROM edges WHERE target_id LIKE 'func_call:%';"
            ).fetchall()

            for rowid, src_id, tgt_placeholder, raw_meta in call_edges:
                callee_name = tgt_placeholder.split(":", 1)[-1]
                meta = json.loads(raw_meta) if raw_meta else {}
                meta["original_reference"] = callee_name

                # Check if caller has an explicit import matching callee_name
                caller_node = conn.execute("SELECT path FROM nodes WHERE id = ?;", (src_id,)).fetchone()
                caller_path = caller_node[0] if caller_node else ""

                resolved_cand = None
                if caller_path in file_imports and callee_name in file_imports[caller_path]:
                    imported_target = file_imports[caller_path][callee_name]
                    target_mod = imported_target.replace(".", "/")
                    # Look up by module and short name
                    for (mod_key, sym_name), cand in scoped_candidates.items():
                        if sym_name == callee_name and (target_mod.endswith(mod_key) or mod_key.endswith(target_mod)):
                            resolved_cand = cand
                            break

                if not resolved_cand:
                    # Fallback to candidate list
                    cands = candidates_by_name.get(callee_name, [])
                    if len(cands) == 1:
                        resolved_cand = cands[0]
                    elif len(cands) > 1:
                        # Ambiguous: Do not guess an arbitrary target! Keep original placeholder and record candidates
                        meta["resolution_status"] = "ambiguous"
                        meta["candidates"] = [c.node_id for c in cands]
                        conn.execute(
                            "UPDATE edges SET provenance = 'ambiguous', metadata_json = ? WHERE rowid = ?;",
                            (json.dumps(meta), rowid)
                        )
                        stats["ambiguous"] += 1
                        continue
                    else:
                        meta["resolution_status"] = "unresolved"
                        conn.execute(
                            "UPDATE edges SET provenance = 'unresolved', metadata_json = ? WHERE rowid = ?;",
                            (json.dumps(meta), rowid)
                        )
                        stats["unresolved"] += 1
                        continue

                # Resolved unambiguously
                meta["resolution_status"] = "resolved"
                conn.execute(
                    "UPDATE edges SET target_id = ?, provenance = 'resolved', metadata_json = ? WHERE rowid = ?;",
                    (resolved_cand.node_id, json.dumps(meta), rowid)
                )
                stats["resolved"] += 1

                is_test_caller = (
                    caller_path.startswith("tests/")
                    or caller_path.startswith("test_")
                    or "_test.py" in caller_path
                    or src_id.startswith(("func:tests/", "class:tests/"))
                )
                if is_test_caller and resolved_cand.node_type in ("function", "class", "service", "endpoint"):
                    exists = conn.execute(
                        "SELECT 1 FROM edges WHERE source_id = ? AND target_id = ? AND edge_type = 'verifies';",
                        (src_id, resolved_cand.node_id)
                    ).fetchone()
                    if not exists:
                        conn.execute(
                            """
                            INSERT INTO edges (source_id, target_id, edge_type, provenance, metadata_json)
                            VALUES (?, ?, 'verifies', 'test_execution_proof', ?);
                            """,
                            (src_id, resolved_cand.node_id, json.dumps({"verified_target": resolved_cand.name, "caller": src_id}))
                        )

        return stats


def resolve_node_candidates(store: GraphStore, query: str) -> ResolutionResult:
    """Resolve a target query string honestly, exposing ambiguous candidate sets without guessing (DEV-041/043)."""
    clean_q = query.strip()
    if not clean_q:
        return ResolutionResult(status=ResolutionStatus.UNRESOLVED, reason="Empty query")

    # 1. Exact node ID match
    node = store.get_node(clean_q)
    if node:
        cand = ResolutionCandidate(node_id=node["id"], name=node["name"], node_type=node["node_type"], path=node.get("path", ""))
        return ResolutionResult(status=ResolutionStatus.RESOLVED, selected_id=node["id"], candidates=[cand])

    # 2. Prefixed domain entity IDs
    for prefix in ("story:", "task:", "criterion:", "adr:", "file:"):
        prefixed_node = store.get_node(f"{prefix}{clean_q}")
        if prefixed_node:
            cand = ResolutionCandidate(node_id=prefixed_node["id"], name=prefixed_node["name"], node_type=prefixed_node["node_type"], path=prefixed_node.get("path", ""))
            return ResolutionResult(status=ResolutionStatus.RESOLVED, selected_id=prefixed_node["id"], candidates=[cand])

    with store._get_connection() as conn:
        # 3. Path match
        path_rows = conn.execute("SELECT id, name, node_type, path FROM nodes WHERE path = ?;", (clean_q,)).fetchall()
        if len(path_rows) == 1:
            r = path_rows[0]
            cand = ResolutionCandidate(node_id=r[0], name=r[1], node_type=r[2], path=r[3] or "")
            return ResolutionResult(status=ResolutionStatus.RESOLVED, selected_id=r[0], candidates=[cand])

        # 4. Exact name matches (detect ambiguity!)
        name_rows = conn.execute("SELECT id, name, node_type, path FROM nodes WHERE name = ?;", (clean_q,)).fetchall()
        if len(name_rows) == 1:
            r = name_rows[0]
            cand = ResolutionCandidate(node_id=r[0], name=r[1], node_type=r[2], path=r[3] or "")
            return ResolutionResult(status=ResolutionStatus.RESOLVED, selected_id=r[0], candidates=[cand])
        elif len(name_rows) > 1:
            # Multiple symbols share the exact same name! Refuse to guess.
            candidates = [
                ResolutionCandidate(node_id=r[0], name=r[1], node_type=r[2], path=r[3] or "")
                for r in name_rows
            ]
            return ResolutionResult(
                status=ResolutionStatus.AMBIGUOUS,
                selected_id=None,
                candidates=candidates,
                reason=f"Ambiguous query '{clean_q}' matches {len(candidates)} symbols across different scopes"
            )

    # 5. Full-Text Search fallback
    results = store.query_fts(clean_q, limit=5)
    if results:
        exact_fts = [r for r in results if r["name"].lower() == clean_q.lower()]
        if len(exact_fts) == 1:
            r = exact_fts[0]
            cand = ResolutionCandidate(node_id=r["id"], name=r["name"], node_type=r["node_type"], path=r.get("path", ""))
            return ResolutionResult(status=ResolutionStatus.RESOLVED, selected_id=r["id"], candidates=[cand])
        elif len(exact_fts) > 1:
            candidates = [
                ResolutionCandidate(node_id=r["id"], name=r["name"], node_type=r["node_type"], path=r.get("path", ""))
                for r in exact_fts
            ]
            return ResolutionResult(
                status=ResolutionStatus.AMBIGUOUS,
                selected_id=None,
                candidates=candidates,
                reason=f"FTS query '{clean_q}' matches {len(candidates)} candidate symbols"
            )

    return ResolutionResult(status=ResolutionStatus.UNRESOLVED, reason=f"Symbol or node '{clean_q}' not found")
