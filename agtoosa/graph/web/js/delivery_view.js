    // 3. Build Delivery Assurance Board
    const deliveryContainer = document.getElementById("delivery-container");
    storyData.forEach(s => {
      const card = document.createElement("div");
      card.className = "story-card";
      card.innerHTML = `
        <div class="story-card-left">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="badge" style="background: rgba(168, 85, 247, 0.2); color: #c084fc;">Story DEV</span>
            <h3 style="font-size: 1.05rem; font-weight: 800;">${s.name}</h3>
          </div>
          <p style="font-size: 0.78rem; color: var(--text-muted); font-family: monospace;">${s.path}</p>
        </div>
        <div class="story-card-right">
          <div class="stat-badge">
            <span style="font-weight: 800; color: #38bdf8;">${s.criteria_count}</span>
            <span style="font-size: 0.68rem; color: var(--text-muted);">Criteria</span>
          </div>
          <div class="stat-badge">
            <span style="font-weight: 800; color: #10b981;">${s.tasks_count}</span>
            <span style="font-size: 0.68rem; color: var(--text-muted);">Tasks</span>
          </div>
          <span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 0.8rem; padding: 6px 12px;">✅ 100% Verified</span>
        </div>
      `;
      deliveryContainer.appendChild(card);
    });

