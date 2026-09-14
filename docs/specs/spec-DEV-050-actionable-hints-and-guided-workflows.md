# DEV-050: Actionable Architecture Hints & Guided Next-Steps Engine

> **Cycle:** DEV-050  
> **Milestone:** Milestone 17 (Developer Experience & Contextual Intelligence)  
> **Status:** Implemented & Verified  
> **Type:** Feature  

---

## 1. Problem Statement

When developers or team leads run architectural analysis tools (such as `agtoosa graph report`, `agtoosa graph status`, `agtoosa audit`, or `agtoosa refactor dead-code`), they are often presented with dense technical metrics:
- "Grade C (75/100)"
- "36 disconnected nodes"
- "PageRank: 0.0253 on GraphStore"
- "437 God nodes detected"

Without immediate, plain-language guidance, users struggle to answer three critical questions:
1. **What is going on?** (What do these numbers actually represent?)
2. **What does this mean for our system?** (What is the business risk, failure mode, or cost?)
3. **What should I run next?** (What is the exact terminal command or Studio action to resolve or investigate this?)

---

## 2. Capability Requirements

### R-1: Contextual Diagnosis Banner ("What Is Going On")
Every diagnostic command must translate raw graph metrics into a human-readable summary explaining the current health state in plain English.

### R-2: Risk & Impact Translation ("What It Means")
- **Isolated Nodes**: Explain that these represent dead code, zombie helper scripts, or missing entry points that bloat AI agent context.
- **Afferent Hubs (PageRank)**: Explain that high-centrality symbols concentrate architectural gravity, where any change triggers a massive upstream blast radius.
- **Cycles**: Explain the architectural debt of mutual module coupling and tight circular dependencies.

### R-3: Actionable Next-Steps Recommendations ("What To Run Next")
Every report must conclude with a dynamic, prioritized list of exact executable commands tailored to the findings:
- If isolated nodes exist: recommend `agtoosa refactor dead-code --dry-run`.
- If critical hubs exist: recommend `agtoosa graph explain "<symbol>"` and `agtoosa graph impact "<symbol>"`.
- If circular dependencies exist: recommend `agtoosa refactor decouple`.
- For AI agent workflows: recommend `agtoosa query "<symbol>" --budget 1500`.
- For visual exploration: recommend `agtoosa graph view --serve`.

### R-4: Studio UI Guidance Hints
Agtoosa Studio (HTTP server on `:8080`) must display contextual guided tooltips and callout panels in the Drawer and Radar views, showing:
- Current health grade explanation.
- 1-click action buttons matching the CLI next-steps.

---

## 3. Implementation Plan

1. **`agtoosa/graph/metrics.py`**:
   - Enhance `MetricsEngine.format_text()` and `format_markdown()` to append an automated `💡 Actionable Recommendations & Next Steps` section based on computed metrics.
2. **`agtoosa/cli/graph_cmd.py`**:
   - Enhance `cmd_graph_status()` to display immediate guidance on what to run next.
   - Enhance `cmd_audit()` to explain God node gravity and propose immediate refactoring steps.
3. **Documentation & Parity Matrix**:
   - Register DEV-050 in `docs/Master-Plan.md` and `docs/Capability-Matrix.md`.
4. **Verification**:
   - Add unit test coverage in `tests/test_metrics.py` verifying recommendation generation.
