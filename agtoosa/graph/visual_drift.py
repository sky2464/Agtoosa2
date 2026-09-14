"""Visual-to-Code Architecture Drift Verification Engine (DEV-033).

Mathematically audits visual architecture diagrams (Mermaid, PlantUML, Excalidraw)
against indexed SQLite AST callgraphs and network dependencies, flagging:
1. Ghost Nodes: visual components with no matching code implementation.
2. Path Mismatches: visual arrows asserting relationships absent in the AST.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Set

from agtoosa.graph.store import GraphStore


def _normalize_name(name: str) -> str:
    """Normalize identifier for fuzzy matching across visual and code naming conventions."""
    clean = re.sub(r"[^a-zA-Z0-9]", "", name).lower()
    # Strip common visual suffixes
    for suffix in ["service", "controller", "manager", "component", "module"]:
        if clean.endswith(suffix) and len(clean) > len(suffix):
            clean = clean[:-len(suffix)]
    return clean


class VisualDriftDetector:
    """Detects drift between visual architectural models and concrete code implementations."""

    def __init__(self, store: GraphStore):
        self.store = store

    def detect_drift(self) -> Dict[str, Any]:
        """Audit all visual nodes and edges in the graph against concrete code symbols."""
        all_nodes = self.store.get_all_nodes()
        all_edges = self.store.get_all_edges()

        visual_nodes: List[Dict[str, Any]] = []
        code_nodes: List[Dict[str, Any]] = []

        for n in all_nodes:
            is_vis = n.get("metadata", {}).get("is_visual", False) or n["id"].startswith("visual:")
            if is_vis:
                visual_nodes.append(n)
            elif n["node_type"] in {"class", "function", "service", "endpoint", "topic", "module"}:
                code_nodes.append(n)

        # Build index of code nodes by normalized names
        code_by_norm: Dict[str, List[Dict[str, Any]]] = {}
        for cn in code_nodes:
            norm = _normalize_name(cn["name"])
            code_by_norm.setdefault(norm, []).append(cn)

        ghost_nodes: List[Dict[str, Any]] = []
        visual_to_code_map: Dict[str, str] = {}
        synchronized_components: List[str] = []

        for vn in visual_nodes:
            v_norm = _normalize_name(vn["name"])
            matches = code_by_norm.get(v_norm, [])

            if not matches:
                # Ghost node: diagram component has no code implementation
                ghost_nodes.append({
                    "node_id": vn["id"],
                    "name": vn["name"],
                    "path": vn["path"],
                    "diagram_type": vn.get("metadata", {}).get("diagram_type", "diagram"),
                    "issue": "Diagram component has no matching code implementation in repository AST"
                })
            else:
                matched_code = matches[0]
                visual_to_code_map[vn["id"]] = matched_code["id"]
                synchronized_components.append(f"{vn['name']} -> {matched_code['name']} ({matched_code['path']})")

        # Check visual edges for path mismatches
        path_mismatches: List[Dict[str, Any]] = []

        # Build set of real code edges
        code_edge_pairs: Set[tuple[str, str]] = set()
        for e in all_edges:
            code_edge_pairs.add((e["source_id"], e["target_id"]))

        for e in all_edges:
            is_vis_edge = e.get("metadata", {}).get("is_visual", False) or e["source_id"].startswith("visual:")
            if not is_vis_edge:
                continue

            src_vis = e["source_id"]
            tgt_vis = e["target_id"]

            code_src = visual_to_code_map.get(src_vis)
            code_tgt = visual_to_code_map.get(tgt_vis)

            if code_src and code_tgt:
                # Both components exist in code! Check if connection exists in AST
                if (code_src, code_tgt) not in code_edge_pairs:
                    # Also check neighbors
                    neighbors = [n["id"] for n in self.store.get_neighbors(code_src, direction="out")]
                    if code_tgt not in neighbors:
                        src_name = next((v["name"] for v in visual_nodes if v["id"] == src_vis), src_vis)
                        tgt_name = next((v["name"] for v in visual_nodes if v["id"] == tgt_vis), tgt_vis)
                        path_mismatches.append({
                            "visual_edge": f"{src_name} -> {tgt_name}",
                            "source_code": code_src,
                            "target_code": code_tgt,
                            "issue": f"Visual diagram asserts connection '{src_name}' -> '{tgt_name}', but no matching AST or network relationship exists between {code_src} and {code_tgt}."
                        })

        drift_detected = (len(ghost_nodes) > 0 or len(path_mismatches) > 0)

        return {
            "drift_detected": drift_detected,
            "total_visual_nodes": len(visual_nodes),
            "total_ghost_nodes": len(ghost_nodes),
            "total_path_mismatches": len(path_mismatches),
            "ghost_nodes": ghost_nodes,
            "path_mismatches": path_mismatches,
            "synchronized_components": synchronized_components,
            "verdict": "DRIFT_DETECTED" if drift_detected else "SYNCHRONIZED"
        }
