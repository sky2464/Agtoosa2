    // Perspective Tab Switching
    function switchView(viewName) {
      document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.view === viewName);
      });

      document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
      if (viewName === "overview") {
        if (workspaceMetadata.isGenesis && !window.cockpitUnlocked) {
          document.getElementById("view-genesis")?.classList.add("active");
        } else {
          document.getElementById("view-overview")?.classList.add("active");
        }
      } else if (viewName === "c4") {
        document.getElementById("view-c4")?.classList.add("active");
      } else if (viewName === "network") {
        document.getElementById("view-network")?.classList.add("active");
        setTimeout(() => {
          resizeNetwork();
          if (netPanX === 0 && netPanY === 0) resetNetView();
        }, 40);
      } else if (viewName === "radar") {
        document.getElementById("view-radar")?.classList.add("active");
      } else if (viewName === "pipeline") {
        document.getElementById("view-pipeline")?.classList.add("active");
      } else if (viewName === "blast") {
        document.getElementById("view-blast")?.classList.add("active");
      }
    }
    window.switchView = switchView;

    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", () => switchView(btn.dataset.view));
    });

    // Search Interaction & Omni-Dropdown
    const searchInput = document.getElementById("search-input");
    const searchDropdown = document.getElementById("search-dropdown");

    function renderSearchResults(q) {
      if (!q) {
        searchDropdown.classList.remove("show");
        searchDropdown.innerHTML = "";
        return;
      }
      const matches = graphData.nodes
        .filter(n => n.data.name.toLowerCase().includes(q) || (n.data.path && n.data.path.toLowerCase().includes(q)))
        .slice(0, 8);

      if (matches.length === 0) {
        searchDropdown.innerHTML = '<div style="padding: 12px; color: var(--text-muted); font-size: 0.78rem; text-align: center;">No matching symbols or files found.</div>';
        searchDropdown.classList.add("show");
        return;
      }

      searchDropdown.innerHTML = matches.map(m => `
        <div class="search-item" onclick="selectSearchItem('${m.data.id}')">
          <div class="search-item-left">
            <span class="search-item-name">${escapeHtml(m.data.name)}</span>
            <span class="search-item-path">${escapeHtml(m.data.path || '')}${m.data.start_line ? ':L' + m.data.start_line : ''}</span>
          </div>
          <span class="badge" style="background: ${m.data.color || '#38bdf8'}25; color: ${m.data.color || '#38bdf8'}; font-size: 0.65rem;">${m.data.type}</span>
        </div>
      `).join('');
      searchDropdown.classList.add("show");
    }

    window.selectSearchItem = function(id) {
      searchDropdown.classList.remove("show");
      searchInput.value = "";
      inspectEntity(id);
    };

    searchInput.addEventListener("input", e => {
      renderSearchResults(e.target.value.toLowerCase().trim());
    });

    document.addEventListener("click", e => {
      if (!e.target.closest(".search-wrapper")) {
        searchDropdown.classList.remove("show");
      }
    });

    window.addEventListener("keydown", e => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
      if (e.key === "Escape") {
        searchDropdown.classList.remove("show");
        sidebar.classList.remove("active");
        welcomeModal.classList.remove("show");
      }
    });

    // Header Export Button
    const btnExportHdr = document.getElementById("btn-export-hdr");
    if (btnExportHdr) {
      btnExportHdr.addEventListener("click", () => {
        if (currentSelectedEntity) {
          copyAiContext(currentSelectedEntity.id);
        } else {
          showToast("💡 Click any subsystem or symbol to inspect and export its AI Context Pack!");
        }
      });
    }

    // Guide Modal
    const welcomeModal = document.getElementById("welcome-modal");
    document.getElementById("btn-guide").addEventListener("click", () => welcomeModal.classList.add("show"));
    document.getElementById("modal-close").addEventListener("click", () => welcomeModal.classList.remove("show"));
    document.getElementById("btn-explore-studio").addEventListener("click", () => welcomeModal.classList.remove("show"));
    welcomeModal.addEventListener("click", e => {
      if (e.target === welcomeModal) welcomeModal.classList.remove("show");
    });

    // Mode Switcher (DEV-058)
    const btnModeToggle = document.getElementById("btn-mode-toggle");
    const modeIcon = document.getElementById("mode-icon");
    const modeText = document.getElementById("mode-text");

    function applyMode(mode) {
      currentMode = mode;
      localStorage.setItem("agtoosa_mode", mode);
      if (mode === "advanced") {
        document.body.classList.add("advanced-mode");
        if (modeIcon) modeIcon.textContent = "⚡";
        if (modeText) modeText.textContent = "Advanced Mode";
      } else {
        document.body.classList.remove("advanced-mode");
        if (modeIcon) modeIcon.textContent = "🌿";
        if (modeText) modeText.textContent = "Simple Mode";
      }
    }

    if (btnModeToggle) {
      applyMode(currentMode);
      btnModeToggle.addEventListener("click", () => {
        const nextMode = (currentMode === "simple") ? "advanced" : "simple";
        applyMode(nextMode);
        showToast(nextMode === "advanced" ? "⚡ Advanced Architect Mode enabled" : "🌿 Simple Developer Mode enabled");
      });
    }

    // Dynamic Findings Renderer (DEV-058)
    function renderFindings(containerId, findings) {
      const container = document.getElementById(containerId);
      if (!container) return;

      if (!findings || findings.length === 0) {
        container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 12px; text-align: center;">✅ No active warnings. Architecture health is optimal.</div>`;
        return;
      }

      container.innerHTML = findings.map(f => {
        const sevClass = f.severity ? `severity-${f.severity}` : 'severity-info';
        const actionBtn = f.action_label ? `
          <div class="finding-action-col">
            <button class="finding-action-btn" type="button" onclick="handleFindingAction('${escapeHtml(f.id)}')">
              ${escapeHtml(f.action_label)}
            </button>
            ${f.action_hint ? `<span class="finding-hint">${escapeHtml(f.action_hint)}</span>` : ''}
          </div>
        ` : '';

        return `
          <div class="finding-card ${sevClass}" id="finding-card-${escapeHtml(f.id)}">
            <div class="finding-card-content">
              <div class="finding-title-row">
                <span style="font-size: 1.1rem;">${f.icon || '📌'}</span>
                <span class="finding-title">${escapeHtml(f.title)}</span>
              </div>
              <div class="finding-desc">${escapeHtml(f.description)}</div>
            </div>
            ${actionBtn}
          </div>
        `;
      }).join('');
    }

    window.handleFindingAction = async function(findingId) {
      const finding = plainEnglishFindings.find(f => f.id === findingId);
      if (!finding) return;

      if (finding.action_endpoint) {
        try {
          const res = await fetch(finding.action_endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ with_git_hooks: true })
          });
          const data = await res.json();
          showToast("🤖 AI Agent instructions successfully generated in AGENTS.md & CLAUDE.md!");
          const card = document.getElementById(`finding-card-${findingId}`);
          if (card) {
            card.className = "finding-card severity-success";
            const btn = card.querySelector(".finding-action-btn");
            if (btn) {
              btn.textContent = "✅ Enforced";
              btn.disabled = true;
            }
          }
        } catch (err) {
          showToast("⚠️ Could not contact server: " + err.message);
        }
      } else if (finding.action_command) {
        navigator.clipboard?.writeText(finding.action_command);
        showToast(`📋 Copied command: ${finding.action_command}`);
      }
    };

    // 1-Click Enforce AI Agents Button Handler
    const btnEnforceAgents = document.getElementById("btn-enforce-agents");
    if (btnEnforceAgents) {
      btnEnforceAgents.addEventListener("click", async () => {
        try {
          const res = await fetch("/api/agent/enforce", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ with_git_hooks: true })
          });
          const data = await res.json();
          showToast("🤖 AI Agent rules installed into AGENTS.md & CLAUDE.md!");
          btnEnforceAgents.innerHTML = "<span>✅</span> AI Agents Enforced (AGENTS.md &amp; CLAUDE.md)";
          btnEnforceAgents.style.background = "#10b981";
        } catch (e) {
          showToast("⚠️ Failed to enforce rules: " + e.message);
        }
      });
    }

    // Genesis Preview Cockpit Button
    const btnPreviewCockpit = document.getElementById("btn-preview-cockpit");
    if (btnPreviewCockpit) {
      btnPreviewCockpit.addEventListener("click", () => {
        window.cockpitUnlocked = true;
        document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
        document.getElementById("view-overview")?.classList.add("active");
        showToast("👁️ Viewing Full Architecture Cockpit");
      });
    }

    // Global copy button handler for code snippets
    document.addEventListener("click", (e) => {
      const copyBtn = e.target.closest(".btn-copy-cmd");
      if (copyBtn) {
        const cmd = copyBtn.getAttribute("data-copy");
        if (cmd) {
          navigator.clipboard?.writeText(cmd);
          const toastFn = window.showToast || showToast;
          if (toastFn) toastFn(`📋 Copied: ${cmd}`);
        }
      }
    });

    // Initial View Setup (Genesis vs Grown Codebase)
    const genesisWsName = document.getElementById("genesis-workspace-name");
    if (genesisWsName) genesisWsName.textContent = workspaceMetadata.workspaceName || "Your Workspace";
    const genesisBadgeText = document.getElementById("genesis-badge-text");
    if (genesisBadgeText) {
      genesisBadgeText.textContent = `🌱 Project Genesis Stage: ${workspaceMetadata.docFileCount || 0} Document(s) • Ready for Code`;
    }

    // Conversational Copilot Advice Box Setup
    function setupCopilotAdvice() {
      const wsName = workspaceMetadata.workspaceName || "this project";
      const docCount = workspaceMetadata.docFileCount || 0;
      const codeCount = workspaceMetadata.codeFileCount || 0;
      const isEnforced = workspaceMetadata.agentRulesInstalled;
      const cycles = cycleData.length || 0;

      // 1. Genesis Copilot Setup
      const genesisMsg = document.getElementById("copilot-message");
      const genesisIndicator = document.getElementById("copilot-step-indicator");
      const genesisActions = document.getElementById("copilot-quick-actions");

      if (genesisMsg) {
        if (!isEnforced) {
          if (genesisIndicator) genesisIndicator.textContent = "Step 1 of 3: Guard AI Agents";
          genesisMsg.innerHTML = `
            👋 Welcome to <strong>${escapeHtml(wsName)}</strong>! We found <strong>${docCount} design document(s)</strong> and 0 code files.<br>
            Before you start writing code, <strong>enforce Agtoosa guardrails on your AI agents</strong> (Antigravity, Claude Code, Cursor, Copilot). This tells them to query subgraphs before making changes and verify zero circular imports.
          `;
          if (genesisActions) {
            genesisActions.innerHTML = `
              <button class="btn-copy-cmd primary" data-copy="agtoosa agent-init" type="button">📋 Copy: agtoosa agent-init</button>
              <button class="btn-copy-cmd" data-copy="touch main.py &amp;&amp; agtoosa graph build" type="button">📋 Copy: touch main.py &amp;&amp; agtoosa graph build</button>
            `;
          }
        } else {
          if (genesisIndicator) genesisIndicator.textContent = "Step 2 of 3: Start Developing";
          genesisMsg.innerHTML = `
            🎉 Great job! AI agent guardrails (<code>AGENTS.md</code> &amp; <code>CLAUDE.md</code>) are active in <strong>${escapeHtml(wsName)}</strong>.<br>
            <strong>Your next step:</strong> Start writing code! Create your first source file (e.g. <code>main.py</code> or <code>index.ts</code>) or prompt your AI agent to implement your first feature. Then run <code>agtoosa graph build</code> to see your architecture live.
          `;
          if (genesisActions) {
            genesisActions.innerHTML = `
              <button class="btn-copy-cmd primary" data-copy="touch main.py &amp;&amp; agtoosa graph build" type="button">📋 Copy: touch main.py &amp;&amp; agtoosa graph build</button>
              <button class="btn-copy-cmd" data-copy="agtoosa review" type="button">📋 Copy: agtoosa review</button>
            `;
          }
        }
      }

      // 2. Overview / Active Codebase Copilot Setup
      const ovMsg = document.getElementById("overview-copilot-message");
      const ovIndicator = document.getElementById("overview-copilot-step-indicator");
      const ovActions = document.getElementById("overview-copilot-quick-actions");

      if (ovMsg) {
        if (cycles > 0) {
          if (ovIndicator) {
            ovIndicator.textContent = `⚠️ Warning: ${cycles} Cycle(s)`;
            ovIndicator.style.background = "rgba(239, 68, 68, 0.15)";
            ovIndicator.style.borderColor = "rgba(239, 68, 68, 0.35)";
            ovIndicator.style.color = "#f87171";
          }
          ovMsg.innerHTML = `
            🚨 Agtoosa detected <strong>${cycles} circular dependency loop(s)</strong> in <strong>${escapeHtml(wsName)}</strong>.<br>
            Circular dependencies create fragile coupling and bloat AI agent context windows. <strong>Recommended next step:</strong> Decouple cycles or run an architecture review to inspect the affected call paths.
          `;
          if (ovActions) {
            ovActions.innerHTML = `
              <button class="btn-copy-cmd primary" data-copy="agtoosa refactor decouple" type="button">📋 Copy: agtoosa refactor decouple</button>
              <button class="btn-copy-cmd" data-copy="agtoosa review" type="button">📋 Copy: agtoosa review</button>
              <button class="btn-copy-cmd" data-copy="agtoosa status" type="button">📋 Copy: agtoosa status</button>
            `;
          }
        } else {
          if (ovIndicator) {
            ovIndicator.textContent = `✅ Strict DAG Architecture (${healthData.grade || 'Grade A+'})`;
          }
          ovMsg.innerHTML = `
            🏛️ Agtoosa is actively monitoring <strong>${codeCount} code file(s)</strong> and <strong>${workspaceMetadata.totalNodeCount || 0} symbols</strong> in <strong>${escapeHtml(wsName)}</strong> with <strong>zero circular dependencies</strong>.<br>
            <strong>Your continuous engineering loop:</strong><br>
            • <strong>Develop:</strong> Query bounded context with <code>agtoosa query "&lt;feature&gt;"</code> before prompting AI coding agents.<br>
            • <strong>Update:</strong> Sync your AST knowledge graph with <code>agtoosa graph build</code> when files change.<br>
            • <strong>Verify:</strong> Run <code>agtoosa review</code> before committing to enforce layer boundaries.
          `;
          if (ovActions) {
            ovActions.innerHTML = `
              <button class="btn-copy-cmd primary" data-copy="agtoosa review" type="button">📋 Copy: agtoosa review</button>
              <button class="btn-copy-cmd" data-copy="agtoosa graph build" type="button">📋 Copy: agtoosa graph build</button>
              <button class="btn-copy-cmd" data-copy="agtoosa status" type="button">📋 Copy: agtoosa status</button>
              <button class="btn-copy-cmd" data-copy='agtoosa query "service"' type="button">📋 Copy: agtoosa query "service"</button>
            `;
          }
        }
      }
    }

    setupCopilotAdvice();
    renderFindings("genesis-findings-list", plainEnglishFindings);
    renderFindings("overview-findings-list", plainEnglishFindings);

    // Explicitly initialize and activate default landing view
    switchView("overview");

