    // 1. Build C4 Architecture Tiers
    const tiersContainer = document.getElementById("c4-tiers");
    const tiers = [
      { id: 1, label: "Tier 1: Entrypoints & Client Interfaces (CLI & AI Protocol)" },
      { id: 2, label: "Tier 2: Core Processing, Polyglot AST Analysis & Specifications" },
      { id: 3, label: "Tier 3: Knowledge Persistence, Architecture Governance & Quality Assurance" }
    ];

    tiers.forEach(t => {
      const section = document.createElement("div");
      section.className = "tier-section";

      const label = document.createElement("div");
      label.className = "tier-label";
      label.textContent = t.label;
      section.appendChild(label);

      const grid = document.createElement("div");
      grid.className = "tier-grid";

      Object.values(subsystemsData)
        .filter(sub => sub.tier_num === t.id)
        .forEach(sub => {
          const card = document.createElement("div");
          card.className = "c4-card";
          card.id = `card-${sub.name.replace(/\\s+/g, '-')}`;
          card.innerHTML = `
            <div class="c4-card-header">
              <div class="c4-card-title">
                <span style="font-size: 1.3rem;">${sub.icon}</span>
                <span>${sub.name}</span>
              </div>
              <span class="badge" style="background: ${sub.color}20; color: ${sub.color};">${sub.total_entities} entities</span>
            </div>
            <p class="c4-card-desc">${sub.desc}</p>
            <div class="c4-metric-chips">
              <div class="metric-chip"><strong>${sub.files_count}</strong> Files</div>
              <div class="metric-chip"><strong>${sub.classes_count}</strong> Classes</div>
              <div class="metric-chip"><strong>${sub.functions_count}</strong> Functions</div>
              ${sub.specs_count > 0 ? `<div class="metric-chip"><strong>${sub.specs_count}</strong> Specs</div>` : ''}
              ${sub.tests_count > 0 ? `<div class="metric-chip"><strong>${sub.tests_count}</strong> Tests</div>` : ''}
            </div>
            <div class="c4-exports-section">
              <div class="c4-exports-title">Key Public Interfaces</div>
              <div class="c4-exports-grid">
                ${sub.key_exports.slice(0, 4).map(exp => `
                  <span class="export-pill" onclick="event.stopPropagation(); inspectEntity('${exp.id}')">${exp.name}</span>
                `).join('')}
                ${sub.key_exports.length > 4 ? `
                  <span class="export-pill more" onclick="event.stopPropagation(); inspectSubsystem('${sub.name}')">+${sub.key_exports.length - 4} more</span>
                ` : ''}
              </div>
            </div>
            <div class="c4-card-footer">
              <div class="c4-io-tag">
                <span>📥 ${sub.inbound_count} in</span> • <span>📤 ${sub.outbound_count} out</span>
              </div>
              <button class="btn-inspect-subsystem" onclick="event.stopPropagation(); inspectSubsystem('${sub.name}')">
                Inspect Subsystem ➔
              </button>
            </div>
          `;
          card.addEventListener("click", () => inspectSubsystem(sub.name));
          grid.appendChild(card);
        });

      section.appendChild(grid);
      tiersContainer.appendChild(section);
    });

