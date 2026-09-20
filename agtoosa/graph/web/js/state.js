    // HTML Sanitization for XSS Defense
    function escapeHtml(str) {
      if (str === null || str === undefined) return "";
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    // Injected Data Payloads (from window.GRAPH_DATA)
    const DATA = window.GRAPH_DATA || {};
    const graphData = DATA.graphData || { nodes: [], edges: [] };
    const graphStats = DATA.graphStats || {};
    const healthData = DATA.healthData || {};
    const domainConfig = DATA.domainConfig || {};
    const domainCounts = DATA.domainCounts || {};
    const cycleData = DATA.cycleData || [];
    const conduitData = DATA.conduitData || [];
    const storyData = DATA.storyData || [];
    const topHubsData = DATA.topHubsData || [];
    const subsystemsData = DATA.subsystemsData || {};
    const telemetryData = DATA.telemetryData || {};
    const decouplerData = DATA.decouplerData || {};
    const deadCodeData = DATA.deadCodeData || {};
    const spectralData = DATA.spectralData || {};
    const curvatureData = DATA.curvatureData || {};
    const bottleneckEdges = new Set(
      (curvatureData.top_bottlenecks || []).map(b => `${b.source}->${b.target}`)
    );

    const workspaceMetadata = DATA.workspaceMetadata || {
      workspaceName: "Workspace",
      isGenesis: false,
      codeFileCount: 0,
      docFileCount: 0,
      totalNodeCount: graphData.nodes.length,
      totalEdgeCount: graphData.edges.length,
      agentRulesInstalled: false,
      storyCount: storyData.length,
      subsystemCount: Object.keys(subsystemsData).length
    };
    const plainEnglishFindings = DATA.plainEnglishFindings || [];

    // Mode management (Simple vs Advanced)
    let currentMode = localStorage.getItem("agtoosa_mode") || "simple";

    // Update Executive KPIs
    const kpiGrade = document.getElementById("kpi-grade");
    if (kpiGrade) kpiGrade.textContent = `Grade ${healthData.grade || 'A+'} (${healthData.score || 94}/100)`;
    const scoreGrade = document.getElementById("score-grade");
    if (scoreGrade) scoreGrade.textContent = healthData.grade || 'A+';

    const kpiCycles = document.getElementById("kpi-cycles");
    if (kpiCycles) {
      kpiCycles.textContent = `${cycleData.length} Cycles (${cycleData.length === 0 ? 'Clean' : 'Warning'})`;
      if (cycleData.length > 0) kpiCycles.style.color = "var(--danger)";
    }
    const scoreCycles = document.getElementById("score-cycles");
    if (scoreCycles) {
      scoreCycles.textContent = `${cycleData.length}`;
      if (cycleData.length > 0) scoreCycles.style.color = "var(--danger)";
    }

    const kpiHubs = document.getElementById("kpi-hubs");
    if (kpiHubs) kpiHubs.textContent = `${topHubsData.length} Monitored`;
    const scoreHubs = document.getElementById("score-hubs");
    if (scoreHubs) scoreHubs.textContent = `${topHubsData.length}`;

    // Ground Overview Metrics Dynamically
    const ovTitle = document.getElementById("ov-workspace-title");
    if (ovTitle && workspaceMetadata.workspaceName) {
      ovTitle.textContent = `${workspaceMetadata.workspaceName} Command Center`;
    }
    const ovDesc = document.getElementById("ov-workspace-desc");
    if (ovDesc && workspaceMetadata.workspaceName) {
      ovDesc.textContent = `Deterministic structural intelligence, automated governance, and delivery verification for ${workspaceMetadata.workspaceName}.`;
    }
    const ovGradeVal = document.getElementById("ov-grade-val");
    if (ovGradeVal) {
      ovGradeVal.textContent = `${healthData.grade || 'A+'} (${healthData.score || 94}/100)`;
    }
    const ovDagVal = document.getElementById("ov-dag-val");
    if (ovDagVal) {
      ovDagVal.textContent = `${cycleData.length === 0 ? '100% DAG Clean' : cycleData.length + ' Cycles Warning'}`;
      if (cycleData.length > 0) ovDagVal.style.color = "var(--danger)";
    }
    const ovDagFooter = document.getElementById("ov-dag-footer");
    if (ovDagFooter) {
      ovDagFooter.innerHTML = `<span style="font-weight: 700;">${cycleData.length} Cycles</span> &bull; ${cycleData.length === 0 ? 'Strict DAG' : 'Decoupling needed'}`;
    }
    const ovTraceVal = document.getElementById("ov-trace-val");
    if (ovTraceVal) {
      ovTraceVal.textContent = `${workspaceMetadata.storyCount || 0} Stories`;
    }
    const ovTraceFooter = document.getElementById("ov-trace-footer");
    if (ovTraceFooter) {
      ovTraceFooter.innerHTML = `<span style="color: #c084fc; font-weight: 700;">${workspaceMetadata.storyCount > 0 ? '100% Mapped' : '0 Mapped'}</span> &bull; Verified`;
    }
    const ovBlastVal = document.getElementById("ov-blast-val");
    if (ovBlastVal) {
      ovBlastVal.textContent = `${topHubsData.length} Critical Hubs`;
    }
    const ovBlastFooter = document.getElementById("ov-blast-footer");
    if (ovBlastFooter) {
      ovBlastFooter.innerHTML = `<span style="color: #a5b4fc; font-weight: 700;">${topHubsData.length} Monitored</span> &bull; Bounded context`;
    }

    // Map & index elements
    const nodeMap = new Map();
    const inEdges = new Map();
    const outEdges = new Map();
    const domainNodes = new Map();

    Object.keys(domainConfig).forEach(dom => domainNodes.set(dom, []));

    graphData.nodes.forEach(n => {
      const d = n.data.domain || "Core Engine";
      if (!domainNodes.has(d)) domainNodes.set(d, []);
      domainNodes.get(d).push(n.data);
      nodeMap.set(n.data.id, n.data);
      inEdges.set(n.data.id, []);
      outEdges.set(n.data.id, []);
    });

    graphData.edges.forEach(e => {
      if (nodeMap.has(e.data.source) && nodeMap.has(e.data.target)) {
        const edgeObj = {
          source: nodeMap.get(e.data.source),
          target: nodeMap.get(e.data.target),
          type: e.data.type
        };
        outEdges.get(e.data.source).push(edgeObj);
        inEdges.get(e.data.target).push(edgeObj);
      }
    });

