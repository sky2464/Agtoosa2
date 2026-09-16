    // ==========================================
    // Interactive Network Graph Engine (Sunflower 2D Canvas)
    // ==========================================
    const netCanvas = document.getElementById("network-canvas");
    const netCtx = netCanvas.getContext("2d");
    const netContainer = document.getElementById("network-container");
    const netTooltip = document.getElementById("network-tooltip");

    let netW = 0, netH = 0;
    function resizeNetwork() {
      if (!netContainer || netContainer.clientWidth === 0) return;
      netW = netContainer.clientWidth;
      netH = netContainer.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      netCanvas.width = netW * dpr;
      netCanvas.height = netH * dpr;
      netCtx.setTransform(1, 0, 0, 1, 0, 0);
      netCtx.scale(dpr, dpr);
      renderNetwork();
    }
    window.addEventListener("resize", resizeNetwork);

    // Sunflower Spiral Packing per Subsystem Domain
    const GOLDEN_ANGLE = 2.399963229728653;
    const NODE_SPACING = 24;

    const simNodes = [];
    const simNodeMap = new Map();

    domainNodes.forEach((nodesInDom, domName) => {
      const domConf = domainConfig[domName] || { cx: 0, cy: 0, color: "#38bdf8" };
      nodesInDom.forEach((n, idx) => {
        const r = 28 + NODE_SPACING * Math.sqrt(idx);
        const theta = idx * GOLDEN_ANGLE;
        const relX = domConf.cx + r * Math.cos(theta);
        const relY = domConf.cy + r * Math.sin(theta);

        const item = {
          id: n.id,
          name: n.name,
          type: n.type,
          domain: domName,
          path: n.path,
          start_line: n.start_line,
          end_line: n.end_line,
          docstring: n.docstring,
          color: n.color,
          is_hub: n.is_hub,
          hub_score: n.hub_score,
          relX: relX,
          relY: relY,
          radius: n.is_hub ? 9 : n.type === 'class' ? 8 : n.type === 'file' ? 7 : 5,
          visible: true,
          highlight: false
        };
        simNodes.push(item);
        simNodeMap.set(item.id, item);
      });
    });

    const netEdges = graphData.edges
      .filter(e => simNodeMap.has(e.data.source) && simNodeMap.has(e.data.target))
      .map(e => ({
        source: simNodeMap.get(e.data.source),
        target: simNodeMap.get(e.data.target),
        type: e.data.type
      }));

    let netZoom = 0.82;
    let netPanX = 0;
    let netPanY = 0;
    let isNetDragging = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let hoveredNetNode = null;
    let selectedNetNode = null;
    let showBottlenecks = false;

    const btnBottlenecks = document.getElementById("graph-btn-bottlenecks");
    if (btnBottlenecks) {
      btnBottlenecks.addEventListener("click", () => {
        showBottlenecks = !showBottlenecks;
        btnBottlenecks.classList.toggle("active", showBottlenecks);
        renderNetwork();
      });
    }

    function resetNetView() {
      netZoom = 0.82;
      netPanX = netW / 2;
      netPanY = netH / 2;
      renderNetwork();
    }

    // Populate Domain Selector
    const domSelect = document.getElementById("graph-domain-select");
    Object.keys(domainConfig).forEach(dom => {
      const opt = document.createElement("option");
      opt.value = dom;
      opt.textContent = dom;
      domSelect.appendChild(opt);
    });

    function updateNetFilters() {
      const domVal = domSelect.value;
      const typeVal = document.getElementById("graph-type-select").value;
      const query = document.getElementById("graph-search-input").value.toLowerCase().trim();

      simNodes.forEach(n => {
        const matchDom = (domVal === "all" || n.domain === domVal);
        const matchType = (typeVal === "all" || n.type === typeVal);
        n.visible = matchDom && matchType;
        n.highlight = query ? (n.name.toLowerCase().includes(query) || (n.path && n.path.toLowerCase().includes(query))) : false;
      });

      if (domVal !== "all" && domainConfig[domVal]) {
        const dc = domainConfig[domVal];
        netPanX = netW / 2 - dc.cx * netZoom;
        netPanY = netH / 2 - dc.cy * netZoom;
      }
      renderNetwork();
    }

    domSelect.addEventListener("change", updateNetFilters);
    document.getElementById("graph-type-select").addEventListener("change", updateNetFilters);
    document.getElementById("graph-search-input").addEventListener("input", updateNetFilters);

    document.getElementById("graph-btn-reset").addEventListener("click", resetNetView);
    document.getElementById("graph-btn-zoom-in").addEventListener("click", () => {
      netZoom = Math.min(3.5, netZoom * 1.25);
      renderNetwork();
    });
    document.getElementById("graph-btn-zoom-out").addEventListener("click", () => {
      netZoom = Math.max(0.2, netZoom / 1.25);
      renderNetwork();
    });

    function isConnectedTo(nodeAId, nodeBId) {
      const inList = inEdges.get(nodeBId) || [];
      if (inList.some(e => e.source.id === nodeAId)) return true;
      const outList = outEdges.get(nodeBId) || [];
      if (outList.some(e => e.target.id === nodeAId)) return true;
      return false;
    }

    function renderNetwork() {
      if (!netW || !netH) return;
      netCtx.clearRect(0, 0, netW, netH);
      netCtx.save();
      netCtx.translate(netPanX, netPanY);
      netCtx.scale(netZoom, netZoom);

      // 1. Subsystem Domain Hulls
      Object.entries(domainConfig).forEach(([domName, dom]) => {
        const count = domainCounts[domName] || 0;
        if (count === 0) return;
        const bubbleR = Math.max(160, 28 + NODE_SPACING * Math.sqrt(count) + 36);

        netCtx.beginPath();
        netCtx.arc(dom.cx, dom.cy, bubbleR, 0, Math.PI * 2);
        netCtx.fillStyle = `${dom.color}0a`;
        netCtx.fill();
        netCtx.lineWidth = 1.5;
        netCtx.strokeStyle = `${dom.color}35`;
        netCtx.setLineDash([8, 8]);
        netCtx.stroke();
        netCtx.setLineDash([]);

        // Label
        netCtx.textAlign = "center";
        netCtx.fillStyle = "#ffffff";
        netCtx.font = "bold 13px sans-serif";
        netCtx.fillText(`${dom.icon} ${domName}`, dom.cx, dom.cy - bubbleR - 16);
        netCtx.fillStyle = "#94a3b8";
        netCtx.font = "11px sans-serif";
        netCtx.fillText(`${count} entities`, dom.cx, dom.cy - bubbleR - 2);
      });

      // 2. High-level conduits between domains
      conduitData.forEach(c => {
        const sDom = domainConfig[c.source];
        const tDom = domainConfig[c.target];
        if (!sDom || !tDom) return;
        netCtx.beginPath();
        netCtx.moveTo(sDom.cx, sDom.cy);
        netCtx.lineTo(tDom.cx, tDom.cy);
        netCtx.strokeStyle = "rgba(56, 189, 248, 0.12)";
        netCtx.lineWidth = Math.min(6, Math.max(1.5, c.count / 8));
        netCtx.stroke();
      });

      // 2B. Forman-Ricci Hyperbolic Bottleneck Edges Overlay (Stage 54)
      if (showBottlenecks && typeof bottleneckEdges !== "undefined" && bottleneckEdges.size > 0) {
        netEdges.forEach(e => {
          if (!e.source.visible || !e.target.visible) return;
          const key = `${e.source.id}->${e.target.id}`;
          if (bottleneckEdges.has(key)) {
            netCtx.beginPath();
            netCtx.moveTo(e.source.relX, e.source.relY);
            netCtx.lineTo(e.target.relX, e.target.relY);
            netCtx.strokeStyle = "rgba(244, 63, 94, 0.9)";
            netCtx.lineWidth = 3.5;
            netCtx.setLineDash([6, 4]);
            netCtx.stroke();
            netCtx.setLineDash([]);
          }
        });
      }

      // 3. Active micro-edges for selected or hovered node
      const activeNode = hoveredNetNode || selectedNetNode;
      if (activeNode) {
        netEdges.forEach(e => {
          if (!e.source.visible || !e.target.visible) return;
          if (e.source.id === activeNode.id || e.target.id === activeNode.id) {
            netCtx.beginPath();
            netCtx.moveTo(e.source.relX, e.source.relY);
            netCtx.lineTo(e.target.relX, e.target.relY);
            netCtx.strokeStyle = e.source.id === activeNode.id ? "rgba(56, 189, 248, 0.75)" : "rgba(245, 158, 11, 0.75)";
            netCtx.lineWidth = 2;
            netCtx.stroke();
          }
        });
      }

      // 4. Nodes
      simNodes.forEach(n => {
        if (!n.visible) return;

        netCtx.beginPath();
        netCtx.arc(n.relX, n.relY, n.radius, 0, Math.PI * 2);

        if (n.highlight) {
          netCtx.fillStyle = "#facc15";
          netCtx.shadowColor = "#facc15";
          netCtx.shadowBlur = 14;
        } else if (activeNode && (n.id === activeNode.id || isConnectedTo(n.id, activeNode.id))) {
          netCtx.fillStyle = n.color;
          netCtx.shadowColor = n.color;
          netCtx.shadowBlur = 10;
        } else {
          netCtx.fillStyle = n.color;
          netCtx.shadowBlur = 0;
        }

        netCtx.fill();
        netCtx.shadowBlur = 0;
        netCtx.lineWidth = n.is_hub ? 2.5 : 1;
        netCtx.strokeStyle = n.is_hub ? "#ffffff" : "rgba(255, 255, 255, 0.4)";
        netCtx.stroke();

        // If zoomed in or is hub, draw text label
        if (netZoom >= 1.1 || n.is_hub || n.highlight || (activeNode && n.id === activeNode.id)) {
          netCtx.fillStyle = "#f1f5f9";
          netCtx.font = `${n.is_hub ? 'bold 11px' : '10px'} sans-serif`;
          netCtx.textAlign = "center";
          netCtx.fillText(n.name, n.relX, n.relY + n.radius + 12);
        }
      });

      netCtx.restore();
    }

    netCanvas.addEventListener("mousedown", e => {
      isNetDragging = true;
      dragStartX = e.clientX - netPanX;
      dragStartY = e.clientY - netPanY;
    });

    window.addEventListener("mouseup", () => {
      isNetDragging = false;
    });

    netCanvas.addEventListener("mousemove", e => {
      if (isNetDragging) {
        netPanX = e.clientX - dragStartX;
        netPanY = e.clientY - dragStartY;
        renderNetwork();
        return;
      }

      const rect = netCanvas.getBoundingClientRect();
      const mouseX = (e.clientX - rect.left - netPanX) / netZoom;
      const mouseY = (e.clientY - rect.top - netPanY) / netZoom;

      let found = null;
      for (let i = simNodes.length - 1; i >= 0; i--) {
        const n = simNodes[i];
        if (!n.visible) continue;
        const dx = mouseX - n.relX;
        const dy = mouseY - n.relY;
        if (dx * dx + dy * dy <= (n.radius + 4) * (n.radius + 4)) {
          found = n;
          break;
        }
      }

      if (found !== hoveredNetNode) {
        hoveredNetNode = found;
        if (found) {
          netTooltip.innerHTML = `
            <div style="font-weight: 800; color: ${found.color}; font-size: 0.88rem;">${escapeHtml(found.name)}</div>
            <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">${escapeHtml(found.type)} &bull; ${escapeHtml(found.domain)}</div>
            <div style="font-size: 0.72rem; color: var(--text-dim); font-family: monospace; margin-top: 3px;">${escapeHtml(found.path || '')}</div>
            <div style="font-size: 0.7rem; color: #a5b4fc; margin-top: 4px;">Click to inspect details &rarr;</div>
          `;
          netTooltip.style.left = `${e.clientX - rect.left}px`;
          netTooltip.style.top = `${e.clientY - rect.top}px`;
          netTooltip.classList.add("visible");
        } else {
          netTooltip.classList.remove("visible");
        }
        renderNetwork();
      } else if (found) {
        netTooltip.style.left = `${e.clientX - rect.left}px`;
        netTooltip.style.top = `${e.clientY - rect.top}px`;
      }
    });

    netCanvas.addEventListener("click", () => {
      if (hoveredNetNode) {
        selectedNetNode = hoveredNetNode;
        inspectEntity(hoveredNetNode.id);
        renderNetwork();
      }
    });

    netCanvas.addEventListener("wheel", e => {
      e.preventDefault();
      const rect = netCanvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
      const newZoom = Math.min(3.5, Math.max(0.2, netZoom * zoomFactor));

      netPanX = mouseX - (mouseX - netPanX) * (newZoom / netZoom);
      netPanY = mouseY - (mouseY - netPanY) * (newZoom / netZoom);
      netZoom = newZoom;

      renderNetwork();
    }, { passive: false });

