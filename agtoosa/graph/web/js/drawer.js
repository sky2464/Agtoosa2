    // Slide-Over Drawer Inspection Logic
    const sidebar = document.getElementById("sidebar");
    let currentSelectedEntity = null;

    window.inspectEntity = function(nid) {
      const n = nodeMap.get(nid);
      if (!n) return;
      currentSelectedEntity = n;
      sidebar.classList.add("active");

      document.getElementById("side-badge").textContent = n.type;
      document.getElementById("side-badge").style.background = n.color;
      document.getElementById("side-badge").style.color = "#070a13";
      document.getElementById("side-domain").textContent = n.domain;
      document.getElementById("side-name").textContent = n.name;
      const lineStr = n.start_line ? `:L${n.start_line}` : '';
      document.getElementById("side-path").textContent = `${n.path}${lineStr}`;

      const docGroup = document.getElementById("group-doc");
      if (n.docstring) {
        docGroup.style.display = "block";
        document.getElementById("side-doc").textContent = n.docstring;
      } else {
        docGroup.style.display = "none";
      }

      document.getElementById("group-subsystem-items").style.display = "none";

      const inList = inEdges.get(n.id) || [];
      document.getElementById("side-in-count").textContent = inList.length;
      document.getElementById("side-in-list").innerHTML = inList.map(e => `
        <div class="conn-item" onclick="inspectEntity('${e.source.id}')">
          <span style="color: #38bdf8; font-family: monospace;">${e.source.name}</span>
          <span style="color: var(--text-muted); font-size: 0.72rem;">${e.type}</span>
        </div>
      `).join('') || '<p style="color: var(--text-muted); font-size: 0.8rem;">No incoming callers</p>';

      const outList = outEdges.get(n.id) || [];
      document.getElementById("side-out-count").textContent = outList.length;
      document.getElementById("side-out-list").innerHTML = outList.map(e => `
        <div class="conn-item" onclick="inspectEntity('${e.target.id}')">
          <span style="color: #f59e0b; font-family: monospace;">${e.target.name}</span>
          <span style="color: var(--text-muted); font-size: 0.72rem;">${e.type}</span>
        </div>
      `).join('') || '<p style="color: var(--text-muted); font-size: 0.8rem;">No outgoing dependencies</p>';
    };

    window.inspectSubsystem = function(domName) {
      const sub = subsystemsData[domName];
      if (!sub) return;
      currentSelectedEntity = {
        name: sub.name,
        type: "Subsystem",
        domain: sub.tier,
        path: `agtoosa/${sub.name.toLowerCase().split(' ')[0]}`,
        docstring: sub.desc,
        id: `domain:${sub.name}`
      };

      sidebar.classList.add("active");
      document.getElementById("side-badge").textContent = "Subsystem";
      document.getElementById("side-badge").style.background = sub.color;
      document.getElementById("side-badge").style.color = "#070a13";
      document.getElementById("side-domain").textContent = sub.tier;
      document.getElementById("side-name").textContent = sub.name;
      document.getElementById("side-path").textContent = `${sub.total_entities} entities (${sub.files_count} files)`;

      document.getElementById("group-doc").style.display = "block";
      document.getElementById("side-doc").textContent = sub.desc;

      // Render contained symbols
      const membersGroup = document.getElementById("group-subsystem-items");
      membersGroup.style.display = "block";
      const nodesInDom = domainNodes.get(domName) || [];
      document.getElementById("subsystem-items-count").textContent = nodesInDom.length;
      document.getElementById("subsystem-members-container").innerHTML = nodesInDom.slice(0, 40).map(n => `
        <div class="conn-item" onclick="inspectEntity('${n.id}')">
          <span style="color: #cbd5e1; font-family: monospace;">${n.name}</span>
          <span class="badge" style="background: rgba(255, 255, 255, 0.06); font-size: 0.68rem;">${n.type}</span>
        </div>
      `).join('');

      // Cross domain connections
      const inConduits = conduitData.filter(c => c.target === domName);
      document.getElementById("side-in-count").textContent = inConduits.length;
      document.getElementById("side-in-list").innerHTML = inConduits.map(c => `
        <div class="conn-item" onclick="inspectSubsystem('${c.source}')">
          <span style="color: #38bdf8; font-weight: 700;">${c.source}</span>
          <span class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8;">${c.count} calls</span>
        </div>
      `).join('') || '<p style="color: var(--text-muted); font-size: 0.8rem;">No incoming cross-domain calls</p>';

      const outConduits = conduitData.filter(c => c.source === domName);
      document.getElementById("side-out-count").textContent = outConduits.length;
      document.getElementById("side-out-list").innerHTML = outConduits.map(c => `
        <div class="conn-item" onclick="inspectSubsystem('${c.target}')">
          <span style="color: #f59e0b; font-weight: 700;">${c.target}</span>
          <span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b;">${c.count} calls</span>
        </div>
      `).join('') || '<p style="color: var(--text-muted); font-size: 0.8rem;">No outgoing cross-domain calls</p>';
    };

    document.getElementById("side-close").addEventListener("click", () => {
      sidebar.classList.remove("active");
    });

    // AI Context Pack Exporter
    function showToast(msg) {
      const toast = document.getElementById("toast");
      if (!toast) return;
      toast.textContent = msg;
      toast.classList.add("show");
      setTimeout(() => toast.classList.remove("show"), 2800);
    }
    window.showToast = showToast;

    window.copyAiContext = function(targetId) {
      const n = nodeMap.get(targetId) || currentSelectedEntity;
      if (!n) return;

      const inList = inEdges.get(n.id) || [];
      const outList = outEdges.get(n.id) || [];

      const q = String.fromCharCode(96);
      let pack = "# Agtoosa Bounded Context Pack: " + n.name + " (" + n.type + ")\\n\\n";
      pack += "- **File Location**: " + q + n.path + (n.start_line ? ':L' + n.start_line : '') + q + "\\n";
      pack += "- **Subsystem**: " + n.domain + "\\n";
      if (n.docstring) {
        pack += "- **Architectural Intent**: " + n.docstring + "\\n";
      }
      pack += "\\n## Ingress (Incoming Callers - " + inList.length + ")\\n";
      inList.slice(0, 10).forEach(e => {
        pack += "- " + q + e.source.name + q + " (" + e.source.type + " in " + q + e.source.path + q + ") via " + q + e.type + q + "\\n";
      });
      pack += "\\n## Egress (Outgoing Dependencies - " + outList.length + ")\\n";
      outList.slice(0, 10).forEach(e => {
        pack += "- " + q + e.target.name + q + " (" + e.target.type + " in " + q + e.target.path + q + ") via " + q + e.type + q + "\\n";
      });

      navigator.clipboard.writeText(pack).then(() => {
        showToast(`📋 Copied bounded AI Context Pack for ${n.name}! Ready for Claude/Cursor.`);
      });
    };

    document.getElementById("btn-copy-ai").addEventListener("click", () => {
      if (currentSelectedEntity) copyAiContext(currentSelectedEntity.id);
    });

    document.getElementById("btn-open-blast").addEventListener("click", () => {
      if (currentSelectedEntity) {
        switchView("blast");
        selectBlastNode(currentSelectedEntity.id);
      }
    });

    document.getElementById("btn-copy-path").addEventListener("click", () => {
      if (currentSelectedEntity?.path) {
        navigator.clipboard.writeText(currentSelectedEntity.path);
        showToast(`📋 Copied path: ${currentSelectedEntity.path}`);
      }
    });

