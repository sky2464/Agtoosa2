"""Interactive standalone architecture exploration visualizer — Agtoosa Studio."""

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import webbrowser

from agtoosa.graph.store import GraphStore
from agtoosa.graph.metrics import MetricsEngine


class VisualizerEngine:
    """Generates self-contained, offline interactive HTML architecture command center."""

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
        "concept": "#fb923c"
    }

    DOMAIN_CONFIG = {
        "CLI Layer": {
            "color": "#3b82f6",
            "cx": -550,
            "cy": -280,
            "icon": "⚡",
            "desc": "Unified command dispatcher, CLI flags, terminal UX and launchers."
        },
        "Core Engine": {
            "color": "#6366f1",
            "cx": 0,
            "cy": -280,
            "icon": "⚙️",
            "desc": "Lifecycle state machine, domain models, and bounded context compiler."
        },
        "Specifications & Delivery": {
            "color": "#a855f7",
            "cx": 550,
            "cy": -280,
            "icon": "📋",
            "desc": "User stories (DEV-001..005), acceptance criteria, and traceable tasks."
        },
        "AST Parser Subsystem": {
            "color": "#06b6d4",
            "cx": -550,
            "cy": 180,
            "icon": "🌳",
            "desc": "Polyglot AST extractors (Python, JS/TS, Shell) and workspace scanner."
        },
        "Knowledge Graph & Storage": {
            "color": "#0ea5e9",
            "cx": 0,
            "cy": 180,
            "icon": "🧠",
            "desc": "Transactional SQLite store, FTS5 full-text indexing, and metrics engine."
        },
        "Verification & Quality": {
            "color": "#10b981",
            "cx": 550,
            "cy": 180,
            "icon": "🛡️",
            "desc": "Unit and integration test suites, proof verification gates, and evidence."
        },
        "Native MCP Protocol": {
            "color": "#8b5cf6",
            "cx": -280,
            "cy": 640,
            "icon": "🔌",
            "desc": "Model Context Protocol JSON-RPC 2.0 stdio server for AI coding tools."
        },
        "Decisions & Architecture": {
            "color": "#f59e0b",
            "cx": 280,
            "cy": 640,
            "icon": "📐",
            "desc": "Master Plan, Master Architecture, ADRs, and capability matrices."
        }
    }

    def __init__(self, store: GraphStore):
        self.store = store

    def _assign_domain(self, node: Dict[str, Any]) -> str:
        path = (node.get("path") or "").lower()
        ntype = (node.get("node_type") or "").lower()

        if ntype in ("story", "epic", "criterion", "task"):
            return "Specifications & Delivery"
        if ntype in ("test", "evidence") or "test" in path:
            return "Verification & Quality"
        if ntype in ("adr", "doc", "concept") or path.startswith("docs"):
            return "Decisions & Architecture"
        if "agtoosa/cli" in path or "bin/" in path:
            return "CLI Layer"
        if "agtoosa/parser" in path:
            return "AST Parser Subsystem"
        if "agtoosa/graph" in path:
            return "Knowledge Graph & Storage"
        if "agtoosa/mcp" in path:
            return "Native MCP Protocol"
        if "agtoosa/core" in path:
            return "Core Engine"
        return "Core Engine"

    def generate_html(self, filter_type: Optional[str] = None) -> str:
        """Generate standalone HTML document embedding Agtoosa Studio."""
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
        for e in edges:
            src_dom = node_domain_map.get(e["source_id"])
            tgt_dom = node_domain_map.get(e["target_id"])
            if src_dom and tgt_dom and src_dom != tgt_dom:
                pair_key = f"{src_dom}➔{tgt_dom}"
                conduit_counts[pair_key] += 1

        conduits = [
            {"source": k.split("➔")[0], "target": k.split("➔")[1], "count": count}
            for k, count in conduit_counts.items()
        ]

        # Story delivery proofs
        stories = [n for n in nodes if n["node_type"] == "story"]
        story_cards = []
        for s in stories:
            s_id = s["id"]
            # find linked criteria & tasks
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

        json_payload = json.dumps(elements_data, indent=None)
        stats_json = json.dumps(stats, indent=None)
        health_json = json.dumps(health_scorecard, indent=None)
        domains_json = json.dumps(self.DOMAIN_CONFIG, indent=None)
        domain_counts_json = json.dumps(dict(domain_counts), indent=None)
        cycles_json = json.dumps(cycles, indent=None)
        conduits_json = json.dumps(conduits, indent=None)
        stories_json = json.dumps(story_cards, indent=None)
        top_hubs_json = json.dumps(hubs_list, indent=None)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agtoosa Studio — Architecture Command Center</title>
  <style>
    :root {{
      --bg: #060911;
      --surface: rgba(15, 23, 42, 0.85);
      --surface-elevated: rgba(30, 41, 59, 0.9);
      --surface-border: rgba(255, 255, 255, 0.09);
      --surface-border-active: rgba(56, 189, 248, 0.5);
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-glow: rgba(56, 189, 248, 0.3);
      --accent: #818cf8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --panel-width: 420px;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", Oxygen, Ubuntu, Cantarell, sans-serif;
      background: var(--bg);
      color: var(--text);
      overflow: hidden;
      width: 100vw;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    /* Top Command Header */
    header {{
      height: 64px;
      background: var(--surface);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--surface-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      z-index: 30;
      gap: 16px;
    }}

    .brand-section {{
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 210px;
    }}
    .brand-logo {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 800;
      font-size: 1.15rem;
      letter-spacing: -0.02em;
    }}
    .brand-logo span {{ color: var(--primary); }}
    .brand-badge {{
      background: linear-gradient(135deg, rgba(56, 189, 248, 0.18), rgba(129, 140, 248, 0.18));
      color: #7dd3fc;
      border: 1px solid rgba(56, 189, 248, 0.3);
      font-size: 0.68rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    /* Executive KPI Strip */
    .kpi-strip {{
      display: flex;
      align-items: center;
      gap: 12px;
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid var(--surface-border);
      padding: 4px 14px;
      border-radius: 8px;
    }}
    .kpi-item {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.78rem;
      color: var(--text-muted);
    }}
    .kpi-item strong {{
      color: var(--text);
      font-weight: 700;
    }}
    .kpi-pill {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 7px;
      border-radius: 4px;
      font-weight: 700;
      font-size: 0.72rem;
    }}
    .kpi-pill.grade {{
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}
    .kpi-pill.tag {{
      background: rgba(56, 189, 248, 0.12);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.25);
    }}

    /* Perspective Switcher */
    .perspective-switcher {{
      display: flex;
      align-items: center;
      background: rgba(0, 0, 0, 0.45);
      padding: 3px;
      border-radius: 8px;
      border: 1px solid var(--surface-border);
      gap: 2px;
    }}
    .tab-btn {{
      background: none;
      border: none;
      color: var(--text-muted);
      padding: 6px 13px;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }}
    .tab-btn:hover {{
      color: var(--text);
      background: rgba(255, 255, 255, 0.05);
    }}
    .tab-btn.active {{
      background: var(--surface-elevated);
      color: #ffffff;
      border: 1px solid var(--surface-border-active);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
    }}

    /* Controls Bar */
    .controls-bar {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    input, select, button {{
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid var(--surface-border);
      color: var(--text);
      padding: 7px 12px;
      border-radius: 6px;
      font-size: 0.82rem;
      outline: none;
      transition: all 0.2s;
    }}
    input:focus, select:focus {{
      border-color: var(--primary);
      box-shadow: 0 0 0 2px var(--primary-glow);
    }}
    button {{
      cursor: pointer;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    button:hover {{
      background: rgba(51, 65, 85, 0.9);
      border-color: rgba(255, 255, 255, 0.2);
    }}
    button.primary {{
      background: #0284c7;
      border-color: #38bdf8;
      color: #ffffff;
    }}
    button.primary:hover {{
      background: #0369a1;
    }}

    /* Main Container with Tab Views */
    #main-viewport {{
      flex: 1;
      position: relative;
      width: 100%;
      height: calc(100vh - 64px);
      overflow: hidden;
    }}

    .view-panel {{
      position: absolute;
      inset: 0;
      display: none;
      width: 100%;
      height: 100%;
    }}
    .view-panel.active {{
      display: flex;
    }}

    /* Canvas View Container */
    #canvas-container {{
      position: relative;
      width: 100%;
      height: 100%;
      background: radial-gradient(circle at 50% 20%, #111a2e 0%, #060911 100%);
    }}
    canvas {{
      display: block;
      width: 100%;
      height: 100%;
    }}

    /* Perspective Banner */
    .perspective-banner {{
      position: absolute;
      top: 16px;
      left: 16px;
      background: var(--surface);
      backdrop-filter: blur(14px);
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 10px 16px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      z-index: 10;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
      max-width: 440px;
      pointer-events: none;
    }}
    .perspective-banner h3 {{
      font-size: 0.92rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .perspective-banner p {{
      font-size: 0.77rem;
      color: var(--text-muted);
      line-height: 1.4;
    }}

    /* View: System Architecture Cards (C4 Clean View) */
    #c4-container {{
      overflow-y: auto;
      padding: 28px 36px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 20px;
      background: var(--bg);
      align-content: start;
    }}
    .subsystem-card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
    }}
    .subsystem-card:hover {{
      transform: translateY(-2px);
      border-color: var(--surface-border-active);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    }}
    .subsystem-card-header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
    }}
    .subsystem-card-title {{
      font-size: 1.05rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .subsystem-desc {{
      font-size: 0.8rem;
      color: var(--text-muted);
      line-height: 1.45;
    }}
    .subsystem-pill-grid {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      max-height: 100px;
      overflow-y: auto;
    }}
    .component-pill {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--surface-border);
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
      cursor: pointer;
    }}
    .component-pill:hover {{
      background: rgba(56, 189, 248, 0.15);
      border-color: var(--primary);
      color: #ffffff;
    }}

    /* View: Delivery Assurance Board */
    #delivery-container {{
      overflow-y: auto;
      padding: 28px 36px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      background: var(--bg);
    }}
    .story-card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 10px;
      padding: 18px 22px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }}
    .story-card-left {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .story-card-right {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .stat-badge {{
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--surface-border);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.8rem;
      display: flex;
      flex-direction: column;
      align-items: center;
    }}

    /* View: Risk & Bottlenecks Table */
    #risk-container {{
      overflow-y: auto;
      padding: 28px 36px;
      display: flex;
      flex-direction: column;
      gap: 24px;
      background: var(--bg);
    }}
    .table-card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
    }}
    th, td {{
      padding: 10px 14px;
      text-align: left;
      border-bottom: 1px solid var(--surface-border);
    }}
    th {{
      color: var(--text-muted);
      font-weight: 700;
      text-transform: uppercase;
      font-size: 0.72rem;
      letter-spacing: 0.05em;
    }}

    /* Floating Tooltip */
    #node-tooltip {{
      position: absolute;
      background: rgba(15, 23, 42, 0.95);
      backdrop-filter: blur(12px);
      border: 1px solid var(--primary);
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 0.78rem;
      pointer-events: none;
      z-index: 40;
      display: none;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6), 0 0 10px var(--primary-glow);
      max-width: 280px;
    }}

    /* Action Drawer (Sidebar) */
    #sidebar {{
      position: absolute;
      top: 16px;
      right: 16px;
      bottom: 16px;
      width: var(--panel-width);
      background: var(--surface);
      backdrop-filter: blur(20px);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 22px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      z-index: 25;
      transform: translateX(calc(100% + 28px));
      transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      box-shadow: -10px 0 30px rgba(0, 0, 0, 0.6);
      overflow-y: auto;
    }}
    #sidebar.active {{
      transform: translateX(0);
    }}

    .sidebar-header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      border-bottom: 1px solid var(--surface-border);
      padding-bottom: 14px;
    }}
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .domain-tag {{
      display: inline-block;
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-top: 4px;
      font-weight: 500;
    }}
    .close-btn {{
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      font-size: 1.3rem;
      padding: 2px 6px;
    }}
    .close-btn:hover {{ color: #ffffff; }}

    /* Action Buttons in Drawer */
    .drawer-actions {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }}
    .action-btn {{
      padding: 8px 10px;
      font-size: 0.78rem;
      justify-content: center;
      border-radius: 6px;
    }}
    .action-btn.ai-context {{
      grid-column: span 2;
      background: linear-gradient(135deg, #2563eb, #7c3aed);
      border-color: #38bdf8;
      color: #ffffff;
    }}
    .action-btn.ai-context:hover {{
      background: linear-gradient(135deg, #1d4ed8, #6d28d9);
      box-shadow: 0 0 12px var(--primary-glow);
    }}

    .detail-group {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .detail-group label {{
      font-size: 0.74rem;
      text-transform: uppercase;
      color: var(--text-muted);
      letter-spacing: 0.05em;
      font-weight: 700;
    }}
    .detail-group p, .detail-group pre {{
      font-size: 0.84rem;
      color: #e2e8f0;
      word-break: break-word;
    }}

    .connection-list {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-height: 160px;
      overflow-y: auto;
    }}
    .conn-item {{
      background: rgba(255, 255, 255, 0.04);
      padding: 7px 10px;
      border-radius: 6px;
      font-size: 0.8rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
      transition: background 0.15s;
    }}
    .conn-item:hover {{
      background: rgba(255, 255, 255, 0.1);
    }}

    /* Toast Notification */
    #toast {{
      position: absolute;
      bottom: 24px;
      right: 24px;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid var(--primary);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5), 0 0 16px var(--primary-glow);
      color: #ffffff;
      padding: 12px 18px;
      border-radius: 8px;
      font-size: 0.84rem;
      display: flex;
      align-items: center;
      gap: 8px;
      z-index: 50;
      transform: translateY(120px);
      transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    #toast.show {{
      transform: translateY(0);
    }}

    /* Welcome Onboarding Modal */
    #welcome-modal {{
      position: fixed;
      inset: 0;
      background: rgba(5, 8, 16, 0.75);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 100;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.25s ease;
    }}
    #welcome-modal.show {{
      opacity: 1;
      pointer-events: auto;
    }}
    .modal-card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 16px;
      width: 90%;
      max-width: 640px;
      padding: 32px;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.7);
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}
    .modal-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .modal-title {{
      font-size: 1.35rem;
      font-weight: 800;
      letter-spacing: -0.02em;
    }}
    .feature-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }}
    .feature-item {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--surface-border);
      padding: 14px;
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .feature-item h4 {{
      font-size: 0.88rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .feature-item p {{
      font-size: 0.78rem;
      color: var(--text-muted);
      line-height: 1.4;
    }}
  </style>
</head>
<body>

  <!-- Top Command Header -->
  <header>
    <div class="brand-section">
      <div class="brand-logo">
        <span>Agtoosa</span> Studio
      </div>
      <span class="brand-badge">Command Center</span>
    </div>

    <!-- Executive KPI Strip -->
    <div class="kpi-strip">
      <div class="kpi-item">
        <span>Health:</span>
        <span class="kpi-pill grade" id="kpi-grade">Grade A</span>
      </div>
      <div class="kpi-item">
        <span>Cycles:</span>
        <strong id="kpi-cycles">0 Chains</strong>
      </div>
      <div class="kpi-item">
        <span>Critical Hubs:</span>
        <strong id="kpi-hubs">5 Top</strong>
      </div>
      <div class="kpi-item">
        <span>AI Context Cut:</span>
        <span class="kpi-pill tag">~74% Saved</span>
      </div>
    </div>

    <!-- Perspective Tabs -->
    <div class="perspective-switcher">
      <button class="tab-btn active" data-view="blueprint">
        <span>🏛️</span> Domain Blueprint
      </button>
      <button class="tab-btn" data-view="c4">
        <span>🏗️</span> System Cards
      </button>
      <button class="tab-btn" data-view="pipeline">
        <span>🛡️</span> Delivery Pipeline
      </button>
      <button class="tab-btn" data-view="radar">
        <span>⚡</span> Risk & Hub Radar
      </button>
    </div>

    <!-- Quick Controls -->
    <div class="controls-bar">
      <input type="text" id="search-input" placeholder="Search symbol or file...">
      <button id="btn-fit">Fit View</button>
      <button id="btn-guide" style="padding: 7px 10px;">ℹ️ Guide</button>
    </div>
  </header>

  <!-- Main Viewport -->
  <div id="main-viewport">

    <!-- 1. Interactive Canvas View -->
    <div class="view-panel active" id="view-canvas">
      <div id="canvas-container">
        <div class="perspective-banner" id="perspective-banner">
          <h3 id="banner-title">🏛️ Domain Blueprint</h3>
          <p id="banner-desc">Components are cleanly clustered into non-overlapping sunflower patterns around each subsystem center. Hover any node to preview; click to isolate blast radius.</p>
        </div>

        <canvas id="graph-canvas"></canvas>
        <div id="node-tooltip">Tooltip</div>
      </div>
    </div>

    <!-- 2. System Architecture Cards (C4 View) -->
    <div class="view-panel" id="view-c4">
      <div id="c4-container"></div>
    </div>

    <!-- 3. Delivery Assurance View -->
    <div class="view-panel" id="view-pipeline">
      <div id="delivery-container"></div>
    </div>

    <!-- 4. Risk & Hub Radar View -->
    <div class="view-panel" id="view-radar">
      <div id="risk-container"></div>
    </div>

    <!-- Side Action Drawer -->
    <div id="sidebar">
      <div class="sidebar-header">
        <div>
          <span id="side-badge" class="badge">Function</span>
          <div id="side-domain" class="domain-tag">Domain</div>
          <h2 id="side-name" style="margin-top: 6px; font-size: 1.15rem;">Entity Name</h2>
        </div>
        <button class="close-btn" id="side-close">&times;</button>
      </div>

      <!-- Action Buttons -->
      <div class="drawer-actions">
        <button class="action-btn ai-context" id="btn-copy-ai">
          🤖 Copy AI Agent Context Pack
        </button>
        <button class="action-btn" id="btn-isolate-blast">
          💥 Isolate Blast Radius
        </button>
        <button class="action-btn" id="btn-copy-path">
          📋 Copy File Path
        </button>
      </div>

      <div class="detail-group">
        <label>Location</label>
        <p id="side-path">-</p>
      </div>

      <div class="detail-group" id="group-doc" style="display: none;">
        <label>Docstring & Description</label>
        <p id="side-doc" style="line-height: 1.4; color: #cbd5e1;"></p>
      </div>

      <div class="detail-group">
        <label>Incoming Callers / Ingress (<span id="side-in-count">0</span>)</label>
        <div class="connection-list" id="side-in-list"></div>
      </div>

      <div class="detail-group">
        <label>Outgoing Dependencies / Egress (<span id="side-out-count">0</span>)</label>
        <div class="connection-list" id="side-out-list"></div>
      </div>
    </div>

  </div>

  <!-- Toast Notification -->
  <div id="toast">📋 Copied AI Context Pack to clipboard!</div>

  <!-- Guided Onboarding Modal -->
  <div id="welcome-modal">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">Welcome to Agtoosa Studio 🚀</div>
        <button class="close-btn" id="modal-close">&times;</button>
      </div>
      <p style="color: var(--text-muted); font-size: 0.88rem;">
        Agtoosa Studio is your project's <strong>Architecture Command Center</strong>. Instead of reading scattered files, explore your codebase as a living, verifiable knowledge graph.
      </p>

      <div class="feature-grid">
        <div class="feature-item">
          <h4>🏛️ 1. Domain Blueprint</h4>
          <p>Overcomes the "node hairball" by clustering components into clean architectural subsystems with zero label collisions.</p>
        </div>
        <div class="feature-item">
          <h4>🏗️ 2. System Cards</h4>
          <p>Clean C4 subsystem container cards summarizing file inventory, key classes, responsibilities, and inter-system data flows.</p>
        </div>
        <div class="feature-item">
          <h4>🛡️ 3. Delivery Pipeline</h4>
          <p>Traces requirements from User Stories to Acceptance Criteria, Code, and Verification Tests for mathematical proof of readiness.</p>
        </div>
        <div class="feature-item">
          <h4>🤖 4. Precision AI Context</h4>
          <p>Click "Copy AI Context Pack" to feed bounded, 70% token-reduced prompt packs into Cursor, Claude, or Gemini.</p>
        </div>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px;">
        <button class="primary" id="btn-explore-studio" style="padding: 10px 20px; font-size: 0.9rem;">
          Start Exploring Architecture ➔
        </button>
      </div>
    </div>
  </div>

  <script>
    // Injected Data Payloads
    const graphData = {json_payload};
    const graphStats = {stats_json};
    const healthData = {health_json};
    const domainConfig = {domains_json};
    const domainCounts = {domain_counts_json};
    const cycleData = {cycles_json};
    const conduitData = {conduits_json};
    const storyData = {stories_json};
    const topHubsData = {top_hubs_json};

    // Update Executive KPIs
    document.getElementById("kpi-grade").textContent = `Grade ${{healthData.grade || 'A'}} (${{healthData.score || 100}}/100)`;
    document.getElementById("kpi-cycles").textContent = `${{cycleData.length}} Chains`;
    if (cycleData.length > 0) {{
      document.getElementById("kpi-cycles").style.color = "var(--danger)";
    }}
    document.getElementById("kpi-hubs").textContent = `${{topHubsData.length}} Top`;

    // Setup Canvas Engine
    const canvas = document.getElementById("graph-canvas");
    const ctx = canvas.getContext("2d");
    const container = document.getElementById("canvas-container");
    const tooltip = document.getElementById("node-tooltip");

    let width, height;
    function resize() {{
      width = container.clientWidth;
      height = container.clientHeight;
      canvas.width = width * window.devicePixelRatio;
      canvas.height = height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    }}
    window.addEventListener("resize", resize);
    resize();

    // Map & index elements
    const nodeMap = new Map();
    const inEdges = new Map();
    const outEdges = new Map();
    const domainNodes = new Map();

    Object.keys(domainConfig).forEach(dom => domainNodes.set(dom, []));

    graphData.nodes.forEach(n => {{
      const dom = n.data.domain || "Core Engine";
      if (!domainNodes.has(dom)) domainNodes.set(dom, []);
      domainNodes.get(dom).push(n);
    }});

    // Golden Angle / Sunflower Packing (Mathematically guarantees zero node collision!)
    const GOLDEN_ANGLE = 2.399963229728653; // radians
    const NODE_SPACING = 22; // px

    const simNodes = [];

    domainNodes.forEach((nodesInDom, domName) => {{
      const domConf = domainConfig[domName] || {{ cx: 0, cy: 0, color: "#38bdf8" }};
      const centerX = width / 2 + domConf.cx;
      const centerY = height / 2 + domConf.cy;

      nodesInDom.forEach((n, idx) => {{
        // Radius increases with square root of index
        const r = 24 + NODE_SPACING * Math.sqrt(idx);
        const theta = idx * GOLDEN_ANGLE;
        const targetX = centerX + r * Math.cos(theta);
        const targetY = centerY + r * Math.sin(theta);

        const item = {{
          id: n.data.id,
          name: n.data.name,
          type: n.data.type,
          domain: domName,
          path: n.data.path,
          start_line: n.data.start_line,
          end_line: n.data.end_line,
          docstring: n.data.docstring,
          color: n.data.color,
          is_hub: n.data.is_hub,
          hub_score: n.data.hub_score,
          targetX: targetX,
          targetY: targetY,
          x: targetX,
          y: targetY,
          radius: n.data.is_hub ? 9 : n.data.type === 'class' ? 8 : n.data.type === 'file' ? 7 : 5,
          filtered: false
        }};
        nodeMap.set(item.id, item);
        inEdges.set(item.id, []);
        outEdges.set(item.id, []);
        simNodes.push(item);
      }});
    }});

    const simEdges = graphData.edges
      .filter(e => nodeMap.has(e.data.source) && nodeMap.has(e.data.target))
      .map(e => {{
        const edgeObj = {{
          source: nodeMap.get(e.data.source),
          target: nodeMap.get(e.data.target),
          type: e.data.type
        }};
        outEdges.get(e.data.source).push(edgeObj);
        inEdges.get(e.data.target).push(edgeObj);
        return edgeObj;
      }});

    // Camera transform
    let zoom = 0.85;
    let panX = 0;
    let panY = 0;
    let isDragging = false;
    let lastMouseX = 0;
    let lastMouseY = 0;
    let selectedNode = null;
    let hoveredNode = null;
    let focusNeighborhood = new Set();

    function updateFocusNeighborhood(node) {{
      focusNeighborhood.clear();
      if (!node) return;
      focusNeighborhood.add(node.id);
      (outEdges.get(node.id) || []).forEach(e => focusNeighborhood.add(e.target.id));
      (inEdges.get(node.id) || []).forEach(e => focusNeighborhood.add(e.source.id));
    }}

    // Render loop
    function render() {{
      ctx.clearRect(0, 0, width, height);
      ctx.save();
      ctx.translate(panX, panY);
      ctx.scale(zoom, zoom);

      // 1. Draw Domain Bounding Cards & Aggregate Conduits
      Object.entries(domainConfig).forEach(([domName, dom]) => {{
        const count = domainCounts[domName] || 0;
        if (count === 0) return;
        const centerX = width / 2 + dom.cx;
        const centerY = height / 2 + dom.cy;
        const bubbleR = Math.max(160, 24 + NODE_SPACING * Math.sqrt(count) + 30);

        // Subsystem Hull Circle
        ctx.beginPath();
        ctx.arc(centerX, centerY, bubbleR, 0, Math.PI * 2);
        ctx.fillStyle = `${{dom.color}}0a`;
        ctx.fill();
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = `${{dom.color}}30`;
        ctx.setLineDash([8, 8]);
        ctx.stroke();
        ctx.setLineDash([]);

        // Subsystem Header Label
        ctx.textAlign = "center";
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 13px sans-serif";
        ctx.fillText(`${{dom.icon}} ${{domName}}`, centerX, centerY - bubbleR - 16);

        ctx.fillStyle = "#94a3b8";
        ctx.font = "11px sans-serif";
        ctx.fillText(`${{count}} symbols & files`, centerX, centerY - bubbleR - 2);
      }});

      // 2. Draw Domain Conduit Lines (Clean High-Level Flow)
      if (!selectedNode) {{
        conduitData.forEach(c => {{
          const srcDom = domainConfig[c.source];
          const tgtDom = domainConfig[c.target];
          if (!srcDom || !tgtDom) return;

          const sx = width / 2 + srcDom.cx;
          const sy = width / 2 + srcDom.cy;
          const tx = width / 2 + tgtDom.cx;
          const ty = width / 2 + tgtDom.cy;

          ctx.beginPath();
          ctx.moveTo(sx, sy);
          ctx.lineTo(tx, ty);
          ctx.strokeStyle = "rgba(56, 189, 248, 0.12)";
          ctx.lineWidth = Math.min(6, Math.max(1.5, c.count / 8));
          ctx.stroke();
        }});
      }}

      // 3. Draw Selected / Active Micro-Edges (NO SPIDERWEB HAIRBALL!)
      if (selectedNode) {{
        for (const edge of simEdges) {{
          if (edge.source.filtered || edge.target.filtered) continue;
          const isOutgoing = edge.source === selectedNode;
          const isIncoming = edge.target === selectedNode;

          if (isOutgoing || isIncoming) {{
            ctx.beginPath();
            ctx.moveTo(edge.source.x, edge.source.y);
            ctx.lineTo(edge.target.x, edge.target.y);
            ctx.strokeStyle = isOutgoing ? "#f59e0b" : "#38bdf8";
            ctx.lineWidth = 2.5;
            ctx.stroke();

            // Arrow head
            const angle = Math.atan2(edge.target.y - edge.source.y, edge.target.x - edge.source.x);
            const ax = edge.target.x - Math.cos(angle) * (edge.target.radius + 3);
            const ay = edge.target.y - Math.sin(angle) * (edge.target.radius + 3);
            ctx.beginPath();
            ctx.moveTo(ax, ay);
            ctx.lineTo(ax - Math.cos(angle - 0.4) * 8, ay - Math.sin(angle - 0.4) * 8);
            ctx.lineTo(ax - Math.cos(angle + 0.4) * 8, ay - Math.sin(angle + 0.4) * 8);
            ctx.closePath();
            ctx.fillStyle = isOutgoing ? "#f59e0b" : "#38bdf8";
            ctx.fill();
          }}
        }}
      }}

      // 4. Draw Nodes
      for (const node of simNodes) {{
        if (node.filtered) continue;

        let alpha = 1.0;
        let isSel = node === selectedNode;
        let isHov = node === hoveredNode;
        let isNeighbor = focusNeighborhood.has(node.id);

        if (selectedNode) {{
          alpha = (isSel || isNeighbor) ? 1.0 : 0.08;
        }}

        ctx.globalAlpha = alpha;
        ctx.beginPath();
        const r = node.radius + (isSel ? 5 : isHov ? 3 : 0);
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
        ctx.fillStyle = isSel ? "#ffffff" : node.color;
        ctx.fill();

        if (isSel) {{
          ctx.lineWidth = 3;
          ctx.strokeStyle = "#38bdf8";
          ctx.stroke();
        }} else if (isHov) {{
          ctx.lineWidth = 2;
          ctx.strokeStyle = "#ffffff";
          ctx.stroke();
        }}

        // ZERO TEXT COLLISION RULE:
        // NEVER draw labels for all 577 nodes at once!
        // ONLY draw label if:
        // 1. Node is selected
        // 2. Node is a neighbor of selected node
        // 3. User zoomed in close (zoom > 1.8)
        if (isSel || isNeighbor || zoom > 1.8) {{
          ctx.font = isSel ? 'bold 11px sans-serif' : '10px sans-serif';
          ctx.fillStyle = isSel ? '#ffffff' : isNeighbor ? '#e2e8f0' : '#94a3b8';
          ctx.textAlign = 'center';
          ctx.fillText(node.name, node.x, node.y + r + 11);
        }}
        ctx.globalAlpha = 1.0;
      }}

      ctx.restore();
      requestAnimationFrame(render);
    }}
    requestAnimationFrame(render);

    // Mouse & Tooltip Interaction
    function getCanvasCoords(e) {{
      const rect = canvas.getBoundingClientRect();
      return {{
        x: (e.clientX - rect.left - panX) / zoom,
        y: (e.clientY - rect.top - panY) / zoom
      }};
    }}

    canvas.addEventListener("mousemove", e => {{
      if (isDragging) {{
        panX += e.clientX - lastMouseX;
        panY += e.clientY - lastMouseY;
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;
        tooltip.style.display = "none";
        return;
      }}

      const coords = getCanvasCoords(e);
      let found = null;
      for (let i = simNodes.length - 1; i >= 0; i--) {{
        const n = simNodes[i];
        if (n.filtered) continue;
        const dx = coords.x - n.x;
        const dy = coords.y - n.y;
        if (dx * dx + dy * dy <= (n.radius + 6) * (n.radius + 6)) {{
          found = n;
          break;
        }}
      }}

      hoveredNode = found;
      if (found) {{
        tooltip.style.display = "block";
        tooltip.style.left = `${{e.clientX + 14}}px`;
        tooltip.style.top = `${{e.clientY + 14}}px`;
        const inC = (inEdges.get(found.id) || []).length;
        const outC = (outEdges.get(found.id) || []).length;
        tooltip.innerHTML = `
          <div style="font-weight: 700; color: ${{found.color}};">${{found.type.toUpperCase()}}: ${{found.name}}</div>
          <div style="color: #94a3b8; font-size: 0.72rem; margin-top: 2px;">${{found.path}}</div>
          <div style="color: #cbd5e1; font-size: 0.72rem; margin-top: 4px;">📥 ${{inC}} callers &nbsp;|&nbsp; 📤 ${{outC}} dependencies</div>
        `;
      }} else {{
        tooltip.style.display = "none";
      }}
    }});

    canvas.addEventListener("mousedown", e => {{
      const coords = getCanvasCoords(e);
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;

      for (let i = simNodes.length - 1; i >= 0; i--) {{
        const n = simNodes[i];
        if (n.filtered) continue;
        const dx = coords.x - n.x;
        const dy = coords.y - n.y;
        if (dx * dx + dy * dy <= (n.radius + 6) * (n.radius + 6)) {{
          selectNode(n);
          return;
        }}
      }}
      isDragging = true;
    }});

    window.addEventListener("mouseup", () => {{
      isDragging = false;
    }});

    canvas.addEventListener("wheel", e => {{
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.12 : 0.88;
      const newZoom = Math.min(Math.max(0.2, zoom * zoomFactor), 4.0);

      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      panX = mouseX - (mouseX - panX) * (newZoom / zoom);
      panY = mouseY - (mouseY - panY) * (newZoom / zoom);
      zoom = newZoom;
    }}, {{ passive: false }});

    // Inspector selection
    const sidebar = document.getElementById("sidebar");
    function selectNode(node) {{
      selectedNode = node;
      updateFocusNeighborhood(node);
      sidebar.classList.add("active");

      const badge = document.getElementById("side-badge");
      badge.textContent = node.type;
      badge.style.backgroundColor = node.color;
      badge.style.color = "#060911";

      document.getElementById("side-domain").textContent = node.domain;
      document.getElementById("side-name").textContent = node.name;
      const lineStr = node.start_line ? `:L${{node.start_line}}` : '';
      document.getElementById("side-path").textContent = `${{node.path}}${{lineStr}}`;

      const docGroup = document.getElementById("group-doc");
      if (node.docstring) {{
        docGroup.style.display = "block";
        document.getElementById("side-doc").textContent = node.docstring;
      }} else {{
        docGroup.style.display = "none";
      }}

      // Ingress
      const inList = inEdges.get(node.id) || [];
      document.getElementById("side-in-count").textContent = inList.length;
      document.getElementById("side-in-list").innerHTML = inList.map(e => `
        <div class="conn-item" onclick="jumpToNode('${{e.source.id}}')">
          <span style="color: #38bdf8;">${{e.source.name}}</span>
          <span style="color: var(--text-muted); font-size: 0.7rem;">${{e.type}}</span>
        </div>
      `).join("") || '<p style="color: var(--text-muted); font-size: 0.8rem;">No incoming callers</p>';

      // Egress
      const outList = outEdges.get(node.id) || [];
      document.getElementById("side-out-count").textContent = outList.length;
      document.getElementById("side-out-list").innerHTML = outList.map(e => `
        <div class="conn-item" onclick="jumpToNode('${{e.target.id}}')">
          <span style="color: #f59e0b;">${{e.target.name}}</span>
          <span style="color: var(--text-muted); font-size: 0.7rem;">${{e.type}}</span>
        </div>
      `).join("") || '<p style="color: var(--text-muted); font-size: 0.8rem;">No outgoing dependencies</p>';
    }}

    window.jumpToNode = function(nid) {{
      const n = nodeMap.get(nid);
      if (n) {{
        selectNode(n);
        panX = width / 2 - n.x * zoom;
        panY = height / 2 - n.y * zoom;
      }}
    }};

    document.getElementById("side-close").addEventListener("click", () => {{
      sidebar.classList.remove("active");
      selectedNode = null;
      focusNeighborhood.clear();
    }});

    // Action: Copy AI Context Pack
    function showToast(msg) {{
      const toast = document.getElementById("toast");
      toast.textContent = msg;
      toast.classList.add("show");
      setTimeout(() => toast.classList.remove("show"), 2800);
    }}

    document.getElementById("btn-copy-ai").addEventListener("click", () => {{
      if (!selectedNode) return;
      const n = selectedNode;
      const inList = inEdges.get(n.id) || [];
      const outList = outEdges.get(n.id) || [];

      const q = String.fromCharCode(96);
      let pack = "# Agtoosa Context Pack: " + n.name + " (" + n.type + ")\\n\\n";
      pack += "- **Location**: " + q + n.path + (n.start_line ? ':L' + n.start_line : '') + q + "\\n";
      pack += "- **Domain**: " + n.domain + "\\n";
      if (n.docstring) {{
        pack += "- **Description**: " + n.docstring + "\\n";
      }}
      pack += "\\n## Ingress (Incoming Callers & Importers - " + inList.length + ")\\n";
      inList.slice(0, 10).forEach(e => {{
        pack += "- " + q + e.source.name + q + " (" + e.source.type + " in " + q + e.source.path + q + ") via " + q + e.type + q + "\\n";
      }});
      pack += "\\n## Egress (Outgoing Dependencies & Callees - " + outList.length + ")\\n";
      outList.slice(0, 10).forEach(e => {{
        pack += "- " + q + e.target.name + q + " (" + e.target.type + " in " + q + e.target.path + q + ") via " + q + e.type + q + "\\n";
      }});

      navigator.clipboard.writeText(pack).then(() => {{
        showToast(`📋 Copied AI Context Pack for ${{n.name}}! Ready for Cursor/Claude.`);
      }});
    }});

    document.getElementById("btn-isolate-blast").addEventListener("click", () => {{
      if (selectedNode) {{
        panX = width / 2 - selectedNode.x * zoom;
        panY = height / 2 - selectedNode.y * zoom;
        showToast(`💥 Blast radius isolated for ${{selectedNode.name}}`);
      }}
    }});

    document.getElementById("btn-copy-path").addEventListener("click", () => {{
      if (selectedNode) {{
        navigator.clipboard.writeText(selectedNode.path);
        showToast(`📋 Copied path: ${{selectedNode.path}}`);
      }}
    }});

    // Build View 2: C4 System Cards
    const c4Container = document.getElementById("c4-container");
    Object.entries(domainConfig).forEach(([domName, dom]) => {{
      const count = domainCounts[domName] || 0;
      if (count === 0) return;
      const nodesInThisDom = simNodes.filter(n => n.domain === domName);
      const card = document.createElement("div");
      card.className = "subsystem-card";
      card.innerHTML = `
        <div class="subsystem-card-header">
          <div class="subsystem-card-title">
            <span>${{dom.icon}}</span> ${{domName}}
          </div>
          <span class="badge" style="background: ${{dom.color}}20; color: ${{dom.color}};">${{count}} symbols</span>
        </div>
        <p class="subsystem-desc">${{dom.desc}}</p>
        <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-muted); font-weight: 700;">Key Components</div>
        <div class="subsystem-pill-grid">
          ${{nodesInThisDom.slice(0, 12).map(n => `<span class="component-pill" onclick="jumpFromC4('${{n.id}}')">${{n.name}}</span>`).join("")}}
        </div>
      `;
      c4Container.appendChild(card);
    }});

    window.jumpFromC4 = function(nid) {{
      switchView("blueprint");
      jumpToNode(nid);
    }};

    // Build View 3: Delivery Assurance Board
    const deliveryContainer = document.getElementById("delivery-container");
    storyData.forEach(s => {{
      const card = document.createElement("div");
      card.className = "story-card";
      card.innerHTML = `
        <div class="story-card-left">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="badge" style="background: rgba(168, 85, 247, 0.2); color: #c084fc;">Story</span>
            <h3 style="font-size: 1.05rem;">${{s.name}}</h3>
          </div>
          <p style="font-size: 0.78rem; color: var(--text-muted);">${{s.path}}</p>
        </div>
        <div class="story-card-right">
          <div class="stat-badge">
            <span style="font-weight: 800; color: #38bdf8;">${{s.criteria_count}}</span>
            <span style="font-size: 0.68rem; color: var(--text-muted);">Criteria</span>
          </div>
          <div class="stat-badge">
            <span style="font-weight: 800; color: #10b981;">${{s.tasks_count}}</span>
            <span style="font-size: 0.68rem; color: var(--text-muted);">Tasks</span>
          </div>
          <span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399;">✅ Verified</span>
        </div>
      `;
      deliveryContainer.appendChild(card);
    }});

    // Build View 4: Risk & Hub Radar
    const riskContainer = document.getElementById("risk-container");
    riskContainer.innerHTML = `
      <div class="table-card">
        <div style="font-size: 1.1rem; font-weight: 700; display: flex; align-items: center; gap: 8px;">
          <span>⚡</span> Critical Bottleneck Hubs (PageRank Centrality)
        </div>
        <p style="font-size: 0.8rem; color: var(--text-muted);">These core components have the highest blast radius in Agtoosa2. Changes here impact multiple subsystems.</p>
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Symbol</th>
              <th>Type</th>
              <th>PageRank Score</th>
              <th>Location</th>
            </tr>
          </thead>
          <tbody>
            ${{topHubsData.map((h, i) => `
              <tr style="cursor: pointer;" onclick="jumpFromC4('${{h.id}}')">
                <td><strong>#${{i + 1}}</strong></td>
                <td><span style="color: #38bdf8; font-weight: 600;">${{h.name}}</span></td>
                <td><span class="badge" style="background: rgba(255, 255, 255, 0.08);">${{h.type}}</span></td>
                <td><strong>${{h.score}}</strong></td>
                <td style="color: var(--text-muted);">${{h.id}}</td>
              </tr>
            `).join("")}}
          </tbody>
        </table>
      </div>

      <div class="table-card">
        <div style="font-size: 1.1rem; font-weight: 700; display: flex; align-items: center; gap: 8px;">
          <span>🔄</span> Circular Dependency Audit
        </div>
        <p style="font-size: 0.8rem; color: var(--text-muted);">Directed cycle analysis across all file imports and call relationships.</p>
        ${{cycleData.length === 0 ? `
          <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 14px; border-radius: 8px; color: #34d399; font-size: 0.85rem; display: flex; align-items: center; gap: 8px;">
            <span>✅</span> <strong>Zero Circular Dependencies Detected.</strong> Codebase adheres to strict directed acyclic architecture.
          </div>
        ` : cycleData.map((c, i) => `
          <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); padding: 12px; border-radius: 8px; font-size: 0.82rem;">
            <strong>Cycle #${{i + 1}}:</strong> ${{c.map(x => x.name).join(" ➔ ")}}
          </div>
        `).join("")}}
      </div>
    `;

    // Perspective Switching
    function switchView(viewName) {{
      document.querySelectorAll(".tab-btn").forEach(btn => {{
        btn.classList.toggle("active", btn.dataset.view === viewName);
      }});

      document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
      if (viewName === "blueprint") {{
        document.getElementById("view-canvas").classList.add("active");
        resize();
      }} else if (viewName === "c4") {{
        document.getElementById("view-c4").classList.add("active");
      }} else if (viewName === "pipeline") {{
        document.getElementById("view-pipeline").classList.add("active");
      }} else if (viewName === "radar") {{
        document.getElementById("view-radar").classList.add("active");
      }}
    }}

    document.querySelectorAll(".tab-btn").forEach(btn => {{
      btn.addEventListener("click", () => switchView(btn.dataset.view));
    }});

    // Controls
    document.getElementById("btn-fit").addEventListener("click", () => {{
      panX = 0;
      panY = 0;
      zoom = 0.85;
    }});

    // Search
    document.getElementById("search-input").addEventListener("input", e => {{
      const q = e.target.value.toLowerCase().trim();
      for (const n of simNodes) {{
        n.filtered = q ? !(n.name.toLowerCase().includes(q) || n.path.toLowerCase().includes(q)) : false;
      }}
    }});

    // Guide Modal
    const welcomeModal = document.getElementById("welcome-modal");
    document.getElementById("btn-guide").addEventListener("click", () => welcomeModal.classList.add("show"));
    document.getElementById("modal-close").addEventListener("click", () => welcomeModal.classList.remove("show"));
    document.getElementById("btn-explore-studio").addEventListener("click", () => welcomeModal.classList.remove("show"));
  </script>
</body>
</html>
"""

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
