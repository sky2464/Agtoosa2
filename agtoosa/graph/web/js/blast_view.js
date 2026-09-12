    // 4. Build Focused Blast Radius Explorer
    const blastSelect = document.getElementById("blast-select");
    const sortedNodes = [...graphData.nodes]
      .filter(n => ['class', 'function', 'file', 'story'].includes(n.data.type))
      .sort((a, b) => (b.data.hub_score || 0) - (a.data.hub_score || 0));

    sortedNodes.forEach(n => {
      const opt = document.createElement("option");
      opt.value = n.data.id;
      opt.textContent = `[${n.data.domain}] ${n.data.type}: ${n.data.name}`;
      blastSelect.appendChild(opt);
    });

    function renderBlastRadius(targetId) {
      const target = nodeMap.get(targetId);
      if (!target) return;

      const inList = inEdges.get(targetId) || [];
      const outList = outEdges.get(targetId) || [];

      document.getElementById("blast-in-count").textContent = inList.length;
      document.getElementById("blast-out-count").textContent = outList.length;

      const isProdWeighted = document.getElementById("blast-prod-toggle").checked;
      const targetTelem = telemetryData[targetId] || null;
      const prodBadge = document.getElementById("blast-prod-badge");

      if (isProdWeighted && targetTelem) {
        prodBadge.style.display = "inline-flex";
        const calls = (targetTelem.call_count || 0).toLocaleString();
        const errRate = ((targetTelem.error_rate || 0) * 100).toFixed(2);
        prodBadge.textContent = `⚡ Live Telemetry: ${calls} calls (${errRate}% err)`;
      } else if (isProdWeighted) {
        prodBadge.style.display = "inline-flex";
        prodBadge.textContent = "⚡ Telemetry Active (Dormant / Low Traffic)";
      } else {
        prodBadge.style.display = "none";
      }

      let telemSummaryHtml = '';
      if (isProdWeighted && targetTelem) {
        const callsStr = (targetTelem.call_count || 0).toLocaleString();
        const latStr = (targetTelem.avg_duration_ms || 0).toFixed(1);
        const errStr = ((targetTelem.error_rate || 0) * 100).toFixed(2);
        const errBg = targetTelem.error_count ? 'rgba(239, 68, 68, 0.25)' : 'rgba(16, 185, 129, 0.25)';
        const errColor = targetTelem.error_count ? '#fca5a5' : '#34d399';
        telemSummaryHtml = '<div style="margin-top: 10px; padding: 10px; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 6px; text-align: left;">' +
          '<div style="font-size: 0.72rem; font-weight: 800; color: #fbbf24; text-transform: uppercase;">🔥 Stage 18 Production Telemetry</div>' +
          '<div style="display: flex; gap: 8px; margin-top: 6px; flex-wrap: wrap;">' +
            '<span class="badge" style="background: rgba(245, 158, 11, 0.25); color: #fbbf24;">' + callsStr + ' calls</span>' +
            '<span class="badge" style="background: rgba(56, 189, 248, 0.2); color: #38bdf8;">' + latStr + 'ms latency</span>' +
            '<span class="badge" style="background: ' + errBg + '; color: ' + errColor + ';">' + errStr + '% err</span>' +
          '</div>' +
        '</div>';
      }

      document.getElementById("blast-target-box").innerHTML = `
        <div class="blast-item center-node">
          <div style="font-size: 0.72rem; text-transform: uppercase; color: #38bdf8; font-weight: 800;">${target.type}</div>
          <div style="font-size: 1.15rem; font-weight: 800; margin: 4px 0;">${target.name}</div>
          <div style="font-size: 0.74rem; color: var(--text-muted); font-family: monospace;">${target.path}</div>
          ${target.docstring ? `<p style="font-size: 0.78rem; color: #cbd5e1; margin-top: 8px; line-height: 1.4;">${target.docstring}</p>` : ''}
          ${telemSummaryHtml}
          <div style="margin-top: 12px; display: flex; gap: 8px;">
            <button class="primary" style="font-size: 0.75rem; padding: 5px 10px;" onclick="copyAiContext('${target.id}')">🤖 Copy AI Context</button>
          </div>
        </div>
      `;

      function formatTelemBadge(nid) {
        if (!isProdWeighted) return '';
        const telem = telemetryData[nid];
        if (!telem) return '';
        const callsStr = (telem.call_count || 0).toLocaleString();
        const latStr = (telem.avg_duration_ms || 0).toFixed(1);
        const errSpan = telem.error_count ? ('<span class="badge" style="background: rgba(239, 68, 68, 0.2); color: #fca5a5;">⚠️ ' + ((telem.error_rate || 0) * 100).toFixed(1) + '% err</span>') : '';
        return '<div style="display: flex; gap: 6px; margin-top: 4px; font-size: 0.68rem;">' +
          '<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">🔥 ' + callsStr + ' calls</span>' +
          errSpan +
          '<span class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8;">⚡ ' + latStr + 'ms</span>' +
        '</div>';
      }

      document.getElementById("blast-ingress-list").innerHTML = inList.map(e => `
        <div class="blast-item" onclick="selectBlastNode('${e.source.id}')">
          <div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">${e.source.domain} &bull; ${e.source.type}</div>
          <div style="font-weight: 700; color: #38bdf8; margin: 2px 0;">${e.source.name}</div>
          <div style="font-size: 0.7rem; color: var(--text-dim); font-family: monospace;">${e.type} ➔</div>
          ${formatTelemBadge(e.source.id)}
        </div>
      `).join('') || '<p style="color: var(--text-muted); font-size: 0.8rem;">No incoming callers.</p>';

      document.getElementById("blast-egress-list").innerHTML = outList.map(e => `
        <div class="blast-item" onclick="selectBlastNode('${e.target.id}')">
          <div style="font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase;">${e.target.domain} &bull; ${e.target.type}</div>
          <div style="font-weight: 700; color: #f59e0b; margin: 2px 0;">${e.target.name}</div>
          <div style="font-size: 0.7rem; color: var(--text-dim); font-family: monospace;">➔ ${e.type}</div>
          ${formatTelemBadge(e.target.id)}
        </div>
      `).join('') || '<p style="color: var(--text-muted); font-size: 0.8rem;">No outgoing dependencies.</p>';
    }

    document.getElementById("blast-prod-toggle").addEventListener("change", () => {
      renderBlastRadius(blastSelect.value);
    });

    window.selectBlastNode = function(nid) {
      blastSelect.value = nid;
      renderBlastRadius(nid);
    };

    blastSelect.addEventListener("change", e => renderBlastRadius(e.target.value));
    if (sortedNodes.length > 0) {
      renderBlastRadius(sortedNodes[0].data.id);
    }

