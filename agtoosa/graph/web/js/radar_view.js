    // 2. Build Governance & Risk Radar Tables
    const hubsBody = document.getElementById("table-hubs-body");
    topHubsData.slice(0, 10).forEach((h, idx) => {
      const tr = document.createElement("tr");
      tr.style.cursor = "pointer";
      tr.innerHTML = `
        <td><strong>#${idx + 1}</strong></td>
        <td><span style="color: #38bdf8; font-weight: 700; font-family: monospace;">${h.name}</span></td>
        <td><span style="color: var(--text-muted);">${nodeMap.get(h.id)?.domain || 'Core Engine'}</span></td>
        <td><span class="badge" style="background: rgba(255, 255, 255, 0.08);">${h.type}</span></td>
        <td><strong>${h.score}</strong></td>
        <td><span class="badge" style="background: ${idx < 3 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)'}; color: ${idx < 3 ? '#f87171' : '#fbbf24'};">${idx < 3 ? 'Critical Core Hub' : 'High Centrality'}</span></td>
      `;
      tr.addEventListener("click", () => inspectEntity(h.id));
      hubsBody.appendChild(tr);
    });

    const cyclesContent = document.getElementById("cycles-audit-content");
    if (cycleData.length === 0) {
      cyclesContent.innerHTML = `
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 16px; border-radius: 8px; color: #34d399; font-size: 0.86rem; display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 1.2rem;">✅</span>
          <div>
            <strong>Zero Circular Dependencies Detected.</strong><br>
            <span style="color: var(--text-muted); font-size: 0.78rem;">The entire Agtoosa2 dependency graph is strictly acyclic across all modules and functions.</span>
          </div>
        </div>
      `;
    } else {
      cyclesContent.innerHTML = cycleData.map((c, i) => `
        <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); padding: 12px; border-radius: 8px; font-size: 0.82rem; margin-bottom: 8px;">
          <strong>Cycle #${i + 1}:</strong> ${c.map(x => x.name).join(" ➔ ")}
        </div>
      `).join('');
    }

    // Stage 19: Cycle Decoupler Blueprints
    const decouplerContent = document.getElementById("decoupler-content");
    if (decouplerData && decouplerData.strategies && decouplerData.strategies.length > 0) {
      decouplerContent.innerHTML = decouplerData.strategies.map((strat, idx) => `
        <div class="decoupler-card">
          <div class="decoupler-card-header">
            <div style="font-weight: 800; font-size: 0.95rem; color: #f1f5f9; display: flex; align-items: center; gap: 8px;">
              <span>🪓 Decoupling Strategy #${idx + 1}:</span>
              <span style="font-family: monospace; color: #38bdf8;">${escapeHtml(strat.proposed_interface_name)}</span>
            </div>
            <span class="decoupler-strategy-badge">${escapeHtml(strat.strategy_type)}</span>
          </div>
          <p style="font-size: 0.8rem; color: #cbd5e1; line-height: 1.45;">${escapeHtml(strat.rationale)}</p>
          <div style="margin-top: 8px; font-size: 0.76rem; color: var(--text-dim);">
            <strong>Recommended Decoupling Cut:</strong>
            <span style="font-family: monospace; color: #f87171;">${escapeHtml(strat.cut_edge[0])}</span> ➔
            <span style="font-family: monospace; color: #34d399;">${escapeHtml(strat.cut_edge[1])}</span>
          </div>
          ${strat.generated_code_stub ? `
            <div style="margin-top: 8px; font-size: 0.72rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Generated Code Blueprint Stub:</div>
            <pre class="code-stub-block"><code>${escapeHtml(strat.generated_code_stub)}</code></pre>
          ` : ''}
          <div style="margin-top: 8px; font-size: 0.72rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Refactoring Steps:</div>
          <div class="decoupler-steps">
            ${strat.refactor_steps.map((step, sIdx) => `
              <div class="step-item">
                <span class="step-num">${sIdx + 1}</span>
                <span>${escapeHtml(step)}</span>
              </div>
            `).join('')}
          </div>
        </div>
      `).join('');
    } else {
      decouplerContent.innerHTML = `
        <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); padding: 14px; border-radius: 8px; color: #34d399; font-size: 0.84rem; display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 1.2rem;">✨</span>
          <div>
            <strong>Architecture is Perfectly Acyclic.</strong><br>
            <span style="color: var(--text-muted); font-size: 0.76rem;">No feedback loops detected. The cycle decoupler engine stands active to synthesize dependency inversion interfaces if loops are introduced.</span>
          </div>
        </div>
      `;
    }

    // Stage 20: Dead Code & Zombie Symbol Pruning
    const deadCodePills = document.getElementById("dead-code-summary-pills");
    const deadCodeBody = document.getElementById("table-dead-code-body");
    deadCodePills.innerHTML = `
      <div class="metric-chip"><strong>${deadCodeData.total_symbols_analyzed || graphData.nodes.length}</strong> Symbols Analyzed</div>
      <div class="metric-chip"><strong style="color: ${deadCodeData.total_dead_candidates > 0 ? '#f59e0b' : '#34d399'};">${deadCodeData.total_dead_candidates || 0}</strong> Unreachable Candidates</div>
      <div class="metric-chip"><strong>~${deadCodeData.total_estimated_dead_lines || 0}</strong> Lines Recoverable</div>
    `;

    if (deadCodeData.zombies && deadCodeData.zombies.length > 0) {
      deadCodeBody.innerHTML = deadCodeData.zombies.map(z => `
        <tr id="dead-row-${escapeHtml(z.node_id)}" style="cursor: pointer;" onclick="inspectEntity('${escapeHtml(z.node_id)}')">
          <td><span class="confidence-pill ${escapeHtml(z.confidence)}">${escapeHtml(z.confidence)}</span></td>
          <td><span style="color: #38bdf8; font-weight: 700; font-family: monospace;">${escapeHtml(z.name)}</span></td>
          <td><span style="color: var(--text-muted); font-family: monospace; font-size: 0.74rem;">${escapeHtml(z.path)}:L${z.start_line}-${z.end_line}</span></td>
          <td><span style="font-size: 0.76rem; color: #cbd5e1;">${escapeHtml(z.reason)}</span></td>
          <td><strong>${z.estimated_lines}</strong></td>
          <td>
            ${z.safe_to_delete ? `
              <button class="prune-btn" title="Execute safe dead-code pruning" onclick="event.stopPropagation(); triggerStudioPrune('${escapeHtml(z.node_id)}', '${escapeHtml(z.path)}', '${escapeHtml(z.name)}', ${z.start_line}, ${z.end_line})">
                ✂️ Safe Prune
              </button>
            ` : `
              <span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24;">Needs Review</span>
            `}
          </td>
        </tr>
      `).join('');
    } else {
      deadCodeBody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: #34d399; padding: 18px; font-size: 0.82rem;">
            ✅ Zero Dead Code Detected — All symbols have active call edges or are documented entrypoints.
          </td>
        </tr>
      `;
    }

    // Stage 52 & 54: Spectral & Differential Geometry Invariants
    const spectralPills = document.getElementById("spectral-summary-pills");
    const bottlenecksBody = document.getElementById("table-bottlenecks-body");

    if (spectralPills) {
      const fiedlerConn = spectralData.algebraic_connectivity !== undefined ? Number(spectralData.algebraic_connectivity).toFixed(4) : "N/A";
      const specRadius = spectralData.spectral_radius !== undefined ? Number(spectralData.spectral_radius).toFixed(3) : "N/A";
      const epThresh = spectralData.epidemic_threshold !== undefined ? Number(spectralData.epidemic_threshold).toFixed(4) : "N/A";
      const entropy = spectralData.von_neumann_entropy !== undefined ? Number(spectralData.von_neumann_entropy).toFixed(3) : "N/A";
      const avgCurv = curvatureData.average_curvature !== undefined ? Number(curvatureData.average_curvature).toFixed(3) : "N/A";
      const bottleneckCount = curvatureData.bottleneck_count || (curvatureData.top_bottlenecks || []).length || 0;

      spectralPills.innerHTML = `
        <div class="metric-chip"><strong>&lambda;₂ = ${fiedlerConn}</strong> Algebraic Connectivity</div>
        <div class="metric-chip"><strong>&lambda;₁ = ${specRadius}</strong> Spectral Radius (&tau;<sub>c</sub> = ${epThresh})</div>
        <div class="metric-chip"><strong>S<sub>vN</sub> = ${entropy}</strong> Graph Entropy</div>
        <div class="metric-chip"><strong style="color: ${Number(avgCurv) < 0 ? '#fb7185' : '#34d399'};">Ric<sub>avg</sub> = ${avgCurv}</strong> Forman-Ricci</div>
        <div class="metric-chip"><strong style="color: ${bottleneckCount > 0 ? '#f59e0b' : '#34d399'};">${bottleneckCount}</strong> Hyperbolic Choke Points</div>
      `;
    }

    if (bottlenecksBody) {
      const bottlenecks = curvatureData.top_bottlenecks || [];
      if (bottlenecks.length > 0) {
        bottlenecksBody.innerHTML = bottlenecks.slice(0, 15).map((b, idx) => {
          const curvVal = Number(b.curvature).toFixed(2);
          const isCritical = Number(b.curvature) <= -5.0;
          return `
            <tr style="cursor: pointer;" onclick="inspectEntity('${escapeHtml(b.source)}')">
              <td><strong>#${idx + 1}</strong></td>
              <td><span style="color: #38bdf8; font-weight: 700; font-family: monospace;">${escapeHtml(b.source)}</span></td>
              <td><span style="color: #818cf8; font-weight: 700; font-family: monospace;">${escapeHtml(b.target)}</span></td>
              <td><span class="bottleneck-pill ${isCritical ? 'critical' : 'warning'}">Ric = ${curvVal}</span></td>
              <td><span class="badge" style="background: ${isCritical ? 'rgba(244, 63, 94, 0.15)' : 'rgba(245, 158, 11, 0.15)'}; color: ${isCritical ? '#fb7185' : '#fbbf24'};">${isCritical ? 'Critical Choke Point' : 'Module Bridge'}</span></td>
              <td>
                <button class="prune-btn" style="background: rgba(56, 189, 248, 0.15); border-color: rgba(56, 189, 248, 0.4); color: #38bdf8;" onclick="event.stopPropagation(); inspectEntity('${escapeHtml(b.source)}')">
                  🔍 Inspect
                </button>
              </td>
            </tr>
          `;
        }).join('');
      } else {
        bottlenecksBody.innerHTML = `
          <tr>
            <td colspan="6" style="text-align: center; color: #34d399; padding: 18px; font-size: 0.82rem;">
              ✨ Zero Fragile Choke Points Detected — Codebase has uniform positive curvature distribution.
            </td>
          </tr>
        `;
      }
    }

    // Two-Way Interactive Studio Actions (Stage 23)
    window.triggerStudioPrune = async function(nodeId, path, name, startLine, endLine) {
      if (!confirm(`Execute safe dead-code pruning for '${name}' in ${path}:L${startLine}-${endLine}?`)) return;
      try {
        const res = await fetch('/api/refactor/prune', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ node_id: nodeId, path: path, name: name, start_line: startLine, end_line: endLine })
        });
        if (res.ok) {
          const data = await res.json();
          showToast(`✂️ Successfully pruned '${name}'! Backup saved: ${data.backup_id}`);
          const row = document.getElementById(`dead-row-${nodeId}`);
          if (row) {
            row.style.opacity = '0.35';
            row.style.textDecoration = 'line-through';
          }
        } else {
          showToast(`Run: agtoosa refactor dead-code --apply`);
        }
      } catch (err) {
        showToast(`Offline mode: run 'agtoosa refactor dead-code --apply' in terminal.`);
      }
    };

    window.triggerStudioDecouple = async function(interfaceName, codeStubEncoded) {
      const codeStub = decodeURIComponent(codeStubEncoded);
      try {
        const res = await fetch('/api/refactor/decouple', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ proposed_interface_name: interfaceName, generated_code_stub: codeStub })
        });
        if (res.ok) {
          const data = await res.json();
          showToast(`💡 Generated interface '${interfaceName}'! Backup: ${data.backup_id}`);
        } else {
          showToast(`Run: agtoosa refactor decouple --apply`);
        }
      } catch (err) {
        showToast(`Offline mode: run 'agtoosa refactor decouple --apply' in terminal.`);
      }
    };

