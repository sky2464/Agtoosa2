# Specification: DEV-028 Automated C4 Architecture-as-Code & Live Diagram Sync

## Status
✅ Implemented & Verified

## Priority Score
**82 / 100** (Milestone 12 — Living Documentation: Automatically synthesizes and syncs C4 architecture diagrams in Mermaid, PlantUML, and Structurizr DSL directly from the knowledge graph and commits updated diagrams to documentation).

## Problem Statement
Software architecture diagrams in software teams suffer from chronic rot:
1. **Manual Drawing Desynchronization**: Diagrams drawn in Miro, Lucidchart, or Visio become obsolete within weeks as developers add routes, refactor services, or introduce message queues.
2. **Disconnected Documentation**: Markdown docs in `docs/architecture/` rarely reflect current code reality, leaving new team members and AI coding assistants without a dependable mental model of the system.
3. **No CI Architecture Drift Enforcement**: CI pipelines test unit tests and lints, but never verify whether architectural documentation accurately reflects system boundaries and containers.

## Acceptance Criteria
- **AC-1 (Hierarchical C4 Synthesis)**: WHEN `agtoosa c4 export` is invoked, the engine SHALL synthesize Level 1 (Context), Level 2 (Container), and Level 3 (Component) diagrams in Mermaid, PlantUML, or Structurizr DSL.
- **AC-2 (Live In-Markdown Sync)**: WHEN `agtoosa c4 sync` runs, the engine SHALL update embedded C4 marker blocks in documentation and emit standalone diagram files.
- **AC-3 (CI Drift Linter Gate)**: WHEN `agtoosa c4 sync --check` runs in CI, the engine SHALL exit non-zero if committed diagrams diverge from code reality.

## Objectives
1. **Hierarchical C4 Synthesis Engine (`C4DiagramGenerator`)**:
   - **Level 1 (System Context)**: Maps developers, AI assistants, the core system boundary, external federated repositories, and third-party APIs.
   - **Level 2 (Container)**: Maps CLI subsystem, Native MCP Server, Knowledge Graph SQLite, Web Studio Server, discovered microservices (`NodeType.SERVICE` from DEV-030), and message brokers (`NodeType.TOPIC` from DEV-026).
   - **Level 3 (Component)**: Maps internal architectural subsystems: Parser Subsystem, Lifecycle Engine, Context Compiler, Observability Engine, Refactor Engine, and HTTP Controllers/Endpoints (`NodeType.ENDPOINT` from DEV-025).
2. **Multi-Syntax Renderer**:
   - **Mermaid C4**: `C4Context`, `C4Container`, `C4Component` with `Person(...)`, `System(...)`, `Container(...)`, `Component(...)`, `Rel(...)` renderable natively in GitHub and GitLab Markdown.
   - **PlantUML C4**: `@startuml !include <C4/C4_Context> ... Rel(...) @enduml`.
   - **Structurizr DSL**: Native Structurizr architecture-as-code format (`workspace { model { ... } views { ... } }`).
3. **Live Documentation Sync Engine (`C4SyncManager`)**:
   - In-document markdown sync: Detects `<!-- agtoosa-c4-start:<level> --> ... <!-- agtoosa-c4-end:<level> -->` blocks across documentation markdown files and updates them in-place.
   - Standalone diagram sync: Generates standalone `.mmd`, `.puml`, or `.dsl` files in `docs/architecture/`.
   - CI Drift Linter (`--check`): Validates committed architecture diagrams against live code state; exits with non-zero code if documentation has drifted.
4. **Developer & Agent Surfaces**:
   - CLI: `agtoosa c4 export [--level 1|2|3] [--format mermaid|plantuml|structurizr] [--output <path>]`.
   - CLI: `agtoosa c4 sync [--dir docs/architecture] [--check] [--format mermaid|plantuml|structurizr] [--json]`.
   - MCP Tool: `agtoosa_get_c4_diagram` allowing AI agents to generate C4 diagrams on-the-fly.

## Architecture

```
[ Knowledge Graph Storage (SQLite) ]
├── Nodes (Service, Endpoint, Topic, Component)
└── Edges (Calls, Network_Calls, Routes_To, Publishes)
              │
              ▼
   [ C4DiagramGenerator ]
   ├── Level 1: System Context
   ├── Level 2: Container
   └── Level 3: Component
              │
              ├─► Mermaid C4 (C4Context, C4Container, C4Component)
              ├─► PlantUML C4 (!include <C4/...>)
              └─► Structurizr DSL (workspace { model { ... } })
              │
              ▼
    [ C4SyncManager ]
   ├── In-Markdown Marker Replacement (<!-- agtoosa-c4-start:level -->)
   ├── Standalone File Generation (c4-*.mmd / c4-*.puml)
   └── CI Drift Enforcement (agtoosa c4 sync --check)
```
