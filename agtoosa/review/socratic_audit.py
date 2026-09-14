"""Socratic Architecture Audit & 1-Click God-Node Refactoring Blueprints (DEV-036).

Active architectural audit engine that detects:
1. Architectural God nodes (high centrality, disproportionate coupling).
2. Cyclic dependency hotspots with attached 1-click decoupling blueprints.
3. Cross-modality latent couplings (documentation/diagram requirements without test verification).
4. Socratic inquiry prompts for AI coding agents before sprint execution.
5. Automated generation of GRAPH_REPORT.md.
"""

from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.refactor.decoupler import CycleDecouplerEngine, DecouplingReport
from agtoosa.refactor.dead_code import DeadCodePruner


@dataclass
class GodNode:
    """Architectural God node dominating the codebase."""
    node_id: str
    name: str
    node_type: str
    path: str
    in_degree: int
    out_degree: int
    total_degree: int
    category: str  # "AFFERENT_HUB" (SPOF), "EFFERENT_HUB" (High blast radius), "BALANCED_GOD_NODE"
    decoupling_blueprint: Optional[Dict[str, Any]] = None
    socratic_prompt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CrossModalityLatentCoupling:
    """Implicit relationship between documentation/diagram and unverified code."""
    source_id: str
    source_name: str
    source_path: str
    target_code_id: str
    target_code_name: str
    target_code_path: str
    has_test_coverage: bool
    risk_level: str  # "HIGH", "MEDIUM", "LOW"
    socratic_prompt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SocraticAuditEngine:
    """Coordinates deep architectural audit, blueprint generation, and report synthesis."""

    def __init__(self, store: GraphStore, workspace_root: Optional[Path] = None):
        self.store = store
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.decoupler = CycleDecouplerEngine(store, self.workspace_root)
        self.dead_code_pruner = DeadCodePruner(store, self.workspace_root)

    def detect_god_nodes(self, degree_threshold: int = 5) -> List[GodNode]:
        """Detect architectural God nodes based on degree centrality."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        if not nodes:
            return []

        node_map = {n["id"]: n for n in nodes if not n["id"].startswith("visual:")}
        in_degrees = defaultdict(int)
        out_degrees = defaultdict(int)

        for e in edges:
            src = e["source_id"]
            tgt = e["target_id"]
            if src in node_map and tgt in node_map and src != tgt:
                out_degrees[src] += 1
                in_degrees[tgt] += 1

        god_nodes: List[GodNode] = []
        for nid, n in node_map.items():
            ind = in_degrees[nid]
            outd = out_degrees[nid]
            tot = ind + outd

            if tot >= degree_threshold:
                if ind >= 2 * outd and ind >= 4:
                    cat = "AFFERENT_HUB"  # Core bottleneck / Single Point of Failure
                elif outd >= 2 * ind and outd >= 4:
                    cat = "EFFERENT_HUB"  # High Blast Radius / Orchestration Monster
                else:
                    cat = "BALANCED_GOD_NODE"

                prompt = (
                    f"⚠️ Socratic Inquiry for '{n['name']}': "
                    f"This {n.get('node_type', 'symbol')} has {tot} total dependencies ({ind} callers, {outd} dependencies). "
                    f"Why does this component concentrate so much architectural gravity? "
                    f"Can we partition it into smaller single-responsibility interfaces before modifying it?"
                )

                # Generate blueprint stub
                blueprint = {
                    "strategy": "INTERFACE_SEGREGATION",
                    "target_symbol": n["name"],
                    "proposed_interfaces": [f"I{n['name']}Reader", f"I{n['name']}Writer"],
                    "suggested_action": f"Extract abstract protocols to decouple the {ind} incoming callers."
                }

                god_nodes.append(
                    GodNode(
                        node_id=nid,
                        name=n["name"],
                        node_type=n.get("node_type", "unknown"),
                        path=n.get("path", ""),
                        in_degree=ind,
                        out_degree=outd,
                        total_degree=tot,
                        category=cat,
                        decoupling_blueprint=blueprint,
                        socratic_prompt=prompt
                    )
                )

        # Sort by total degree descending
        god_nodes.sort(key=lambda g: g.total_degree, reverse=True)
        return god_nodes

    def audit_cross_modality_couplings(self) -> List[CrossModalityLatentCoupling]:
        """Detect doc/diagram requirements linked to code that lacks test evidence."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        node_map = {n["id"]: n for n in nodes}
        test_verified_targets: Set[str] = set()

        for e in edges:
            if e["edge_type"] in ("verifies", "evidenced_by"):
                test_verified_targets.add(e["target_id"])

        latent_couplings: List[CrossModalityLatentCoupling] = []

        for e in edges:
            src_id = e["source_id"]
            tgt_id = e["target_id"]

            is_doc_src = any(src_id.startswith(p) for p in ("doc:", "visual:", "concept:", "story:", "req:", "adr:"))
            tgt_node = node_map.get(tgt_id)

            if is_doc_src and tgt_node and tgt_node.get("node_type") in ("class", "function", "method"):
                has_test = tgt_id in test_verified_targets
                risk = "LOW" if has_test else "HIGH"

                src_node = node_map.get(src_id, {})
                prompt = (
                    f"⚠️ Socratic Inquiry: Requirement '{src_node.get('name', src_id)}' "
                    f"claims dependency on code '{tgt_node['name']}', but this code symbol has NO automated test evidence. "
                    f"How can this specification be marked completed without proof-graph validation?"
                )

                latent_couplings.append(
                    CrossModalityLatentCoupling(
                        source_id=src_id,
                        source_name=src_node.get("name", src_id),
                        source_path=src_node.get("path", ""),
                        target_code_id=tgt_id,
                        target_code_name=tgt_node["name"],
                        target_code_path=tgt_node.get("path", ""),
                        has_test_coverage=has_test,
                        risk_level=risk,
                        socratic_prompt=prompt
                    )
                )

        return latent_couplings

    def run_full_audit(self, generate_blueprints: bool = True) -> Dict[str, Any]:
        """Execute comprehensive architectural audit."""
        god_nodes = self.detect_god_nodes()
        latent_couplings = self.audit_cross_modality_couplings()
        cycles_report = self.decoupler.analyze_cycles()

        # Dead code review
        dead_report = self.dead_code_pruner.analyze(min_confidence="low")
        dead_symbols = dead_report.zombies

        total_alarms = (
            len(god_nodes)
            + len([c for c in latent_couplings if c.risk_level == "HIGH"])
            + cycles_report.total_cycles_detected
        )

        return {
            "total_alarms": total_alarms,
            "god_nodes": [g.to_dict() for g in god_nodes],
            "cyclic_hotspots": cycles_report.to_dict(),
            "cross_modality_couplings": [c.to_dict() for c in latent_couplings],
            "dead_code_candidates": [s.to_dict() for s in dead_symbols[:10]]
        }

    def generate_markdown_report(self, audit_data: Dict[str, Any]) -> str:
        """Render Socratic architecture audit as GRAPH_REPORT.md."""
        lines = [
            "# 🏛️ Socratic Architecture Audit Report (`GRAPH_REPORT.md`)",
            "\n*Generated by Agtoosa2 (DEV-036) — Autonomous Architecture Engine*\n",
            f"**Total Architectural Alarms:** `{audit_data['total_alarms']}`\n",
            "---",
            "## 1. Architectural God Nodes & Concentration Risks\n",
            "God nodes accumulate excessive structural gravity, becoming single points of failure or high-blast-radius choke points.\n"
        ]

        if not audit_data["god_nodes"]:
            lines.append("✅ **Clean Architecture**: No disproportionate God nodes detected.\n")
        else:
            lines.extend([
                "| Symbol | Type | Path | In-Degree | Out-Degree | Total | Gravity Classification |",
                "|---|---|---|:---:|:---:|:---:|---|"
            ])
            for g in audit_data["god_nodes"]:
                lines.append(
                    f"| `{g['name']}` | {g['node_type']} | `{g['path']}` | {g['in_degree']} | {g['out_degree']} | {g['total_degree']} | **{g['category']}** |"
                )

            lines.append("\n### 💡 Socratic Coding Agent Inquiries & Refactoring Blueprints\n")
            for g in audit_data["god_nodes"][:5]:
                lines.append(f"> **{g['name']}** (`{g['category']}`)")
                lines.append(f"> {g['socratic_prompt']}\n")
                if g.get("decoupling_blueprint"):
                    bp = g["decoupling_blueprint"]
                    lines.append(f"```json\n{json.dumps(bp, indent=2)}\n```\n")

        lines.extend([
            "---",
            "## 2. Cyclic Dependency Hotspots & Decoupling Blueprints\n"
        ])

        cycles = audit_data["cyclic_hotspots"]
        if cycles["total_cycles_detected"] == 0:
            lines.append("✅ **Acyclic Directed Graph**: No dependency cycles found.\n")
        else:
            lines.append(f"⚠️ **Detected `{cycles['total_cycles_detected']}` cyclic loops.** Structural refactoring required.\n")
            for idx, st in enumerate(cycles["strategies"], start=1):
                lines.append(f"### Cycle {idx}: `{st['strategy_type']}`")
                lines.append(f"- **Cycle Path:** `{' -> '.join(st['cycle'])}`")
                lines.append(f"- **Cut Edge:** `{st['cut_edge'][0]}` ➔ `{st['cut_edge'][1]}`")
                lines.append(f"- **Rationale:** {st['rationale']}")
                lines.append("\n**Proposed Interface Stub:**")
                lines.append(f"```python\n{st['generated_code_stub']}\n```\n")

        lines.extend([
            "---",
            "## 3. Cross-Modality Latent Couplings (Docs vs Code Verification)\n"
        ])

        couplings = audit_data["cross_modality_couplings"]
        high_risk = [c for c in couplings if c["risk_level"] == "HIGH"]
        if not high_risk:
            lines.append("✅ **Synchronized Verification**: All documentation references are grounded with automated test evidence.\n")
        else:
            lines.extend([
                "| Requirement / Document | Referenced Code Symbol | Test Evidence | Risk Level |",
                "|---|---|:---:|:---:|"
            ])
            for c in high_risk[:10]:
                lines.append(f"| `{c['source_name']}` | `{c['target_code_name']}` | ❌ None | **HIGH** |")

            lines.append("\n### ⚠️ Socratic Questions on Unverified Specifications\n")
            for c in high_risk[:3]:
                lines.append(f"- {c['socratic_prompt']}")

        lines.append("\n---\n*Report generated automatically. Run `agtoosa refactor decouple` or `agtoosa refactor dead-code` to execute healing blueprints.*")
        return "\n".join(lines)

    def write_report(
        self,
        output_path: Optional[Path] = None,
        format: str = "markdown",
        generate_blueprints: bool = True
    ) -> Dict[str, Any]:
        """Generate and write audit report to disk."""
        target_path = output_path or (self.workspace_root / "GRAPH_REPORT.md")
        data = self.run_full_audit(generate_blueprints=generate_blueprints)

        if format == "json":
            target_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        else:
            md_content = self.generate_markdown_report(data)
            target_path.write_text(md_content, encoding="utf-8")

        return {
            "output_path": str(target_path),
            "format": format,
            "total_alarms": data["total_alarms"],
            "data": data
        }
