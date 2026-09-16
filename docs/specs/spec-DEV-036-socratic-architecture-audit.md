# DEV-036: Socratic Architecture Audit & 1-Click God-Node Refactoring Blueprints

## Status
- **Status:** ✅ Implemented & Verified
- **Cycle ID:** DEV-036
- **Layer:** Architecture Review / Refactoring / Verification
- **Dependencies:** DEV-044, DEV-048, DEV-033, DEV-034

## Context & Problem Statement
Static analysis tools typically dump static metrics (cyclomatic complexity, line counts) without providing actionable refactoring pathways or identifying cross-modal architectural inconsistencies (e.g. architecture diagrams specifying microservice boundaries that code violates, or God classes accumulating unsustainable efferent/afferent coupling). Furthermore, AI coding agents entering a codebase often jump straight to code edits without realizing the architectural blast radius of God nodes.

## Acceptance Criteria
- **AC-1 (God-Node & Centrality Identification)**: WHEN auditing architecture, the engine SHALL compute centrality metrics and structural coupling to identify architectural God nodes.
- **AC-2 (Cyclic Hotspots & Cross-Modal Consistency)**: WHEN cycles or unverified doc claims exist, the audit SHALL pinpoint exact SCC cycles and ungrounded claims.
- **AC-3 (Refactoring Blueprints & Audit CLI)**: WHEN `agtoosa audit` is executed, the engine SHALL generate structured refactoring blueprints and remediation plans.

## Architectural Invariants
1. **Multi-Faceted Centrality & God Node Identification**:
   - Calculates combined in-degree, out-degree, and betweenness proxies to identify architectural God nodes.
   - Computes structural coupling ratios and flags modules that violate Single Responsibility Principle (SRP).
2. **Cyclic Hotspot Detection**:
   - Executes Tarjan strongly connected components (SCC) analysis to pinpoint dependency cycles between components.
3. **Cross-Modality Latent Couplings**:
   - Correlates visual/documentation nodes (`doc:*`, `visual:*`, `story:*`) with code nodes.
   - Flags code components referenced in documentation that lack automated test evidence (`NodeType.TEST` or `EdgeType.VERIFIES`).
4. **Actionable 1-Click Refactoring Blueprints**:
   - For every identified God node and cycle, attaches executable refactoring blueprints generated via `CycleDecouplerEngine` (interface extraction, dependency inversion) and `DeadCodePruner` (pruning zombie methods).
5. **Socratic Coding Prompts**:
   - Formulates targeted inquiry questions designed for AI agents (Claude, Cursor, Antigravity) that challenge assumptions before code modifications are attempted.
6. **Artifact Output (`GRAPH_REPORT.md`)**:
   - Generates clean, human-readable and agent-ingestible Markdown report with embedded Mermaid diagrams and blueprint diffs.

## CLI & MCP Interfaces
- CLI: `agtoosa audit [--output <path>] [--format markdown|json] [--generate-blueprints]`
- MCP Server Tool: `agtoosa_get_socratic_audit`
