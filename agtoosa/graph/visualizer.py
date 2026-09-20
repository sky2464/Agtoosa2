"""Interactive standalone architecture exploration visualizer — Agtoosa Studio C4 Command Center."""

from collections import defaultdict
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import webbrowser

from agtoosa.graph.store import GraphStore
from agtoosa.graph.metrics import MetricsEngine


class VisualizerEngine:
    """Generates self-contained, offline interactive HTML C4 architecture command center."""

    NODE_COLORS = {
        "file": "#64748b",
        "module": "#475569",
        "class": "#0284c7",
        "function": "#38bdf8",
        "variable": "#94a3b8",
        "import": "#cbd5e1",
        "story": "#a855f7",
        "epic": "#7c3aed",
        "criterion": "#c084fc",
        "task": "#e879f9",
        "test": "#10b981",
        "evidence": "#34d399",
        "adr": "#f59e0b",
        "doc": "#fbbf24",
        "concept": "#fb923c",
        "service": "#3b82f6",
        "endpoint": "#06b6d4",
        "topic": "#ec4899",
        "table": "#8b5cf6"
    }

    DOMAIN_CONFIG = {
        "Distributed Services & Runtimes": {
            "tier": "Tier 1: Entrypoints & Dispatch",
            "tier_num": 1,
            "color": "#3b82f6",
            "icon": "🌐",
            "cx": -300,
            "cy": -380,
            "desc": "Distributed microservices, external RPC/HTTP runtimes, and client ingress."
        },
        "CLI Layer": {
            "tier": "Tier 1: Entrypoints & Dispatch",
            "tier_num": 1,
            "color": "#38bdf8",
            "icon": "⚡",
            "cx": -460,
            "cy": -240,
            "desc": "Unified command dispatcher, CLI flags, terminal UX, and process launchers."
        },
        "Native MCP Protocol": {
            "tier": "Tier 1: Entrypoints & Dispatch",
            "tier_num": 1,
            "color": "#818cf8",
            "icon": "🔌",
            "cx": 460,
            "cy": -240,
            "desc": "Model Context Protocol JSON-RPC 2.0 stdio server for AI coding agents."
        },
        "Core Engine": {
            "tier": "Tier 2: Processing & Analysis",
            "tier_num": 2,
            "color": "#6366f1",
            "icon": "⚙️",
            "cx": 0,
            "cy": -240,
            "desc": "Lifecycle state machine, domain models, and bounded context compiler."
        },
        "AST Parser Subsystem": {
            "tier": "Tier 2: Processing & Analysis",
            "tier_num": 2,
            "color": "#06b6d4",
            "icon": "🌳",
            "cx": -460,
            "cy": 60,
            "desc": "Polyglot AST extractors (Python, JS/TS, Shell) and workspace scanner."
        },
        "Specifications & Delivery": {
            "tier": "Tier 2: Processing & Analysis",
            "tier_num": 2,
            "color": "#c084fc",
            "icon": "📋",
            "cx": 460,
            "cy": 60,
            "desc": "User stories (DEV-001..005), acceptance criteria, and traceable tasks."
        },
        "Knowledge Graph & Storage": {
            "tier": "Tier 3: Persistence & Verification",
            "tier_num": 3,
            "color": "#0ea5e9",
            "icon": "🧠",
            "cx": 0,
            "cy": 60,
            "desc": "Transactional SQLite store, FTS5 full-text indexing, and graph metrics engine."
        },
        "Verification & Quality": {
            "tier": "Tier 3: Persistence & Verification",
            "tier_num": 3,
            "color": "#10b981",
            "icon": "🛡️",
            "cx": -260,
            "cy": 340,
            "desc": "Unit and integration test suites, proof verification gates, and evidence."
        },
        "Decisions & Architecture": {
            "tier": "Tier 3: Persistence & Verification",
            "tier_num": 3,
            "color": "#f59e0b",
            "icon": "📐",
            "cx": 260,
            "cy": 340,
            "desc": "Master Plan, Master Architecture, ADRs, and capability matrices."
        }
    }

    def __init__(self, store: GraphStore, workspace_root: Optional[Path] = None):
        self.store = store
        self.workspace_root = workspace_root
        self.web_dir = Path(__file__).resolve().parent / "web"

    def _assign_domain(self, node: Dict[str, Any]) -> str:
        path = (node.get("path") or "").lower()
        ntype = (node.get("node_type") or "").lower()

        if ntype in ("story", "epic", "criterion", "task"):
            return "Specifications & Delivery"
        if ntype in ("service",) or path.startswith("runtime://"):
            return "Distributed Services & Runtimes"
        if ntype in ("test", "evidence") or "test" in path:
            return "Verification & Quality"
        if ntype in ("adr", "doc", "concept") or path.startswith("docs"):
            return "Decisions & Architecture"
        if "/cli" in path or path.startswith("cli/") or "bin/" in path:
            return "CLI Layer"
        if "/parser" in path or path.startswith("parser/"):
            return "AST Parser Subsystem"
        if "/graph" in path or path.startswith("graph/") or "storage" in path:
            return "Knowledge Graph & Storage"
        if "/mcp" in path or path.startswith("mcp/"):
            return "Native MCP Protocol"
        if "/core" in path or path.startswith("core/") or "engine" in path:
            return "Core Engine"
        return "Core Engine"

    def extract_graph_data(self, filter_type: Optional[str] = None) -> Dict[str, Any]:
        """Extract and structure all architectural graph datasets, metrics, hubs, and blueprints."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        if filter_type:
            ft = filter_type.lower()
            valid_node_ids = {n["id"] for n in nodes if n["node_type"].lower() == ft}
            nodes = [n for n in nodes if n["id"] in valid_node_ids]
            edges = [e for e in edges if e["source_id"] in valid_node_ids and e["target_id"] in valid_node_ids]

        stats = self.store.get_stats().to_dict()

        # Compute architecture metrics & hubs
        metrics_engine = MetricsEngine(self.store)
        metrics_report = metrics_engine.compute_all()
        health_scorecard = metrics_report["health_scorecard"]
        top_hubs = {h["id"]: h for h in metrics_report["top_hubs"]}
        cycles = metrics_report["cycles"]

        # Domain breakdown
        domain_counts: Dict[str, int] = defaultdict(int)
        domain_nodes_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        node_domain_map: Dict[str, str] = {}

        for n in nodes:
            d = self._assign_domain(n)
            domain_counts[d] += 1
            domain_nodes_map[d].append(n)
            node_domain_map[n["id"]] = d

        # Cross-domain conduit edge aggregates
        conduit_counts: Dict[str, int] = defaultdict(int)
        domain_inbound: Dict[str, int] = defaultdict(int)
        domain_outbound: Dict[str, int] = defaultdict(int)

        for e in edges:
            src_dom = node_domain_map.get(e["source_id"])
            tgt_dom = node_domain_map.get(e["target_id"])
            if src_dom and tgt_dom and src_dom != tgt_dom:
                pair_key = f"{src_dom}➔{tgt_dom}"
                conduit_counts[pair_key] += 1
                domain_outbound[src_dom] += 1
                domain_inbound[tgt_dom] += 1

        conduits = [
            {
                "source": k.split("➔")[0],
                "target": k.split("➔")[1],
                "count": count
            }
            for k, count in conduit_counts.items()
        ]

        # Detailed subsystem container profiles
        subsystems_data = {}
        for dom_name, conf in self.DOMAIN_CONFIG.items():
            d_nodes = domain_nodes_map.get(dom_name, [])
            files_count = len({n["path"] for n in d_nodes if n.get("path")})
            classes = [n for n in d_nodes if n["node_type"] == "class"]
            functions = [n for n in d_nodes if n["node_type"] == "function"]
            specs = [n for n in d_nodes if n["node_type"] in ("story", "epic", "criterion", "task")]
            tests = [n for n in d_nodes if n["node_type"] in ("test", "evidence")]

            # Top exports (highest hub score or classes)
            key_exports = sorted(
                classes + functions,
                key=lambda x: top_hubs.get(x["id"], {}).get("score", 0.0),
                reverse=True
            )[:8]

            subsystems_data[dom_name] = {
                "name": dom_name,
                "tier": conf["tier"],
                "tier_num": conf["tier_num"],
                "color": conf["color"],
                "icon": conf["icon"],
                "desc": conf["desc"],
                "total_entities": len(d_nodes),
                "files_count": files_count,
                "classes_count": len(classes),
                "functions_count": len(functions),
                "specs_count": len(specs),
                "tests_count": len(tests),
                "inbound_count": domain_inbound[dom_name],
                "outbound_count": domain_outbound[dom_name],
                "key_exports": [
                    {
                        "id": x["id"],
                        "name": x["name"],
                        "type": x["node_type"],
                        "path": x["path"],
                        "color": self.NODE_COLORS.get(x["node_type"], "#38bdf8")
                    }
                    for x in key_exports
                ]
            }

        # Story delivery proofs
        stories = [n for n in nodes if n["node_type"] == "story"]
        story_cards = []
        for s in stories:
            s_id = s["id"]
            linked_crits = [e["target_id"] for e in edges if e["source_id"] == s_id and "criterion" in e["target_id"]]
            linked_tasks = [e["target_id"] for e in edges if e["source_id"] == s_id and "task" in e["target_id"]]
            story_cards.append({
                "id": s["id"],
                "name": s["name"],
                "criteria_count": len(linked_crits),
                "tasks_count": len(linked_tasks),
                "path": s["path"]
            })

        elements_data = {
            "nodes": [
                {
                    "data": {
                        "id": n["id"],
                        "name": n["name"],
                        "type": n["node_type"],
                        "domain": self._assign_domain(n),
                        "path": n["path"],
                        "start_line": n.get("start_line"),
                        "end_line": n.get("end_line"),
                        "docstring": n.get("docstring") or "",
                        "color": self.NODE_COLORS.get(n["node_type"], "#38bdf8"),
                        "is_hub": n["id"] in top_hubs,
                        "hub_score": top_hubs[n["id"]]["score"] if n["id"] in top_hubs else 0.0,
                        "metadata": n.get("metadata", {})
                    }
                }
                for n in nodes
            ],
            "edges": [
                {
                    "data": {
                        "id": f"e_{idx}",
                        "source": e["source_id"],
                        "target": e["target_id"],
                        "type": e["edge_type"],
                        "provenance": e.get("provenance", "extracted")
                    }
                }
                for idx, e in enumerate(edges, start=1)
            ]
        }

        if filter_type and filter_type.lower() != "story":
            story_cards = []

        hubs_list = [h for h in metrics_report["top_hubs"] if not filter_type or h.get("type", "").lower() == filter_type.lower()]

        # Stage 18: Telemetry Data
        telemetry_data = self.store.get_all_telemetry()

        # Stage 19: Cycle Decoupling Strategies
        try:
            from agtoosa.refactor.decoupler import CycleDecouplerEngine
            decoupler_engine = CycleDecouplerEngine(self.store)
            decoupler_data = decoupler_engine.analyze_cycles().to_dict()
        except Exception:
            decoupler_data = {"total_cycles_detected": 0, "strategies": []}

        # Stage 20: Dead Code & Zombie Symbol Pruning
        try:
            from agtoosa.refactor.dead_code import DeadCodePruner
            dead_code_pruner = DeadCodePruner(self.store)
            dead_code_data = dead_code_pruner.analyze().to_dict()
            if filter_type:
                dead_code_data["zombies"] = [
                    z for z in dead_code_data.get("zombies", [])
                    if z.get("node_type", "").lower() == filter_type.lower()
                ]
                dead_code_data["total_dead_candidates"] = len(dead_code_data["zombies"])
        except Exception:
            dead_code_data = {
                "total_symbols_analyzed": len(nodes),
                "total_dead_candidates": 0,
                "total_estimated_dead_lines": 0,
                "confidence_breakdown": {},
                "zombies": []
            }

        # Workspace Context & Early-Stage (Genesis) Detection (DEV-058)
        workspace_root = self.workspace_root or getattr(self.store, "workspace_root", None) or Path.cwd()
        workspace_name = workspace_root.name

        code_node_types = {"function", "class", "module", "variable", "interface", "method", "enum", "type"}
        code_nodes = [n for n in nodes if (n.get("node_type") or "").lower() in code_node_types]
        doc_node_types = {"doc", "adr", "concept", "story", "epic", "criterion", "task"}
        doc_nodes = [n for n in nodes if (n.get("node_type") or "").lower() in doc_node_types]

        code_files = {n.get("path") for n in code_nodes if n.get("path")}
        doc_files = {n.get("path") for n in doc_nodes if n.get("path")}

        is_genesis = (len(nodes) < 15 or len(code_nodes) == 0)

        # AI Agent Enforcement Status (AGENTS.md, CLAUDE.md, etc.)
        try:
            from agtoosa.core.agent_rules import AgentWorkflowEnforcer
            enforcer = AgentWorkflowEnforcer(workspace_root)
            agent_rules_installed = enforcer.is_enforced()
        except Exception:
            agent_rules_installed = False

        # Synthesize Plain-English Findings & Next Steps
        plain_english_findings = []
        if is_genesis:
            doc_count = len(doc_files) or len(doc_nodes)
            plain_english_findings.append({
                "id": "genesis_stage",
                "severity": "info",
                "icon": "🌱",
                "title": "Project Inception Stage",
                "description": f"Found {doc_count} design document(s) and 0 code files in '{workspace_name}'. Agtoosa is ready to monitor symbols as you start building.",
                "action_label": "Create Code File",
                "action_hint": "Create your first .py, .ts, or .js file and run 'agtoosa graph build'.",
                "action_command": "touch main.py && agtoosa graph build"
            })
        else:
            plain_english_findings.append({
                "id": "codebase_active",
                "severity": "success",
                "icon": "🏛️",
                "title": "Architecture Monitored",
                "description": f"Agtoosa is tracking {len(nodes)} symbols across {len(code_files)} code file(s) with continuous drift alarms.",
                "action_label": "Verify Architecture",
                "action_hint": "Run 'agtoosa review' to verify layer boundaries and zero cycles.",
                "action_command": "agtoosa review"
            })

        if not agent_rules_installed:
            plain_english_findings.append({
                "id": "agent_governance",
                "severity": "warning",
                "icon": "🤖",
                "title": "AI Agent Rules Not Enforced",
                "description": "AI coding agents (Cursor, Claude, Copilot, Antigravity) are not instructed yet on Agtoosa guardrails.",
                "action_label": "Enforce on AI Agents",
                "action_hint": "Click to generate AGENTS.md & CLAUDE.md with zero-drift instructions.",
                "action_command": "agtoosa agent-init",
                "action_endpoint": "/api/agent/enforce"
            })
        else:
            plain_english_findings.append({
                "id": "agent_governance_active",
                "severity": "success",
                "icon": "🛡️",
                "title": "AI Agent Governance Active",
                "description": "AGENTS.md and CLAUDE.md are actively guarding against unreviewed architectural drift.",
                "action_label": "View Guidelines",
                "action_hint": "Inspect AGENTS.md in your repository root.",
                "action_command": "cat AGENTS.md"
            })

        if cycles:
            plain_english_findings.append({
                "id": "cycles_detected",
                "severity": "danger",
                "icon": "🔄",
                "title": f"{len(cycles)} Circular Dependency Loop(s)",
                "description": "Modules mutually depend on each other, preventing clean decoupling and bloating AI context.",
                "action_label": "Decouple Cycles",
                "action_hint": "Run 'agtoosa refactor decouple' to resolve cycles automatically.",
                "action_command": "agtoosa refactor decouple"
            })
        else:
            plain_english_findings.append({
                "id": "cycles_clean",
                "severity": "success",
                "icon": "✅",
                "title": "Strict DAG (0 Cycles)",
                "description": "Clean dependency architecture with zero circular import loops detected.",
                "action_label": "Verify Layers",
                "action_hint": "Run 'agtoosa review' to verify layer compliance.",
                "action_command": "agtoosa review"
            })

        if dead_code_data.get("total_dead_candidates", 0) > 0:
            cnt = dead_code_data["total_dead_candidates"]
            plain_english_findings.append({
                "id": "dead_code_tokens",
                "severity": "warning",
                "icon": "🧟",
                "title": f"{cnt} Unused Symbol(s) Detected",
                "description": f"Found {cnt} unreferenced symbols wasting AI agent context window tokens.",
                "action_label": "Prune Dead Code",
                "action_hint": "Run 'agtoosa refactor dead-code' to review candidates safely.",
                "action_command": "agtoosa refactor dead-code"
            })

        return {
            "graphData": elements_data,
            "graphStats": stats,
            "healthData": health_scorecard,
            "domainConfig": self.DOMAIN_CONFIG,
            "domainCounts": dict(domain_counts),
            "cycleData": cycles,
            "conduitData": conduits,
            "storyData": story_cards,
            "topHubsData": hubs_list,
            "subsystemsData": subsystems_data,
            "telemetryData": telemetry_data,
            "decouplerData": decoupler_data,
            "deadCodeData": dead_code_data,
            "spectralData": metrics_report.get("spectral", {}),
            "curvatureData": metrics_report.get("curvature", {}),
            "workspaceMetadata": {
                "workspaceName": workspace_name,
                "isGenesis": is_genesis,
                "codeFileCount": len(code_files),
                "docFileCount": len(doc_files) or len(doc_nodes),
                "totalNodeCount": len(nodes),
                "totalEdgeCount": len(edges),
                "agentRulesInstalled": agent_rules_installed,
                "storyCount": len(story_cards),
                "subsystemCount": len(subsystems_data)
            },
            "plainEnglishFindings": plain_english_findings
        }

    def generate_html(self, filter_type: Optional[str] = None) -> str:
        """Generate self-contained, offline interactive HTML document bundling modular assets."""
        data = self.extract_graph_data(filter_type=filter_type)

        def _safe_json(d: Any) -> str:
            raw = json.dumps(d, indent=None)
            return raw.replace("</", "<\\/")

        # Read template HTML
        index_file = self.web_dir / "index.html"
        if not index_file.exists():
            return f"""<!DOCTYPE html>
<html>
<head><title>Agtoosa Studio</title></head>
<body style="font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#f8fafc;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
  <div style="text-align:center;padding:2rem;background:#1e293b;border-radius:12px;border:1px solid #334155;max-width:540px;">
    <h2 style="margin-top:0;color:#38bdf8;">🏛️ Agtoosa Studio</h2>
    <p>Studio web assets were not found at <code>{self.web_dir}</code>.</p>
    <p style="color:#94a3b8;font-size:0.9rem;">Please run <code>agtoosa update</code> to update your installation.</p>
  </div>
</body>
</html>"""

        index_html = index_file.read_text(encoding="utf-8")

        # Bundle CSS
        css_files = ["theme.css", "layout.css", "views.css"]
        css_bundle = "\n".join([
            (self.web_dir / "css" / f).read_text(encoding="utf-8")
            for f in css_files
        ])

        # Bundle JavaScript
        js_files = [
            "state.js", "c4_view.js", "network_view.js", "blast_view.js",
            "radar_view.js", "delivery_view.js", "drawer.js", "app.js"
        ]
        injected_data_script = f"    window.GRAPH_DATA = {_safe_json(data)};"
        js_bundle = "\n".join(
            [injected_data_script] +
            [(self.web_dir / "js" / f).read_text(encoding="utf-8") for f in js_files]
        )

        # Strip link and external script tags
        html = re.sub(r"\s*<link rel=\"stylesheet\" href=\"[^\"]+\">", "", index_html)
        html = re.sub(r"\s*<script src=\"[^\"]+\"></script>", "", html)

        # Inline bundled CSS & JS
        html = html.replace("</head>", f"  <style>\n{css_bundle}\n  </style>\n</head>")
        html = html.replace("</body>", f"  <script>\n{js_bundle}\n  </script>\n</body>")

        return html

    def save_html(self, output_path: Path, filter_type: Optional[str] = None, open_browser: bool = False) -> Path:
        """Write visualizer HTML to output_path and optionally open in default browser."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html_content = self.generate_html(filter_type=filter_type)
        output_path.write_text(html_content, encoding="utf-8")

        if open_browser:
            try:
                webbrowser.open(output_path.as_uri())
            except Exception:
                pass

        return output_path
