# DEV-056: Executive Studio Progressive Disclosure & Clean Command Center

> **Cycle:** DEV-056  
> **Milestone:** Milestone 19 (v1.0.0 GA Polish & Executive Experience)  
> **Status:** Implemented & Verified  
> **Type:** Feature  

---

## 1. Problem Statement

From an executive, product, and developer adoption perspective, the current Agtoosa Studio Web Command Center suffers from significant visual clutter, cognitive overload, and navigational confusion:
1. **Brand Redundancy ("Studio Studio")**: The header displays `Agtoosa Studio [STUDIO]`, duplicating labels in the logo and badge.
2. **First-Glance Cognitive Overload**: When opening Studio, users are immediately confronted with 5 separate technical perspective tabs, a full-width 4-item KPI strip, a legend, 3 tiers, and 8 large subsystem cards loaded with dense metric chips, counters, and buttons. First-time visitors do not know where to look.
3. **Overlapping Contexts & Infinite Scroll**: The Risk Radar view stacks 6 dense tables and sections (Hubs, Cycles, Decoupler, Dead Code, Spectral Invariants, Forman-Ricci Bottlenecks) onto a single 4,000px scrollable view, repeating metrics already shown in the top ribbon.
4. **Network Graph Collisions**: The Sunflower 2D canvas displays 3,400+ nodes simultaneously with overlapping text labels, producing a noisy blizzard of dots rather than actionable clarity.

---

## 2. Acceptance Criteria

- **AC-1 (Brand & Header Integrity)**: WHEN the Studio web interface loads, the brand section SHALL display clean branding `Agtoosa` with the current version badge (`v0.9.5`), completely eliminating duplicate `Studio STUDIO` labels.
- **AC-2 (Executive Cockpit 3-to-4 Point Progressive Disclosure)**: WHEN first opened, the UI SHALL default to a calm, uncluttered **Overview** cockpit presenting exactly 4 key architecture health indicators (Architecture Grade, Dependency Integrity, Centrality Hubs, AI Token Efficiency) and 3 prominent, single-click navigation portals to deep-dive workspaces.
- **AC-3 (Non-Overlapping Architecture Exploration)**: WHEN navigating to Architecture Blueprint or Network Graph, the layout SHALL provide a clean segmented toggle, and the Network Canvas SHALL suppress overlapping entity labels, rendering labels only on hover, selection, or for top critical hubs.
- **AC-4 (Progressive Risk Radar Sub-Navigation)**: WHEN viewing Risk Radar, the UI SHALL eliminate duplicate top-level metrics and provide a focused 1-click sub-navigation bar (`⚡ Bottlenecks & Hubs`, `🧟 Dead Code Pruning`, `🔄 Cycle Decoupler`, `📐 Spectral Invariants`) ensuring users focus on one refactoring context at a time without infinite scroll.

---

## 3. Tasks & Deliverables

- [x] **Task 56.1**: Update branding and remove duplicate 'Studio STUDIO' in `agtoosa/graph/web/index.html` and `layout.css`.
- [x] **Task 56.2**: Implement `#view-overview` cockpit landing view with 4 core metrics and 3 portal cards in `index.html` and `app.js`.
- [x] **Task 56.3**: Implement Risk Radar sub-navigation to organize Bottlenecks, Dead Code, Decoupler, and Invariants into clean progressive views in `radar_view.js` and `views.css`.
- [x] **Task 56.4**: Refactor Network Graph canvas label rendering to eliminate label collisions in `network_view.js`.
- [x] **Task 56.5**: Update visualizer engine and verify automated tests in `test_visualizer.py`.
