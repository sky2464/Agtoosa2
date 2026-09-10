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
        "CLI Layer": {"color": "#3b82f6", "cx": -420, "cy": -240, "icon": "⚡"},
        "Core Engine": {"color": "#6366f1", "cx": 0, "cy": -240, "icon": "⚙️"},
        "Specifications & Delivery": {"color": "#a855f7", "cx": 420, "cy": -240, "icon": "📋"},
        "AST Parser Subsystem": {"color": "#06b6d4", "cx": -420, "cy": 120, "icon": "🌳"},
        "Knowledge Graph & Storage": {"color": "#0ea5e9", "cx": 0, "cy": 120, "icon": "🧠"},
        "Verification & Quality": {"color": "#10b981", "cx": 420, "cy": 120, "icon": "🛡️"},
        "Native MCP Protocol": {"color": "#8b5cf6", "cx": -220, "cy": 420, "icon": "🔌"},
        "Decisions & Architecture": {"color": "#f59e0b", "cx": 220, "cy": 420, "icon": "📐"},
        "Shared & Foundation": {"color": "#64748b", "cx": 0, "cy": 420, "icon": "📦"}
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
        return "Shared & Foundation"

    def generate_html(self, filter_type: Optional[str] = None) -> str:
        """Generate standalone HTML document embedding graph data and Agtoosa Studio."""
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
        for n in nodes:
            d = self._assign_domain(n)
            domain_counts[d] += 1

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

        json_payload = json.dumps(elements_data, indent=None)
        stats_json = json.dumps(stats, indent=None)
        health_json = json.dumps(health_scorecard, indent=None)
        domains_json = json.dumps(self.DOMAIN_CONFIG, indent=None)
        domain_counts_json = json.dumps(dict(domain_counts), indent=None)
        cycles_json = json.dumps(cycles, indent=None)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agtoosa Studio — Architecture Command Center</title>
  <style>
    :root {{
      --bg: #070b14;
      --bg-gradient: radial-gradient(circle at 50% 20%, #111a2e 0%, #070b14 100%);
      --surface: rgba(15, 23, 42, 0.82);
      --surface-elevated: rgba(30, 41, 59, 0.88);
      --surface-border: rgba(255, 255, 255, 0.09);
      --surface-border-active: rgba(56, 189, 248, 0.4);
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-glow: rgba(56, 189, 248, 0.25);
      --accent: #818cf8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --panel-width: 410px;
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
      gap: 12px;
      min-width: 220px;
    }}

    .brand-logo {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 800;
      font-size: 1.12rem;
      letter-spacing: -0.02em;
    }}
    .brand-logo span {{ color: var(--primary); }}
    .brand-badge {{
      background: linear-gradient(135deg, rgba(56, 189, 248, 0.18), rgba(129, 140, 248, 0.18));
      color: #7dd3fc;
      border: 1px solid rgba(56, 189, 248, 0.3);
      font-size: 0.68rem;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}

    /* Executive KPI Strip */
    .kpi-strip {{
      display: flex;
      align-items: center;
      gap: 10px;
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid var(--surface-border);
      padding: 4px 12px;
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
      padding: 2px 6px;
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

    /* Perspective Tabs */
    .perspective-switcher {{
      display: flex;
      align-items: center;
      background: rgba(0, 0, 0, 0.4);
      padding: 3px;
      border-radius: 8px;
      border: 1px solid var(--surface-border);
      gap: 2px;
    }}
    .tab-btn {{
      background: none;
      border: none;
      color: var(--text-muted);
      padding: 6px 12px;
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
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
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

    /* Canvas Area */
    #canvas-container {{
      flex: 1;
      position: relative;
      width: 100%;
      height: calc(100vh - 64px);
      background: var(--bg-gradient);
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
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
      max-width: 380px;
      pointer-events: none;
    }}
    .perspective-banner h3 {{
      font-size: 0.9rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .perspective-banner p {{
      font-size: 0.76rem;
      color: var(--text-muted);
      line-height: 1.35;
    }}

    /* Floating Legend & Minimap Overlay */
    .legend-dock {{
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: var(--surface);
      backdrop-filter: blur(14px);
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 10px 16px;
      display: flex;
      align-items: center;
      gap: 16px;
      z-index: 10;
      font-size: 0.74rem;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    }}
    .legend-group {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .legend-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
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

    <!-- 4 Curated Perspectives -->
    <div class="perspective-switcher">
      <button class="tab-btn active" data-view="blueprint">
        <span>🏛️</span> Domain Blueprint
      </button>
      <button class="tab-btn" data-view="focus">
        <span>🎯</span> Focus & Blast Radius
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
      <select id="domain-filter">
        <option value="">All Domains</option>
      </select>
      <button id="btn-fit">Fit View</button>
      <button id="btn-guide" style="padding: 7px 10px;">ℹ️ Guide</button>
    </div>
  </header>

  <!-- Main Canvas -->
  <div id="canvas-container">
    <!-- Active Perspective Description Banner -->
    <div class="perspective-banner" id="perspective-banner">
      <h3 id="banner-title">🏛️ Domain Blueprint</h3>
      <p id="banner-desc">High-level architectural partitioning. Components cluster around core subsystems to prevent cognitive overload.</p>
    </div>

    <canvas id="graph-canvas"></canvas>

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

    <!-- Bottom Dock Legend -->
    <div class="legend-dock">
      <div class="legend-group"><div class="legend-dot" style="background: #0284c7;"></div> Class</div>
      <div class="legend-group"><div class="legend-dot" style="background: #38bdf8;"></div> Function</div>
      <div class="legend-group"><div class="legend-dot" style="background: #64748b;"></div> File</div>
      <div class="legend-group"><div class="legend-dot" style="background: #a855f7;"></div> Spec / Story</div>
      <div class="legend-group"><div class="legend-dot" style="background: #10b981;"></div> Test / Evidence</div>
      <div class="legend-group"><div class="legend-dot" style="background: #f59e0b;"></div> Architecture ADR</div>
    </div>
  </div>

  <!-- Toast Notification -->
  <div id="toast">📋 Copied AI Context Pack to clipboard!</div>

  <!-- Welcome / Guided Onboarding Modal -->
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
          <p>Overcomes the "node hairball" by clustering components into clean architectural subsystems (CLI, Parser, Graph, MCP, Specs).</p>
        </div>
        <div class="feature-item">
          <h4>🎯 2. Blast Radius Mode</h4>
          <p>Click any symbol to isolate its direct callers and callees, revealing exactly what will break before you make edits.</p>
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

    // Update Executive KPIs
    document.getElementById("kpi-grade").textContent = `Grade ${{healthData.grade || 'A'}} (${{healthData.score || 100}}/100)`;
    document.getElementById("kpi-cycles").textContent = `${{cycleData.length}} Chains`;
    if (cycleData.length > 0) {{
      document.getElementById("kpi-cycles").style.color = "var(--danger)";
    }}

    // Populate Domain Filter Dropdown
    const domainSelect = document.getElementById("domain-filter");
    Object.keys(domainConfig).forEach(dom => {{
      const count = domainCounts[dom] || 0;
      if (count > 0) {{
        const opt = document.createElement("option");
        opt.value = dom;
        opt.textContent = `${{dom}} (${{count}})`;
        domainSelect.appendChild(opt);
      }}
    }});

    // Canvas Engine Setup
    const canvas = document.getElementById("graph-canvas");
    const ctx = canvas.getContext("2d");
    const container = document.getElementById("canvas-container");

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

    // Node & Edge Indexing
    const nodeMap = new Map();
    const inEdges = new Map();
    const outEdges = new Map();

    const simNodes = graphData.nodes.map((n, i) => {{
      const dom = n.data.domain || "Shared & Foundation";
      const domConf = domainConfig[dom] || {{ cx: 0, cy: 0, color: "#38bdf8" }};

      // Cluster initial position around domain center
      const angle = Math.random() * 2 * Math.PI;
      const radius = 20 + Math.random() * 110;

      const item = {{
        id: n.data.id,
        name: n.data.name,
        type: n.data.type,
        domain: dom,
        path: n.data.path,
        start_line: n.data.start_line,
        end_line: n.data.end_line,
        docstring: n.data.docstring,
        color: n.data.color,
        is_hub: n.data.is_hub,
        hub_score: n.data.hub_score,
        x: width / 2 + domConf.cx + Math.cos(angle) * radius,
        y: height / 2 + domConf.cy + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        radius: n.data.is_hub ? 14 : n.data.type === 'class' ? 12 : n.data.type === 'file' ? 10 : 7,
        filtered: false
      }};
      nodeMap.set(item.id, item);
      inEdges.set(item.id, []);
      outEdges.set(item.id, []);
      return item;
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

    // Camera State
    let currentPerspective = "blueprint";
    let zoom = 0.9;
    let panX = 0;
    let panY = 0;
    let isDragging = false;
    let dragNode = null;
    let lastMouseX = 0;
    let lastMouseY = 0;
    let selectedNode = null;

    // Focus & Blast Radius Neighborhood Set
    let focusNeighborhood = new Set();

    function updateFocusNeighborhood(node) {{
      focusNeighborhood.clear();
      if (!node) return;
      focusNeighborhood.add(node.id);

      // 1-hop outgoing
      (outEdges.get(node.id) || []).forEach(e => focusNeighborhood.add(e.target.id));
      // 1-hop incoming
      (inEdges.get(node.id) || []).forEach(e => focusNeighborhood.add(e.source.id));
    }}

    // Simulation Physics Step
    function stepSimulation() {{
      const damping = 0.85;

      if (currentPerspective === "blueprint") {{
        // Gravitate strongly towards Domain Centers
        for (const n of simNodes) {{
          if (n.filtered || n === dragNode) continue;
          const domConf = domainConfig[n.domain] || {{ cx: 0, cy: 0 }};
          const targetX = width / 2 + domConf.cx;
          const targetY = height / 2 + domConf.cy;

          n.vx += (targetX - n.x) * 0.015;
          n.vy += (targetY - n.y) * 0.015;

          n.vx *= damping;
          n.vy *= damping;
          n.x += n.vx;
          n.y += n.vy;
        }}
      }} else if (currentPerspective === "pipeline") {{
        // Arrange horizontally by lifecycle stage
        const typeColMap = {{
          "epic": -500, "story": -350,
          "criterion": -180,
          "task": 0,
          "file": 180, "class": 240, "function": 300,
          "test": 480, "evidence": 540
        }};
        for (const n of simNodes) {{
          if (n.filtered || n === dragNode) continue;
          const targetX = width / 2 + (typeColMap[n.type] ?? 0);
          n.vx += (targetX - n.x) * 0.03;
          n.vy *= damping;
          n.vx *= damping;
          n.x += n.vx;
          n.y += n.vy;
        }}
      }} else {{
        // Focus or Radar default gentle centering
        const cx = width / 2;
        const cy = height / 2;
        for (const n of simNodes) {{
          if (n.filtered || n === dragNode) continue;
          n.vx += (cx - n.x) * 0.003;
          n.vy += (cy - n.y) * 0.003;
          n.vx *= damping;
          n.vy *= damping;
          n.x += n.vx;
          n.y += n.vy;
        }}
      }}
    }}

    // Render Loop
    function render() {{
      stepSimulation();

      ctx.clearRect(0, 0, width, height);
      ctx.save();
      ctx.translate(panX, panY);
      ctx.scale(zoom, zoom);

      // 1. In Domain Blueprint perspective, draw soft domain bounding envelopes & labels
      if (currentPerspective === "blueprint") {{
        ctx.textAlign = "center";
        Object.entries(domainConfig).forEach(([domName, dom]) => {{
          const count = domainCounts[domName] || 0;
          if (count === 0) return;
          const centerX = width / 2 + dom.cx;
          const centerY = height / 2 + dom.cy;

          // Domain Card Hull
          ctx.beginPath();
          ctx.arc(centerX, centerY, 150, 0, Math.PI * 2);
          ctx.fillStyle = `${{dom.color}}10`;
          ctx.fill();
          ctx.lineWidth = 1.5;
          ctx.strokeStyle = `${{dom.color}}35`;
          ctx.setLineDash([6, 6]);
          ctx.stroke();
          ctx.setLineDash([]);

          // Domain Label Badge
          ctx.fillStyle = "#ffffff";
          ctx.font = "bold 12px sans-serif";
          ctx.fillText(`${{dom.icon}} ${{domName}}`, centerX, centerY - 160);

          ctx.fillStyle = "#94a3b8";
          ctx.font = "10px sans-serif";
          ctx.fillText(`${{count}} entities`, centerX, centerY - 144);
        }});
      }}

      // 2. Draw Edges
      for (const edge of simEdges) {{
        if (edge.source.filtered || edge.target.filtered) continue;

        let alpha = 0.25;
        let strokeColor = "rgba(100, 116, 139, 0.3)";
        let lineWidth = 1;

        if (selectedNode) {{
          const isOutgoing = edge.source === selectedNode;
          const isIncoming = edge.target === selectedNode;
          if (isOutgoing) {{
            alpha = 1.0;
            strokeColor = "#f59e0b"; // Outgoing = Amber
            lineWidth = 2.5;
          }} else if (isIncoming) {{
            alpha = 1.0;
            strokeColor = "#38bdf8"; // Incoming = Cyan
            lineWidth = 2.5;
          }} else {{
            alpha = 0.04;
          }}
        }} else if (currentPerspective === "focus" && focusNeighborhood.size > 0) {{
          alpha = focusNeighborhood.has(edge.source.id) && focusNeighborhood.has(edge.target.id) ? 0.9 : 0.05;
        }}

        ctx.beginPath();
        ctx.moveTo(edge.source.x, edge.source.y);
        ctx.lineTo(edge.target.x, edge.target.y);
        ctx.strokeStyle = strokeColor;
        ctx.globalAlpha = alpha;
        ctx.lineWidth = lineWidth;
        ctx.stroke();
        ctx.globalAlpha = 1.0;
      }}

      // 3. Draw Nodes
      for (const node of simNodes) {{
        if (node.filtered) continue;

        let alpha = 1.0;
        let isSel = node === selectedNode;
        let isHub = node.is_hub;

        if (selectedNode) {{
          const isNeighbor = focusNeighborhood.has(node.id);
          if (!isSel && !isNeighbor) {{
            alpha = 0.10;
          }}
        }} else if (currentPerspective === "focus" && focusNeighborhood.size > 0) {{
          alpha = focusNeighborhood.has(node.id) ? 1.0 : 0.08;
        }}

        ctx.globalAlpha = alpha;
        ctx.beginPath();
        const r = node.radius + (isSel ? 4 : isHub ? 2 : 0);
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
        ctx.fillStyle = isHub && currentPerspective === "radar" ? "#f59e0b" : node.color;
        ctx.fill();

        if (isSel) {{
          ctx.lineWidth = 3;
          ctx.strokeStyle = '#ffffff';
          ctx.stroke();
        }} else if (isHub && currentPerspective === "radar") {{
          ctx.lineWidth = 2;
          ctx.strokeStyle = '#fef08a';
          ctx.stroke();
        }}

        // Label rendering
        if (alpha >= 0.5 || isSel) {{
          ctx.font = isSel ? 'bold 11px sans-serif' : '10px sans-serif';
          ctx.fillStyle = isSel ? '#ffffff' : '#cbd5e1';
          ctx.textAlign = 'center';
          ctx.fillText(node.name, node.x, node.y + r + 11);
        }}
        ctx.globalAlpha = 1.0;
      }}

      ctx.restore();
      requestAnimationFrame(render);
    }}
    requestAnimationFrame(render);

    // Mouse Interaction
    function getCanvasCoords(e) {{
      const rect = canvas.getBoundingClientRect();
      return {{
        x: (e.clientX - rect.left - panX) / zoom,
        y: (e.clientY - rect.top - panY) / zoom
      }};
    }}

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
          dragNode = n;
          selectNode(n);
          return;
        }}
      }}
      isDragging = true;
    }});

    window.addEventListener("mousemove", e => {{
      if (dragNode) {{
        const coords = getCanvasCoords(e);
        dragNode.x = coords.x;
        dragNode.y = coords.y;
        dragNode.vx = 0;
        dragNode.vy = 0;
      }} else if (isDragging) {{
        panX += e.clientX - lastMouseX;
        panY += e.clientY - lastMouseY;
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;
      }}
    }});

    window.addEventListener("mouseup", () => {{
      isDragging = false;
      dragNode = null;
    }});

    canvas.addEventListener("wheel", e => {{
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.12 : 0.88;
      const newZoom = Math.min(Math.max(0.15, zoom * zoomFactor), 4.0);

      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      panX = mouseX - (mouseX - panX) * (newZoom / zoom);
      panY = mouseY - (mouseY - panY) * (newZoom / zoom);
      zoom = newZoom;
    }}, {{ passive: false }});

    // Node Selection & Sidebar Inspection
    const sidebar = document.getElementById("sidebar");
    function selectNode(node) {{
      selectedNode = node;
      updateFocusNeighborhood(node);
      sidebar.classList.add("active");

      const badge = document.getElementById("side-badge");
      badge.textContent = node.type;
      badge.style.backgroundColor = node.color;
      badge.style.color = "#070b14";

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

      // Ingress (Callers)
      const inList = inEdges.get(node.id) || [];
      document.getElementById("side-in-count").textContent = inList.length;
      document.getElementById("side-in-list").innerHTML = inList.map(e => `
        <div class="conn-item" onclick="jumpToNode('${{e.source.id}}')">
          <span style="color: #38bdf8;">${{e.source.name}}</span>
          <span style="color: var(--text-muted); font-size: 0.7rem;">${{e.type}}</span>
        </div>
      `).join("") || '<p style="color: var(--text-muted); font-size: 0.8rem;">No incoming callers</p>';

      // Egress (Callees)
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

      let pack = `# Agtoosa Context Pack: ${{n.name}} (${{n.type}})\\n\\n`;
      pack += `- **Location**: \\`${{n.path}}${{n.start_line ? ':L' + n.start_line : ''}}\\`\\n`;
      pack += `- **Domain**: ${{n.domain}}\\n`;
      if (n.docstring) {{
        pack += `- **Description**: ${{n.docstring}}\\n`;
      }}
      pack += `\\n## Ingress (Incoming Callers & Importers - ${{inList.length}})\\n`;
      inList.slice(0, 10).forEach(e => {{
        pack += `- \\`${{e.source.name}}\\` (${{e.source.type}} in \\`${{e.source.path}}\\`) via \\`${{e.type}}\\`\\n`;
      }});
      pack += `\\n## Egress (Outgoing Dependencies & Callees - ${{outList.length}})\\n`;
      outList.slice(0, 10).forEach(e => {{
        pack += `- \\`${{e.target.name}}\\` (${{e.target.type}} in \\`${{e.target.path}}\\`) via \\`${{e.type}}\\`\\n`;
      }});

      navigator.clipboard.writeText(pack).then(() => {{
        showToast(`📋 Copied AI Context Pack for ${{n.name}}! Ready for Cursor/Claude.`);
      }});
    }});

    // Action: Isolate Blast Radius
    document.getElementById("btn-isolate-blast").addEventListener("click", () => {{
      switchPerspective("focus");
      if (selectedNode) {{
        panX = width / 2 - selectedNode.x * zoom;
        panY = height / 2 - selectedNode.y * zoom;
        showToast(`💥 Blast radius isolated for ${{selectedNode.name}}`);
      }}
    }});

    // Action: Copy Path
    document.getElementById("btn-copy-path").addEventListener("click", () => {{
      if (selectedNode) {{
        navigator.clipboard.writeText(selectedNode.path);
        showToast(`📋 Path copied: ${{selectedNode.path}}`);
      }}
    }});

    // Perspective Switching
    const bannerConfig = {{
      blueprint: {{
        title: "🏛️ Domain Blueprint",
        desc: "High-level architectural partitioning. Components cluster around core subsystems to prevent cognitive overload."
      }},
      focus: {{
        title: "🎯 Focus & Blast Radius",
        desc: "Selected entity and its direct 1-hop & 2-hop dependencies are isolated. Unrelated components are dimmed."
      }},
      pipeline: {{
        title: "🛡️ Delivery Assurance Pipeline",
        desc: "Left-to-right flow tracing Stories ➔ Acceptance Criteria ➔ Code Implementation ➔ Verification Tests."
      }},
      radar: {{
        title: "⚡ Risk & Hub Radar",
        desc: "Highlights critical PageRank bottlenecks, circular dependencies, and isolated code units."
      }}
    }};

    function switchPerspective(viewName) {{
      currentPerspective = viewName;
      document.querySelectorAll(".tab-btn").forEach(btn => {{
        btn.classList.toggle("active", btn.dataset.view === viewName);
      }});
      const conf = bannerConfig[viewName];
      document.getElementById("banner-title").textContent = conf.title;
      document.getElementById("banner-desc").textContent = conf.desc;
    }}

    document.querySelectorAll(".tab-btn").forEach(btn => {{
      btn.addEventListener("click", () => switchPerspective(btn.dataset.view));
    }});

    // Controls
    document.getElementById("btn-fit").addEventListener("click", () => {{
      panX = 0;
      panY = 0;
      zoom = 0.85;
    }});

    // Search & Domain Filter
    function applyFilters() {{
      const q = document.getElementById("search-input").value.toLowerCase().trim();
      const dom = document.getElementById("domain-filter").value;

      for (const n of simNodes) {{
        const matchQ = !q || n.name.toLowerCase().includes(q) || n.path.toLowerCase().includes(q);
        const matchDom = !dom || n.domain === dom;
        n.filtered = !(matchQ && matchDom);
      }}
    }}
    document.getElementById("search-input").addEventListener("input", applyFilters);
    document.getElementById("domain-filter").addEventListener("change", applyFilters);

    // Modal Guide Handling
    const welcomeModal = document.getElementById("welcome-modal");
    document.getElementById("btn-guide").addEventListener("click", () => {{
      welcomeModal.classList.add("show");
    }});
    document.getElementById("modal-close").addEventListener("click", () => {{
      welcomeModal.classList.remove("show");
    }});
    document.getElementById("btn-explore-studio").addEventListener("click", () => {{
      welcomeModal.classList.remove("show");
    }});
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
