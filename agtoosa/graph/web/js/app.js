    // Perspective Tab Switching
    function switchView(viewName) {
      document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.view === viewName);
      });

      document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
      if (viewName === "c4") {
        document.getElementById("view-c4").classList.add("active");
      } else if (viewName === "network") {
        document.getElementById("view-network").classList.add("active");
        setTimeout(() => {
          resizeNetwork();
          if (netPanX === 0 && netPanY === 0) resetNetView();
        }, 40);
      } else if (viewName === "radar") {
        document.getElementById("view-radar").classList.add("active");
      } else if (viewName === "pipeline") {
        document.getElementById("view-pipeline").classList.add("active");
      } else if (viewName === "blast") {
        document.getElementById("view-blast").classList.add("active");
      }
    }

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
