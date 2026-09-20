# DEV-058: Adaptive Onboarding, Genesis Dashboard & Agentic AI Workflow Enforcement

> **Cycle:** DEV-058  
> **Milestone:** Milestone 19 (v1.0.0 GA Polish & Executive Experience)  
> **Status:** Completed  
> **Type:** Feature & UX Architecture  

---

## 1. Problem Statement

1. **Early-Stage Cognitive Overload**: When developers run `agtoosa graph view` on an early-stage project (e.g. 2 `.md` files or 0 code files), the Studio immediately presents a dense 6-tab enterprise flight deck intended for 50,000-line monorepos. Users feel overwhelmed, confused, and unable to identify the immediate value proposition.
2. **Hardcoded Ghost Placeholders**: The Studio Overview landing page featured static mock values (`for Agtoosa2`, `39 Stories`, `162 criteria AST verified`, `across the 8 core Agtoosa subsystems`) regardless of the active repository, creating confusion about whether the analysis is real.
3. **Abstract Numbers without Actionable Next Steps**: Displaying raw grades or disconnected numbers ("Grade A+", "0 Cycles", "5 Hubs") leaves users asking "What should I do next?".
4. **Missing AI Agent Governance Enforcement**: Modern software teams use AI coding agents (Claude Code, Cursor, Antigravity, Copilot, Windsurf). If a repository lacks explicit instructions in `AGENTS.md` and `CLAUDE.md`, AI agents bypass the graph, introduce cyclic dependencies, and drift from architecture standards.

---

## 2. Acceptance Criteria

- **AC-1 (Genesis Inception Mode Detection)**: WHEN the active workspace contains $< 15$ nodes or $0$ code files, the Studio SHALL automatically activate **Genesis Launchpad Mode**, welcoming the user with project-specific context (`workspace_name`) and suppressing unnecessary enterprise cockpit complexity.
- **AC-2 (Outcome-Driven Value Proposition)**: The Genesis Launchpad SHALL prominently present the **3 Core Superpowers of Agtoosa**:
  1. *Token-Sparing AI Agent Context* (70%+ token savings, zero hallucination).
  2. *Spaghetti-Proof Architecture Guardrails* (zero circular imports, clean layer boundaries).
  3. *Living Architecture as Code* (self-updating C4 and dependency maps).
- **AC-3 (Inline Plain-English Findings & Next Steps)**: The Studio landing view SHALL render an inline briefing card translating repository state into plain English with direct, single-click actions (e.g. "We found 2 documents and 0 code files. Create your first module to start mapping symbols").
- **AC-4 (Progressive Disclosure Toggle — Simple vs. Advanced)**: The Studio header SHALL feature a `[🌿 Simple | ⚡ Advanced]` segmented toggle. In Simple Mode, only `Overview`, `Architecture Map`, and `Dependency Graph` are visible. Deep mathematical and governance views (`Risk Radar`, `Delivery Assurance`, `Blast Radius`) are revealed in Advanced Mode.
- **AC-5 (Universal AI Agent Workflow Enforcement)**: The engine SHALL provide `AgentWorkflowEnforcer` and CLI command `agtoosa agent-init` (plus a Studio 1-click button) to safely generate and non-destructively update `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/agtoosa.mdc`, `.windsurfrules`, and `.github/copilot-instructions.md` using `<!-- AGTOOSA_AGENT_RULES_START -->` delimiters.
- **AC-6 (100% Dynamic Project Grounding)**: All numbers, titles, story counts, subsystem counts, and workspace names SHALL be computed dynamically from the active graph store with zero hardcoded "Agtoosa2" strings.

---

## 3. Tasks & Deliverables

- [x] **Task 58.1**: Implement `AgentWorkflowEnforcer` in `agtoosa/core/agent_rules.py` supporting `AGENTS.md`, `CLAUDE.md`, Cursor, Windsurf, Copilot, and Git pre-push hooks.
- [x] **Task 58.2**: Enhance `agtoosa/graph/visualizer.py` with `workspace_name`, `is_genesis`, `plain_english_findings`, and dynamic workspace grounding.
- [x] **Task 58.3**: Add `POST /api/agent/enforce` endpoint in `agtoosa/graph/server.py`.
- [x] **Task 58.4**: Implement `agtoosa agent-init` command in `agtoosa/cli/main.py` and `agtoosa/cli/lifecycle_cmd.py`.
- [x] **Task 58.5**: Build Genesis Launchpad, Simple/Advanced mode toggle, inline findings cards, and dynamic metrics in `agtoosa/graph/web/` (`index.html`, `views.css`, `state.js`, `app.js`).
- [x] **Task 58.6**: Create automated test suites `tests/test_agent_rules.py` and `tests/test_genesis_onboarding.py`.
