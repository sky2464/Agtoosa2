"""Interactive standalone architecture exploration visualizer."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import webbrowser

from agtoosa.graph.store import GraphStore


class VisualizerEngine:
    """Generates self-contained, offline interactive HTML graph visualization."""

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

    def __init__(self, store: GraphStore):
        self.store = store

    def generate_html(self, filter_type: Optional[str] = None) -> str:
        """Generate standalone HTML document embedding graph data and visualization engine."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        if filter_type:
            ft = filter_type.lower()
            valid_node_ids = {n["id"] for n in nodes if n["node_type"].lower() == ft}
            nodes = [n for n in nodes if n["id"] in valid_node_ids]
            edges = [e for e in edges if e["source_id"] in valid_node_ids and e["target_id"] in valid_node_ids]

        stats = self.store.get_stats().to_dict()

        # Format elements for visualization
        elements_data = {
            "nodes": [
                {
                    "data": {
                        "id": n["id"],
                        "name": n["name"],
                        "type": n["node_type"],
                        "path": n["path"],
                        "start_line": n.get("start_line"),
                        "end_line": n.get("end_line"),
                        "docstring": n.get("docstring") or "",
                        "color": self.NODE_COLORS.get(n["node_type"], "#38bdf8"),
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

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agtoosa2 — Architecture Graph Visualizer</title>
  <style>
    :root {{
      --bg: #0b0f19;
      --surface: rgba(17, 24, 39, 0.85);
      --surface-border: rgba(255, 255, 255, 0.1);
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --accent: #818cf8;
      --panel-width: 380px;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      background: var(--bg);
      color: var(--text);
      overflow: hidden;
      width: 100vw;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    header {{
      height: 60px;
      background: var(--surface);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--surface-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      z-index: 20;
    }}

    .logo {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 700;
      font-size: 1.15rem;
      letter-spacing: -0.02em;
    }}
    .logo span {{ color: var(--primary); }}

    .controls {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    input, select, button {{
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid var(--surface-border);
      color: var(--text);
      padding: 7px 14px;
      border-radius: 6px;
      font-size: 0.85rem;
      outline: none;
      transition: all 0.2s;
    }}

    input:focus, select:focus {{
      border-color: var(--primary);
      box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
    }}

    button {{
      cursor: pointer;
      font-weight: 500;
    }}
    button:hover {{
      background: rgba(51, 65, 85, 0.9);
      border-color: rgba(255, 255, 255, 0.2);
    }}

    button.primary {{
      background: #0284c7;
      border-color: #38bdf8;
    }}
    button.primary:hover {{
      background: #0369a1;
    }}

    #canvas-container {{
      flex: 1;
      position: relative;
      width: 100%;
      height: calc(100vh - 60px);
      background: radial-gradient(circle at center, #131b2e 0%, #0b0f19 100%);
    }}

    canvas {{
      display: block;
      width: 100%;
      height: 100%;
    }}

    #sidebar {{
      position: absolute;
      top: 16px;
      right: 16px;
      bottom: 16px;
      width: var(--panel-width);
      background: var(--surface);
      backdrop-filter: blur(16px);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      z-index: 10;
      transform: translateX(calc(100% + 24px));
      transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      box-shadow: -8px 0 24px rgba(0, 0, 0, 0.4);
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
      padding-bottom: 12px;
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

    .close-btn {{
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      font-size: 1.2rem;
      padding: 2px 6px;
    }}
    .close-btn:hover {{ color: var(--text); }}

    .detail-group {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}

    .detail-group label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      color: var(--text-muted);
      letter-spacing: 0.05em;
      font-weight: 600;
    }}

    .detail-group p, .detail-group pre {{
      font-size: 0.85rem;
      color: #e2e8f0;
      word-break: break-word;
    }}

    .connection-list {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-height: 180px;
      overflow-y: auto;
    }}

    .conn-item {{
      background: rgba(255, 255, 255, 0.04);
      padding: 6px 10px;
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

    .legend {{
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: var(--surface);
      backdrop-filter: blur(12px);
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 12px 16px;
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      z-index: 5;
      font-size: 0.75rem;
      max-width: 600px;
    }}

    .legend-item {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .legend-dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }}

    #hud-stats {{
      position: absolute;
      top: 16px;
      left: 16px;
      background: var(--surface);
      backdrop-filter: blur(12px);
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 0.8rem;
      color: var(--text-muted);
      z-index: 5;
    }}
    #hud-stats strong {{ color: var(--text); }}
  </style>
</head>
<body>

  <header>
    <div class="logo">
      <span>Agtoosa2</span> Graph Visualizer
    </div>
    <div class="controls">
      <input type="text" id="search-input" placeholder="Search symbols or files...">
      <select id="type-filter">
        <option value="">All Types</option>
        <option value="class">Classes</option>
        <option value="function">Functions</option>
        <option value="file">Files</option>
        <option value="story">Stories</option>
        <option value="criterion">Criteria</option>
        <option value="task">Tasks</option>
        <option value="test">Tests</option>
        <option value="adr">ADRs</option>
      </select>
      <button id="btn-fit">Fit View</button>
      <button id="btn-reset" class="primary">Re-layout</button>
    </div>
  </header>

  <div id="canvas-container">
    <div id="hud-stats">Loading topology...</div>
    <canvas id="graph-canvas"></canvas>

    <div id="sidebar">
      <div class="sidebar-header">
        <div>
          <span id="side-badge" class="badge">Type</span>
          <h2 id="side-name" style="margin-top: 6px; font-size: 1.15rem;">Entity Name</h2>
        </div>
        <button class="close-btn" id="side-close">&times;</button>
      </div>

      <div class="detail-group">
        <label>Location</label>
        <p id="side-path">-</p>
      </div>

      <div class="detail-group" id="group-doc" style="display: none;">
        <label>Documentation</label>
        <p id="side-doc" style="line-height: 1.4; color: #cbd5e1;"></p>
      </div>

      <div class="detail-group">
        <label>Incoming Callers / References (<span id="side-in-count">0</span>)</label>
        <div class="connection-list" id="side-in-list"></div>
      </div>

      <div class="detail-group">
        <label>Outgoing Dependencies / Calls (<span id="side-out-count">0</span>)</label>
        <div class="connection-list" id="side-out-list"></div>
      </div>
    </div>

    <div class="legend">
      <div class="legend-item"><div class="legend-dot" style="background: #0284c7;"></div> Class</div>
      <div class="legend-item"><div class="legend-dot" style="background: #38bdf8;"></div> Function</div>
      <div class="legend-item"><div class="legend-dot" style="background: #64748b;"></div> File</div>
      <div class="legend-item"><div class="legend-dot" style="background: #a855f7;"></div> Story</div>
      <div class="legend-item"><div class="legend-dot" style="background: #c084fc;"></div> Criterion</div>
      <div class="legend-item"><div class="legend-dot" style="background: #10b981;"></div> Test</div>
      <div class="legend-item"><div class="legend-dot" style="background: #f59e0b;"></div> ADR / Doc</div>
    </div>
  </div>

  <script>
    const graphData = {json_payload};
    const graphStats = {stats_json};

    document.getElementById("hud-stats").innerHTML = `
      <strong>${{graphData.nodes.length}}</strong> nodes &nbsp;|&nbsp;
      <strong>${{graphData.edges.length}}</strong> edges &nbsp;|&nbsp;
      Density: <strong>${{graphStats.density || '0.00'}}</strong>
    `;

    // High performance pure-HTML5 Canvas Graph Simulator
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

    // Map & index elements
    const nodeMap = new Map();
    const inEdges = new Map();
    const outEdges = new Map();

    const simNodes = graphData.nodes.map((n, i) => {{
      const angle = (i / graphData.nodes.length) * 2 * Math.PI;
      const radius = 150 + Math.random() * 300;
      const item = {{
        id: n.data.id,
        name: n.data.name,
        type: n.data.type,
        path: n.data.path,
        start_line: n.data.start_line,
        docstring: n.data.docstring,
        color: n.data.color,
        x: width / 2 + Math.cos(angle) * radius,
        y: height / 2 + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        radius: n.data.type === 'class' ? 14 : n.data.type === 'file' ? 12 : 9,
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

    // Camera transform
    let zoom = 1.0;
    let panX = 0;
    let panY = 0;
    let isDragging = false;
    let dragNode = null;
    let lastMouseX = 0;
    let lastMouseY = 0;
    let selectedNode = null;

    // Simulation physics step
    function stepSimulation() {{
      const repulsion = 1200;
      const springLength = 70;
      const springK = 0.04;
      const damping = 0.88;

      // Node repulsion
      for (let i = 0; i < simNodes.length; i++) {{
        const n1 = simNodes[i];
        if (n1.filtered) continue;
        for (let j = i + 1; j < simNodes.length; j++) {{
          const n2 = simNodes[j];
          if (n2.filtered) continue;
          const dx = n2.x - n1.x;
          const dy = n2.y - n1.y;
          const distSq = dx * dx + dy * dy + 100;
          const dist = Math.sqrt(distSq);
          const force = repulsion / distSq;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          n1.vx -= fx;
          n1.vy -= fy;
          n2.vx += fx;
          n2.vy += fy;
        }}
      }}

      // Edge spring attraction
      for (const edge of simEdges) {{
        if (edge.source.filtered || edge.target.filtered) continue;
        const dx = edge.target.x - edge.source.x;
        const dy = edge.target.y - edge.source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - springLength) * springK;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        edge.source.vx += fx;
        edge.source.vy += fy;
        edge.target.vx -= fx;
        edge.target.vy -= fy;
      }}

      // Gravity to center & velocity integration
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

    // Render loop
    function render() {{
      stepSimulation();

      ctx.clearRect(0, 0, width, height);
      ctx.save();
      ctx.translate(panX, panY);
      ctx.scale(zoom, zoom);

      // Draw edges
      for (const edge of simEdges) {{
        if (edge.source.filtered || edge.target.filtered) continue;
        const isHighlight = selectedNode && (edge.source === selectedNode || edge.target === selectedNode);
        ctx.beginPath();
        ctx.moveTo(edge.source.x, edge.source.y);
        ctx.lineTo(edge.target.x, edge.target.y);
        ctx.strokeStyle = isHighlight ? '#38bdf8' : 'rgba(100, 116, 139, 0.25)';
        ctx.lineWidth = isHighlight ? 2 : 1;
        ctx.stroke();

        // Arrow head
        const angle = Math.atan2(edge.target.y - edge.source.y, edge.target.x - edge.source.x);
        const arrowDist = edge.target.radius + 2;
        const ax = edge.target.x - Math.cos(angle) * arrowDist;
        const ay = edge.target.y - Math.sin(angle) * arrowDist;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax - Math.cos(angle - 0.4) * 6, ay - Math.sin(angle - 0.4) * 6);
        ctx.lineTo(ax - Math.cos(angle + 0.4) * 6, ay - Math.sin(angle + 0.4) * 6);
        ctx.closePath();
        ctx.fillStyle = isHighlight ? '#38bdf8' : 'rgba(100, 116, 139, 0.4)';
        ctx.fill();
      }}

      // Draw nodes
      for (const node of simNodes) {{
        if (node.filtered) continue;
        const isSel = node === selectedNode;

        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius + (isSel ? 4 : 0), 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.fill();

        if (isSel) {{
          ctx.lineWidth = 3;
          ctx.strokeStyle = '#ffffff';
          ctx.stroke();
        }}

        // Label
        ctx.font = isSel ? 'bold 11px sans-serif' : '10px sans-serif';
        ctx.fillStyle = isSel ? '#ffffff' : '#cbd5e1';
        ctx.textAlign = 'center';
        ctx.fillText(node.name, node.x, node.y + node.radius + 12);
      }}

      ctx.restore();
      requestAnimationFrame(render);
    }}
    requestAnimationFrame(render);

    // Mouse & Touch interaction
    function getCanvasCoords(e) {{
      const rect = canvas.getBoundingClientRect();
      const clientX = e.clientX - rect.left;
      const clientY = e.clientY - rect.top;
      return {{
        x: (clientX - panX) / zoom,
        y: (clientY - panY) / zoom
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
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      const newZoom = Math.min(Math.max(0.15, zoom * zoomFactor), 4.0);

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
      sidebar.classList.add("active");

      const badge = document.getElementById("side-badge");
      badge.textContent = node.type;
      badge.style.backgroundColor = node.color;
      badge.style.color = "#0b0f19";

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
      const inContainer = document.getElementById("side-in-list");
      inContainer.innerHTML = inList.map(e => `
        <div class="conn-item" onclick="jumpToNode('${{e.source.id}}')">
          <span>${{e.source.name}}</span>
          <span style="color: var(--text-muted); font-size: 0.7rem;">${{e.type}}</span>
        </div>
      `).join("") || '<p style="color: var(--text-muted); font-size: 0.8rem;">No incoming connections</p>';

      // Egress
      const outList = outEdges.get(node.id) || [];
      document.getElementById("side-out-count").textContent = outList.length;
      const outContainer = document.getElementById("side-out-list");
      outContainer.innerHTML = outList.map(e => `
        <div class="conn-item" onclick="jumpToNode('${{e.target.id}}')">
          <span>${{e.target.name}}</span>
          <span style="color: var(--text-muted); font-size: 0.7rem;">${{e.type}}</span>
        </div>
      `).join("") || '<p style="color: var(--text-muted); font-size: 0.8rem;">No outgoing connections</p>';
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
    }});

    // Controls
    document.getElementById("btn-fit").addEventListener("click", () => {{
      if (simNodes.length === 0) return;
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      for (const n of simNodes) {{
        if (n.filtered) continue;
        minX = Math.min(minX, n.x);
        maxX = Math.max(maxX, n.x);
        minY = Math.min(minY, n.y);
        maxY = Math.max(maxY, n.y);
      }}
      const gWidth = maxX - minX + 100;
      const gHeight = maxY - minY + 100;
      zoom = Math.min(width / gWidth, height / gHeight, 1.5);
      panX = width / 2 - ((minX + maxX) / 2) * zoom;
      panY = height / 2 - ((minY + maxY) / 2) * zoom;
    }});

    document.getElementById("btn-reset").addEventListener("click", () => {{
      simNodes.forEach((n, i) => {{
        const angle = (i / simNodes.length) * 2 * Math.PI;
        const radius = 150 + Math.random() * 250;
        n.x = width / 2 + Math.cos(angle) * radius;
        n.y = height / 2 + Math.sin(angle) * radius;
        n.vx = 0;
        n.vy = 0;
      }});
      panX = 0;
      panY = 0;
      zoom = 1.0;
    }});

    // Filtering & Search
    function applyFilters() {{
      const q = document.getElementById("search-input").value.toLowerCase().trim();
      const type = document.getElementById("type-filter").value.toLowerCase();

      for (const n of simNodes) {{
        const matchQ = !q || n.name.toLowerCase().includes(q) || n.path.toLowerCase().includes(q);
        const matchType = !type || n.type.toLowerCase() === type;
        n.filtered = !(matchQ && matchType);
      }}
    }}

    document.getElementById("search-input").addEventListener("input", applyFilters);
    document.getElementById("type-filter").addEventListener("change", applyFilters);
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
