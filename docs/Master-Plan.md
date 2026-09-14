# Agtoosa2 — Master Plan

> **Source of truth for Agtoosa Revision 2 development.**
> **Architecture:** Unified Graph-Native Engineering Operating System.

## Project Charter

| Field | Value |
|---|---|
| Product | `Agtoosa2` |
| Repository | `https://github.com/sky2464/Agtoosa2` |
| Version | `0.6.0` (GA Released) |
| Core Engine | Python 3.11+ (SQLite FTS5, Zero-Dependency Standard Library) |
| Active Milestone | `v0.6.0` — **All 32 Stages Delivered (100% Complete)** |
| Next Frontier | `v0.7.0 / v0.8.0` — **Multimodal Ingestion, Living C4 Wiki & Verified Knowledge Intelligence (Graphify Superseding Engine)** |
| Foundation Gate | [**EPIC-001 — Trusted Knowledge Intelligence**](specs/epic-001-trusted-knowledge-intelligence.md) (DEV-040–049) — accuracy before breadth; must pass before Milestone 14 executes |

---

## Strategic Priority & Impact Scoring Matrix (1–100 Scale)

Evaluated across architectural impact, AI agent context amplification, enterprise readiness, and developer workflow leverage:

| Rank | Cycle ID | Title | Rating | Milestone | Status | Strategic Value & Architectural Impact |
|:---:|---|---|:---:|---|:---:|---|
| 🥇 | **DEV-025** | Framework Dependency Injection & Dynamic Routes | **96 / 100** | Milestone 10 (v0.4.2) | ✅ Done | **Highest Architectural Leverage**: Transforms Agtoosa from a syntax AST parser into a true runtime architecture graph by extracting FastAPI/Flask/NestJS/Express DI containers, decorators (`@app.get`), and ORM schema bindings (SQLAlchemy, Prisma). AI agents gain real execution context. |
| 🥈 | **DEV-033** | Multimodal Ingestion & Visual-to-Code Drift Verification | **95 / 100** | Milestone 14 (v0.7.0) | 📋 Planned | **Supersedes Graphify Ingestion**: Ingests PDFs, research papers, whiteboard sketches, architecture diagrams, and web URLs. Cross-references visual diagrams against SQLite AST symbols to detect and flag architectural Visual-to-Code drift. |
| 🥉 | **DEV-034** | Hierarchical Leiden Clustering & Living C4 Autonomous Wiki | **93 / 100** | Milestone 14 (v0.7.0) | 📋 Planned | **Supersedes Graphify Wiki**: Hierarchical Leiden community detection partitioned into Domains, Subsystems, and Modules. Generates `.agtoosa/wiki/` with Obsidian `[[wikilinks]]`, Robert C. Martin package coupling metrics ($C_a, C_e, I, A, D$), and Studio Web tab. |
| 4th | **DEV-037** | Universal Slash Command Skill & Topology-Budgeted Traversal | **92 / 100** | Milestone 14 (v0.8.0) | 📋 Planned | **Universal AI Copilot Parity**: Ships drop-in `/agtoosa` skills for Claude Code, Cursor, Gemini CLI, Windsurf, and Antigravity. Features PageRank-weighted AST skeleton pruning under strict token budgets (`--budget 1500`). |
| 5th | **DEV-029** | PR Blast Radius & Breaking Schema Review Bot | **91 / 100** | Milestone 12 (v0.6.0) | ✅ Done | **Automated PR Governance**: Calculates multi-dimensional blast radius directly from git diffs and posts sticky Markdown review comments with production telemetry risk tiers. |
| 6th | **DEV-035** | Zero-Trust Hallucination Guard & Subagent Extraction | **90 / 100** | Milestone 14 (v0.7.0) | 📋 Planned | **Supersedes Graphify Extraction**: Parallel subagent extraction for non-code assets with tri-state confidence (`EXTRACTED`, `INFERRED`, `AMBIGUOUS`) backed by bidirectional AST grounding to catch and prevent LLM hallucinated symbols. |
| 7th | **DEV-027** | VS Code & Cursor In-Editor Gutter Lens & Marketplace | **89 / 100** | Milestone 11 (v0.5.0) | ✅ Done | **Maximum Developer Adoption**: Brings real-time CodeLens blast radius, caller count, and 1-click Studio refactor actions ("✂️ Prune", "🔄 Decouple") directly into IDE editor gutters. Published to VS Code Marketplace & Open VSX. |
| 8th | **DEV-036** | Socratic Architecture Audit & 1-Click Refactor Plans | **88 / 100** | Milestone 14 (v0.8.0) | 📋 Planned | **Supersedes Graphify Graph Report**: Generates `GRAPH_REPORT.md` with God nodes, betweenness centrality, and surprising cross-modality links, attaching executable 1-click refactoring blueprints from `CycleDecouplerEngine`. |
| 9th | **DEV-030** | Distributed OpenTelemetry Trace Ingestion & Topology | **87 / 100** | Milestone 12 (v0.6.0) | ✅ Done | **Distributed System Visibility**: Ingests OTLP, Jaeger, and Zipkin traces to map runtime RPC/HTTP/gRPC service topologies and stitches them directly to static AST endpoints. |
| 10th | **DEV-026** | Async Message Queue & Event Bus Lineage | **85 / 100** | Milestone 10 (v0.4.2) | ✅ Done | **Event-Driven Topology**: Maps asynchronous message lineages across Kafka, RabbitMQ, Redis Pub/Sub, and Celery task queues. |

---

## Completed Cycles (All 32 Stages Delivered & Verified)

| ID | Title | Type | Status | Primary Deliverable |
|---|---|---|---|---|
| **DEV-032** | Continuous Performance Regression Benchmarking CI | Feature | ✅ Done | Nanosecond AST benchmark harness, historical telemetry baselines, and PR performance regression blocker |
| **DEV-031** | AI Automated PR Repair & Code Review Agent | Feature | ✅ Done | Autonomous PR repair agent applying verified DIP and dead-code refactoring patches with atomic rollback |
| **DEV-030** | Distributed OpenTelemetry Trace Ingestion & Dynamic Topology | Feature | ✅ Done | Cross-service parent-child span hierarchy parsing, RPC topology metrics ($p50, p95, p99$), and AST endpoint stitching |
| **DEV-029** | PR Blast Radius & Breaking Schema Review Bot | CI/CD | ✅ Done | Multi-dimensional git diff analyzer, sticky PR markdown comment generator, and GitHub Action integration |
| **DEV-028** | Automated C4 Architecture-as-Code & Live Diagram Sync | Feature | ✅ Done | Hierarchical C4 synthesis (Mermaid, PlantUML, Structurizr DSL) with live in-markdown doc sync and CI drift linter |
| **DEV-027** | VS Code & Cursor In-Editor Gutter Lens & Marketplace | Extension | ✅ Done | In-editor gutter heatmaps, 1-click QuickFix refactor actions, guard status bar, and `.vsix` packaging |
| **DEV-026** | Async Message Queue & Event Bus Lineage | Feature | ✅ Done | Event-driven graph lineage for Kafka, RabbitMQ, Redis Pub/Sub, Celery, and BullMQ queues |
| **DEV-025** | Framework Dependency Injection & Dynamic Routes | Feature | ✅ Done | Runtime routes & DI resolvers (FastAPI, Flask, Express, NestJS) + ORM schemas (SQLAlchemy, Prisma, Django) |
| **DEV-024** | Pre-Push Architectural Daemon & Drift Linter | Feature | ✅ Done | Real-time daemon, pre-push hook integration, sub-millisecond cache `.agtoosa/guard_status.json` |
| **DEV-023** | Two-Way Interactive Studio Actions | Feature | ✅ Done | Live Studio HTTP server with REST endpoints (`/api/refactor/prune`, `/api/refactor/decouple`, `/api/refactor/rollback`) and 1-click web UI buttons |
| **DEV-022** | Autonomous AST Patch Engine | Feature | ✅ Done | AST rewriting engine applying safe dead-code deletions and dependency inversion interface abstractions with unified diff previews, atomic backups, and rollback capabilities |
| **DEV-021** | Modular Native Studio Architecture (Zero Build Tools) | Refactor | ✅ Done | Monolithic visualizer.py decomposed from 2,979 lines to ~380 lines into clean, dedicated static assets under `agtoosa/graph/web/` (< 250 lines each) |
| **DEV-020** | Dead Code & Zombie Symbol Pruning | Feature | ✅ Done | Unreachable AST node detection, confidence scoring, entrypoint exclusion, safe deletion refactoring blueprints |
| **DEV-019** | Autonomous Cycle Decoupling Engine | Feature | ✅ Done | Automated dependency inversion, shared kernel, and event-driven decoupling blueprints with executable code stubs |
| **DEV-018** | Production Blast Radius | Feature | ✅ Done | Runtime telemetry traffic weighting, live error rates, caller risk multipliers, and dormant dependency detection |
| **DEV-017** | OpenTelemetry & Profiler Heatmap Overlay | Feature | ✅ Done | OpenTelemetry span / profiler ingestion, execution latency & call frequency heatmaps |
| **DEV-016** | Monorepo Package Boundary Enforcement | Feature | ✅ Done | Monorepo workspace discovery, encapsulation leak detection, undeclared dependencies, package cycles, `agtoosa review boundaries` |
| **DEV-015** | Cross-Repo Graph Federation | Feature | ✅ Done | Multi-repository graph ingestion (`agtoosa graph federate`), OpenAPI/gRPC/GraphQL contract bindings, distributed cross-service blast radius |
| **DEV-014** | Hybrid GraphRAG v2 & Semantic Vector Search | Feature | ✅ Done | Zero-dependency dense vector embeddings (`node_embeddings` BLOBs), RRF lexical + semantic search, `compile_context --hybrid`, CLI & MCP |
| **DEV-013** | VS Code & Cursor IDE Extension | Extension | ✅ Done | Native extension package (`extension/`), architecture tree views, real-time CodeLens blast radius, CLI `agtoosa graph symbols` |
| **DEV-012** | Standalone Binary Packaging & Multi-Platform Distribution | DevOps | ✅ Done | Standalone PyInstaller executable (`agtoosa.spec`), build orchestrator (`scripts/build_standalone.py`), Homebrew formula (`Formula/agtoosa.rb`), release workflow |
| **DEV-011** | CI/CD Quality Gate & GitHub Action Integration | Feature | ✅ Done | Composite GitHub Action (`action.yml`), reference CI workflow, PR architectural impact markdown comment generator, CLI `agtoosa ci review/check` |
| **DEV-010** | Review Intelligence & Architecture Drift Alarms | Feature | ✅ Done | Layer boundary enforcement, cyclic dependency alarms, blast radius warnings, PR diff analysis (`agtoosa review --diff`), and Architectural Memory Bank (`agtoosa review remember/reflect`) |
| **DEV-009** | Continuous Watcher & MCP Push | Feature | ✅ Done | Zero-dependency filesystem watcher (`agtoosa graph watch`), Git hooks (`agtoosa graph hooks`), live MCP resource update notifications |
| **DEV-008** | High-Scale Performance & Streaming Optimization | Performance | ✅ Done | O(1) memory chunked streaming (`stream_nodes`, `stream_edges`); in-database recursive SQL CTE for impact traversal; single-pass compound FTS5 queries |
| **DEV-007** | Zero-Trust Security Hardening | Security | ✅ Done | Visualizer CSP & anti-XSS serialization; workspace sandboxing & symlink guards; .gitignore enforcement; secret redaction; MCP depth & line clamps; SQLite PRAGMA hardening |
| **DEV-006** | Broad Polyglot Language & Schema Coverage | Feature | ✅ Done | Polyglot parser supporting Go, Rust, Java, Kotlin, C/C++, C#, SQL DDL, and Dockerfile |
| **DEV-005** | Interactive Architecture Exploration & Visualizer | Feature | ✅ Done | Offline Cytoscape.js HTML visualizer (`agtoosa graph view`), architecture health & cycle reports (`agtoosa graph report`), and multi-format exports (Obsidian, GraphML, Cypher, DOT) |
| **DEV-004** | Native Model Context Protocol (MCP) Server | Feature | ✅ Done | Built-in stdio/SSE MCP server exposing real-time graph navigation tools to AI coding agents |
| **DEV-003** | Graph-Driven Lifecycle & Context Compilation v0.2 | Feature | ✅ Done | Spec/Story/Criteria/Task ingestion, Context Compiler v0.2 (Graph RAG), `review`, and mathematical proof `ship` gates |
| **DEV-002** | Reliable Incremental Updates & Investigation | Feature | ✅ Done | Content hash fingerprints, incremental sync, `/agtoosa graph explain/path/impact` |
| **DEV-001** | Core Foundation & AST Knowledge Graph | Feature | ✅ Done | Unified CLI, polyglot AST extractors (Py/JS/TS/Sh), SQLite FTS5 graph store, `/agtoosa graph build/query/status/export` |

---

## Strategic Roadmap & Delivery Stages

```mermaid
flowchart LR
    S1[Stage 1: AST Graph Core ✅] --> S2[Stage 2: Updates & Impact ✅]
    S2 --> S3[Stage 3: Lifecycle RAG ✅]
    S2 --> S6[Stage 6: Polyglot Parsers ✅]
    S2 --> S7[Stage 7: Zero-Trust Security ✅]
    S2 --> S8[Stage 8: Streaming Scale ✅]
    S3 --> S4[Stage 4: Native MCP Server ✅]
    S3 --> S5[Stage 5: Visual Explorer ✅]
    S4 --> S9[Stage 9: Continuous Watcher ✅]
    S3 --> S10[Stage 10: Review Intelligence ✅]
    S10 --> S11[Stage 11: CI/CD PR Gate ✅]
    S11 --> S12[Stage 12: Binary Packaging ✅]
    S4 --> S13[Stage 13: IDE Extension ✅]
    S3 --> S14[Stage 14: Hybrid GraphRAG v2 ✅]
    S14 --> S15[Stage 15: Cross-Repo Federation ✅]
    S15 --> S16[Stage 16: Monorepo Boundaries ✅]
    S15 --> S17[Stage 17: Runtime Observability ✅]
    S17 --> S18[Stage 18: Production Blast Radius ✅]
    S10 --> S19[Stage 19: Cycle Decoupler ✅]
    S19 --> S20[Stage 20: Dead Code Pruning ✅]
    S5 --> S21[Stage 21: Modular Studio Web ✅]
    S20 --> S22[Stage 22: Auto-Fix Patch Engine ✅]
    S21 --> S23[Stage 23: Two-Way Studio Actions ✅]
    S22 --> S23
    S22 --> S24[Stage 24: Pre-Push Arch Daemon (72) ✅]
    S15 --> S25[Stage 25: Framework DI & Routes (96) ✅]
    S25 --> S26[Stage 26: Async Event Bus Lineage (85) ✅]
    S26 --> S27[Stage 27: In-Editor Gutter Lens (89) ✅]
    S13 --> S27
    S23 --> S27
    S24 --> S29[Stage 29: PR Blast Radius Bot (91) ✅]
    S25 --> S29
    S26 --> S29
    S17 --> S30[Stage 30: Distributed OTel Topology (87) ✅]
    S25 --> S30
    S5 --> S28[Stage 28: C4 Architecture-as-Code (82) ✅]
    S30 --> S28
    S29 --> S31[Stage 31: AI PR Repair Agent (79) ✅]
    S30 --> S32[Stage 32: Perf Regression CI (74) ✅]
    S3 --> S33[Stage 33: Multimodal Ingest & Visual Drift (95)]
    S28 --> S34[Stage 34: Hierarchical Leiden Wiki (93)]
    S33 --> S35[Stage 35: Zero-Trust Hallucination Guard (90)]
    S34 --> S36[Stage 36: Socratic Audit & Refactor Plans (88)]
    S35 --> S37[Stage 37: Universal Slash Skill & Context Budget (92)]
    S36 --> S37
```

### Milestone 1: Knowledge Engine Core (v0.2.0-alpha)
- **DEV-001 (Stage 1) — Core Foundation & AST Knowledge Graph** [✅ Done]
  - Python 3.11+ packaging, zero-service architecture, single `agtoosa` CLI.
  - Parsers for Python, JavaScript/TypeScript, and Shell.
  - SQLite transactional schema + FTS5 full-text indexing.
  - Commands: `agtoosa graph build`, `agtoosa graph query`, `agtoosa graph status`, `agtoosa graph export`.
- **DEV-002 (Stage 2) — Reliable Incremental Updates & Investigation** [✅ Done]
  - Content hash fingerprints, rename and deletion handling.
  - Commands: `agtoosa graph explain <symbol>`, `agtoosa graph path <from> <to>`, `agtoosa graph impact <target>`.

### Milestone 2: Lifecycle Integration & Agent Context (v0.2.0-beta)
- **DEV-003 (Stage 3) — Graph-Driven Lifecycle & Context Compilation v0.2** [✅ Done]
  - Ingestion of Story, Criterion, Task, and Test nodes into the knowledge graph.
  - Context RAG v0.2: Bounded subgraph prompt compilation replacing bloated markdown templates.
  - Lifecycle state machine: `agtoosa review` and mathematical proof graph validation on `agtoosa ship`.
- **DEV-004 (Stage 4) — Native Model Context Protocol (MCP) Server** [✅ Done]
  - Built-in MCP server (`agtoosa mcp`) providing real-time tools for Cursor, Claude Code, Windsurf, Gemini, and Copilot.
  - Tools: `get_symbol_context`, `query_impact_radius`, `get_active_task_context`, `record_task_evidence`, `agtoosa_watch_status`.

### Milestone 3: Production Hardening, Scale & Breadth (v0.2.0-rc.2)
- **DEV-005 (Stage 5) — Interactive Architecture Exploration & Visualizer** [✅ Done]
  - Bundled standalone offline viewer (`agtoosa graph view`).
  - Community clustering, PageRank importance scoring, cycle detection, health scorecard (`agtoosa graph report`).
  - Multi-format exports: Markdown wiki / Obsidian vault, GraphML, Cypher, DOT.
- **DEV-006 (Stage 6) — Broad Polyglot Language & Schema Coverage** [✅ Done]
  - Polyglot parser supporting Go, Rust, Java, Kotlin, C/C++, C#, SQL DDL tables & views, and Dockerfiles.
- **DEV-007 (Stage 7) — Zero-Trust Security Hardening** [✅ Done]
  - Strict Content-Security-Policy & anti-XSS HTML escaping in visualizer.
  - Workspace scanner sandboxing, canonical path boundary checks, and symlink escape defenses.
  - Automated regex secret and private key redaction in nodes and docstrings.
  - .gitignore pattern loading and enforcement during workspace scans.
  - MCP JSON-RPC protocol max depth and line byte clamping.
- **DEV-008 (Stage 8) — High-Scale Performance & Streaming Optimization** [✅ Done]
  - O(1) memory footprint chunked generators (`stream_nodes`, `stream_edges`).
  - In-database SQLite `WITH RECURSIVE` CTE for blast radius calculations (`compute_impact`).
  - Single-pass compound boolean FTS5 query optimization in Context Compiler.

### Milestone 4: Operational Intelligence & Automation (v0.2.0-GA)
- **DEV-009 (Stage 9) — Continuous Watcher & MCP Push Notifications** [✅ Done]
  - Background filesystem watcher (`agtoosa graph watch`), incremental sync on save with debouncing.
  - Automated Git hook management (`agtoosa graph hooks install/remove/status`).
  - Real-time MCP resource notifications (`notifications/resources/updated`) for connected AI assistants.
- **DEV-010 (Stage 10) — Review Intelligence & Architecture Drift Alarms** [✅ Done]
  - Architectural tier hierarchy enforcement (Tier 1 Entrypoints -> Tier 2 Application/Engine -> Tier 3 Domain Core).
  - Cyclic dependency alarms and high blast radius warnings.
  - Git PR line-level diff to graph symbol mapping (`agtoosa review --diff <base-ref>`).
  - Institutional Architectural Memory Bank (`agtoosa review remember/reflect`) with automatic prompt injection.

### Milestone 5: Ecosystem, Packaging & CI/CD Intelligence (v0.2.x)
- **DEV-011 (Stage 11) — CI/CD Quality Gate & GitHub Action Integration** [✅ Done]
  - Composite GitHub Action (`action.yml`) running `agtoosa review --diff origin/main --strict`.
  - Automated rich PR architectural impact markdown comment generator.
  - Merge blocking on circular dependencies or layer boundary regressions.
- **DEV-012 (Stage 12) — Standalone Binary Packaging & Distribution** [✅ Done]
  - Standalone compiled executables (macOS Apple Silicon/Intel, Linux x86_64, Windows x64).
  - Automated GitHub Releases matrix, Homebrew tap formula, PyPI publication.
- **DEV-013 (Stage 13) — VS Code & Cursor IDE Extension** [✅ Done]
  - In-editor architecture tree view, caller/callee inspection, code lens annotations, and real-time blast radius alerts.
- **DEV-014 (Stage 14) — Hybrid GraphRAG v2 & Semantic Vector Search** [✅ Done]
  - Embedded zero-dependency dense vector embeddings, cosine similarity + FTS5 + graph CTE hybrid prompt compiler.
  - Reciprocal Rank Fusion (RRF) search, CLI `agtoosa graph embeddings build/status`, `agtoosa context compile --hybrid`, MCP `agtoosa_hybrid_search`.

### Milestone 6: Enterprise Federation & Microservices (v0.3.0)
- **DEV-015 (Stage 15) — Cross-Repo Graph Federation** [✅ Done]
  - Multi-repository workspace graph ingestion (`agtoosa graph federate <git-url>`).
  - Distributed blast radius across microservices (OpenAPI/Swagger, gRPC `.proto`, GraphQL schema bindings).
- **DEV-016 (Stage 16) — Monorepo Package Boundary Enforcement** [✅ Done]
  - Workspace package encapsulation policies (`packages/*` boundaries).
  - Alarms preventing internal non-exported module leakage across packages.
  - Verification CLI `agtoosa review boundaries [--strict]`.

### Milestone 7: Runtime Observability & Dynamic Heatmaps (v0.3.5)
- **DEV-017 (Stage 17) — OpenTelemetry & Profiler Heatmap Overlay** [✅ Done]
  - Ingest OpenTelemetry trace spans or PySpy profiler data into the knowledge graph.
  - Live call frequency, execution latency, and error-rate color heatmaps in C4 visualizer.
- **DEV-018 (Stage 18) — Production Blast Radius** [✅ Done]
  - Weight static AST caller graphs with real-time production traffic percentages.

### Milestone 8: Autonomous Architecture Refactoring Engine (v0.4.0)
- **DEV-019 (Stage 19) — Automated Cycle Decoupling** [✅ Done]
  - Interactive CLI / agent engine to automatically generate dependency injection interfaces or event-driven adapters that resolve cyclic dependencies detected by Tarjan's algorithm.
- **DEV-020 (Stage 20) — Dead Code & Zombie Symbol Pruning** [✅ Done]
  - Identify zero-caller unreachable AST nodes and generate safe deprecation/deletion refactors.
  - Confidence scoring (low/medium/high), entrypoint exclusion, CLI `agtoosa refactor dead-code`, MCP `agtoosa_detect_dead_code`.

### Milestone 9: Autonomous Code Actions & 2-Way Studio Sync (v0.4.1)
- **DEV-021 (Stage 21) — Modular Native Studio Architecture (Zero Build Tools)** [✅ Done]
  - **Goal**: Decoupled monolithic `visualizer.py` from 2,979 lines down to 386 lines by extracting clean, syntax-highlighted modular assets under `agtoosa/graph/web/`:
    - `index.html`: Clean semantic layout skeleton (< 150 lines).
    - `css/theme.css`: Design tokens, dark mode palette, typography, glassmorphism (< 100 lines).
    - `css/layout.css`: Header navigation, responsive omni-search, KPI ribbon, docked drawer (< 120 lines).
    - `css/views.css`: Component styles for C4 Blueprint, Network Canvas, Risk Radar, and Blast Radius (< 220 lines).
    - `js/state.js`: Central reactive state (selected node, domain filter, telemetry toggle, active perspective) (< 80 lines).
    - `js/c4_view.js`: Cytoscape.js C4 layout, compound nodes, and domain clustering (< 180 lines).
    - `js/network_view.js`: HTML5 2D canvas sunflower spiral layout, pan/zoom, domain isolation (< 220 lines).
    - `js/blast_view.js`: 3-column blast radius traversal, runtime telemetry weighting, and traffic risk tiers (< 160 lines).
    - `js/radar_view.js`: Centrality rankings, Stage 19 Cycle Decoupler blueprints, and Stage 20 Dead Code pruning table (< 180 lines).
    - `js/drawer.js`: Slide-over inspection drawer and 1-click AI Context Pack (Markdown/JSON) export (< 100 lines).
    - `js/app.js`: Tab routing, global search (`⌘K`), Guide modal, and export handlers (< 120 lines).
  - **Zero Build Tools**: 100% pure standard ES modules and native CSS. Zero Node.js, Bun, or npm tooling required at runtime or install, staying completely faithful to the Python 3.11+ zero-service foundation in `draft.md`.
  - **Eliminated f-string Escaping Collisions**: Completely removed brittle Python double-braced syntax (`{{}}` and `${{}}`), enabling native IDE formatting, syntax highlighting, and linting.
  - **Python Visualizer Refactor**: Dropped `visualizer.py` from ~3,000 lines down to 386 lines.
  - **Dual-Mode Serving**: Supports live serving of modular assets + single-file offline packager for portable `.html` exports.

- **DEV-022 (Stage 22) — Autonomous AST Patch Engine** [✅ Done]
  - AST rewriting engine (`agtoosa/refactor/engine.py`) applying safe dead-code deletions and dependency inversion interface abstractions to source files.
  - Generates unified diffs for `--dry-run` previews without modifying files.
  - Automatic atomic backup creation under `.agtoosa/refactor_backups/<plan_id>/` with rollback support.
  - CLI: `agtoosa refactor dead-code [--apply] [--dry-run]`, `agtoosa refactor decouple [--apply] [--dry-run]`, `agtoosa refactor rollback <backup_id>`, `agtoosa refactor backups`.

- **DEV-023 (Stage 23) — Two-Way Interactive Studio Actions** [✅ Done]
  - Embedded HTTP server (`agtoosa/graph/server.py`) exposing REST endpoints:
    - `POST /api/refactor/prune`: Direct 1-click symbol pruning from the browser.
    - `POST /api/refactor/decouple`: Automated interface abstraction generation.
    - `POST /api/refactor/rollback`: Instant snapshot restoration.
    - `GET /api/refactor/backups`: Snapshot history.
    - `GET /api/graph`: Dynamic graph data polling.
  - Actionable **"✂️ Safe Prune"** buttons integrated directly into the Agtoosa Studio Dead Code table.
  - CLI: `agtoosa graph view --serve [--port 8080]`.

- **DEV-024 (Stage 24) — Pre-Push Architectural Daemon & Drift Linter** [✅ Done — Rating: 72/100]
  - **Objective**: Shift architectural enforcement left into the local development loop, blocking pushes that introduce circular dependencies or blast radius regressions before CI triggers.
  - **Background Daemon**: `agtoosa guard --daemon` runs a background watcher that monitors working tree changes, computes incremental drift, and writes a sub-millisecond status cache to `.agtoosa/guard_status.json`.
  - **Git Hook Integration**: Pre-push and pre-commit hooks invoke `agtoosa guard --strict`, checking the cached or live graph invariants in < 15ms.
  - **Blast Radius Circuit Breaker**: Configurable threshold (`--max-blast-radius <N>`, default: 5) alerting or rejecting changes that touch foundational symbols with cascading caller dependencies.
  - **CLI Surface**:
    - `agtoosa guard [--install-hooks] [--uninstall-hooks]`: Manage repository Git hooks.
    - `agtoosa guard [--daemon] [--interval <sec>]`: Run in continuous background monitoring mode.
    - `agtoosa guard [--strict] [--max-blast-radius <int>] [--base-ref <ref>] [--json] [--status]`: Direct audit or cache status inspection.

### Milestone 10: Deep Polyglot Framework Semantics & Distributed Event Lineage (v0.4.2)
- **DEV-025 (Stage 25) — Framework Dependency Injection & Dynamic Routes** [✅ Done — Rating: 96/100]
  - **Objective**: Elevate the knowledge engine from syntactic AST parsing to true runtime architecture graphs by extracting framework Dependency Injection containers, dynamic route decorators, and ORM schema relationships.
  - **Dependency Injection Resolvers**:
    - **Python**: Parse FastAPI `Depends(...)`, Dishka, Injector, and Django service providers to link caller routes directly to underlying service implementations.
    - **TypeScript/Node**: Extract NestJS `@Injectable()`, `@Inject()`, `InversifyJS`, and TSyringe container bindings.
  - **Dynamic Route & Endpoint Binding**:
    - **FastAPI / Flask**: Extract `@app.get(...)`, `@app.post(...)`, `@router.api_route(...)`, and Flask blueprints into distinct `Endpoint` nodes with HTTP verb, path, path parameters, and target handler function edges.
    - **Express / NestJS**: Extract `app.use('/api', router)`, `router.get(...)`, NestJS `@Controller('/users')` and `@Get(':id')` into unified route hierarchy nodes.
  - **ORM Model & Schema Relational Mapping**:
    - **SQLAlchemy**: Extract `relationship(...)`, `ForeignKey(...)`, and declarative table classes, creating graph edges between database tables, models, and querying functions.
    - **Prisma**: Parse `schema.prisma` files to map Prisma models, field attributes (`@relation`), and foreign keys directly into the knowledge graph.
    - **Django ORM**: Map `models.ForeignKey`, `models.ManyToManyField`, and model querysets.
  - **CLI & MCP Tooling**:
    - `agtoosa graph routes [--json]`: List all detected HTTP API endpoints and their bound handler functions.
    - `agtoosa graph di <symbol>`: Trace injected providers, dependencies, and resolution chains.
    - MCP Tool: `agtoosa_get_route_context` providing AI coding agents with instant mappings from API route to service and database layer.

- **DEV-026 (Stage 26) — Async Message Queue & Event Bus Lineage** [✅ Done — Rating: 85/100]
  - **Objective**: Extend graph lineage across decoupled asynchronous message brokers, pub/sub channels, and background job task trees.
  - **Domain Model Extension**: Added `NodeType.TOPIC = "topic"`, `EdgeType.PUBLISHES = "publishes"`, `EdgeType.SUBSCRIBES = "subscribes"`.
  - **Message Broker & Queue Extractors**:
    - **Apache Kafka**: Extract producer `send(topic=...)` and `produce(...)` calls, consumer `KafkaConsumer` and `AIOKafkaConsumer` loops in Python; KafkaJS `send({ topic })` and `subscribe({ topic })` in TS/JS.
    - **RabbitMQ / AMQP**: Map `channel.basic_publish(..., routing_key=...)` and `channel.basic_consume(queue=..., on_message_callback=...)` in Python; `channel.sendToQueue`, `channel.publish`, and `channel.consume` in TS/JS.
    - **Redis Pub/Sub**: Extract `r.publish("channel", ...)` and `pubsub.subscribe("channel")` in Python; `redis.publish` and `redis.subscribe` in TS/JS.
    - **Celery / Distributed Tasks**: Parse `@app.task` / `@shared_task` definitions (subscribers), `.delay(...)` invocations (publishers), `.apply_async(queue=...)` calls, and BullMQ `new Queue`, `queue.add`, `new Worker` in TS/JS.
  - **Query Engine & Orphan Detection**:
    - `query_events(store, topic=...)` traces publishers -> topics -> subscribers.
    - Automated detection of dead topics: unhandled messages (`no_subscribers`), dormant consumers (`no_publishers`), and isolated topics.
  - **CLI & MCP Tooling**:
    - `agtoosa graph events [--topic <name>] [--json]`: Display formatted console tables and JSON payloads.
    - MCP Tool: `agtoosa_get_event_lineage` providing AI coding agents with instant cross-boundary event lineage.

### Milestone 11: Real-Time Developer Surface & In-Editor CodeLens (v0.5.0)
- **DEV-027 (Stage 27) — VS Code & Cursor In-Editor Gutter Lens & Marketplace** [✅ Done — Rating: 89/100]
  - **Objective**: Embed Agtoosa's architectural intelligence and autonomous refactoring directly into developer flow in VS Code and Cursor editors.
  - **Real-Time CodeLens & Gutter Overlays**:
    - Live upstream caller badges (`⎇ N callers | 💥 blast radius: <RISK>`) floating above function/class declarations.
    - Gutter color coding and icons (`hot.svg`, `error.svg`, `cold.svg`) for runtime telemetry hotspots from OpenTelemetry heatmaps.
  - **In-Editor 1-Click Refactoring Actions (QuickFix)**:
    - **"✂️ Agtoosa: Safe Prune Dead Symbol"**: Invokes RefactorEngine with automatic atomic backup.
    - **"🔄 Agtoosa: Decouple Cyclic Dependency"**: Generates interface protocol and updates call signatures.
    - **"🛡️ Agtoosa: Inspect Blast Radius"**: Inspects active symbol blast radius.
  - **Pre-Push Guard Status Bar**:
    - Real-time status bar badge (`$(shield) Agtoosa: Invariants Clean` vs `$(alert) Agtoosa: N Drift Alarms`).
  - **Packaging & Ecosystem Distribution**:
    - Zero-dependency Python VSIX builder: `scripts/build_extension.py` generating Open VSIX OPC packages (`agtoosa-vscode-0.5.0.vsix`).
    - Automated GitHub Actions release pipeline (`.github/workflows/marketplace-release.yml`) publishing to **VS Code Marketplace** and **Open VSX Registry**.
    - Full version synchronization across repository to `0.5.0`.

### Milestone 12: CI/CD Pull Request Governance & Deep Lineage (v0.6.0)
- **DEV-029 (Stage 29) — PR Blast Radius & Breaking Schema Review Bot** [✅ Done — Rating: 91/100]
  - **Objective**: Automate PR review governance by calculating multi-dimensional blast radius directly from git diffs, posting rich sticky Markdown reports on pull requests.
  - **Multi-Dimensional Diff Analysis**:
    - Scans modified file line ranges using native `git diff -U0` parser.
    - Identifies modified symbols, upstream callers, impacted API routes (DEV-025), and affected message queues / event topics (DEV-026).
    - Correlates with OpenTelemetry runtime telemetry to compute production risk tiers (P0_CRITICAL to P4_DORMANT) and traffic at risk.
    - Checks for architectural violations, layer boundary breaches, and cyclic regressions (DEV-010).
  - **Sticky PR Markdown Comment Generator**:
    - Generates GitHub Flavored Markdown summary card, modified symbol table, impacted API routes, message broker lineage, and architectural drift alarms.
    - Uses deterministic HTML marker `<!-- agtoosa-pr-bot-comment -->` for sticky updates.
  - **Zero-Dependency GitHub REST API Client**:
    - Pure standard library (`urllib.request`) implementation supporting token authentication and comment creation/upsertion without third-party packages.
  - **CLI & GitHub Action Pipeline**:
    - CLI: `agtoosa ci pr-bot [--base <ref>] [--pr <num>] [--repo <owner/repo>] [--post-comment] [--output <path>] [--json] [--fail-on-p0] [--strict]`.
    - Workflow: `.github/workflows/agtoosa-pr-bot.yml` providing out-of-the-box CI integration.

- **DEV-030 (Stage 30) — Distributed OpenTelemetry Trace Ingestion & Dynamic Topology** [✅ Done — Rating: 87/100]
  - **Objective**: Ingest distributed traces across decoupled microservices to map network-level RPC/gRPC/HTTP calls directly alongside static AST callgraphs.
  - **Multi-Format Trace Parser**:
    - Supports OpenTelemetry OTLP JSON (v1 `ExportTraceServiceRequest`), Jaeger JSON export format, and Zipkin JSON array format.
    - Zero external runtime dependencies: Built purely on Python 3.11+ standard library.
  - **Dynamic Service Topology Engine**:
    - Reconstructs cross-service parent-child span hierarchies, extracting `NodeType.SERVICE` (`service:<name>`) nodes and directed `EdgeType.NETWORK_CALLS` edges.
    - Computes link-level metrics: call volume, latency percentiles ($p50, p95, p99$), error rates, and protocols (`http`, `grpc`, `db`, `network`).
  - **AST Endpoint Stitching**:
    - Cross-references server spans with local AST `Endpoint` (DEV-025) and `Function` nodes.
    - Connects remote caller services directly to codebase handlers and records `runtime_telemetry`.
  - **Topology Query & Diagnostics**:
    - `query_topology(store, service=...)` computes service dependency graphs, latency bottlenecks ($p95 \ge 300\text{ms}$), error hotspots, and circular service dependencies ($A \leftrightarrow B$).
  - **Developer & Agent Surfaces**:
    - CLI: `agtoosa telemetry traces <file> [--format otel|jaeger|zipkin] [--no-stitch] [--json]`.
    - CLI: `agtoosa graph topology [--service <name>] [--json]`.
    - MCP Tool: `agtoosa_get_service_topology`.
    - Studio Visualizer: "Distributed Services & Runtimes" domain tier (`🌐`) and network edge styling.

- **DEV-028 (Stage 28) — Automated C4 Architecture-as-Code & Live Diagram Sync** [✅ Done — Rating: 82/100]
  - **Objective**: Synthesize hierarchical C4 Architecture diagrams in Mermaid, PlantUML, and Structurizr DSL directly from the knowledge graph and synchronize diagrams into repository docs on build.
  - **Hierarchical C4 Synthesis**:
    - Level 1: System Context (Developers, AI agents, core system boundary, external repos, third-party APIs).
    - Level 2: Container (CLI, MCP server, SQLite store, Web Studio, discovered microservices, event queues).
    - Level 3: Component (Parser subsystem, Lifecycle engine, Context compiler, Refactor engine, Observability ingester, HTTP endpoints).
  - **Multi-Syntax Renderers**:
    - Pure GitHub-compatible Mermaid C4 (`C4Context`, `C4Container`, `C4Component`).
    - PlantUML C4 macros (`!include <C4/C4_Context>`).
    - Structurizr DSL (`workspace { model { ... } views { ... } }`).
  - **Live Documentation Sync & CI Linter**:
    - In-markdown marker replacement: Automatically updates `<!-- agtoosa-c4-start:<level> -->` blocks in docs/README files.
    - Standalone diagram sync: Generates `.mmd`, `.puml`, or `.dsl` files in target documentation folders.
    - CI Drift Linter: `agtoosa c4 sync --check` exits with non-zero status if architecture documentation is out-of-sync.
  - **CLI & MCP Tooling**:
    - `agtoosa c4 export [--level context|container|component] [--format mermaid|plantuml|structurizr] [--output <path>]`.
    - `agtoosa c4 sync [--dir docs/architecture] [--check] [--format mermaid|plantuml|structurizr] [--json]`.
    - MCP Tool: `agtoosa_get_c4_diagram`.

- **DEV-031 (Stage 31) — AI Automated PR Repair & Code Review Agent** [✅ Done — Rating: 79/100]
  - **Objective**: Autonomous AI repair agent that inspects PR diffs, identifies architectural violations (cycles, dead code, layer boundary leaks), synthesizes verified AST refactor patches, and creates git commits with atomic rollback safety.
  - **Autonomous Diagnostics**:
    - Scans graph invariants and Tarjan cycle detection to uncover circular dependencies.
    - Queries unreachable zero-caller symbols with confidence scoring for dead code pruning.
    - Detects layer boundary violations and monorepo encapsulation leaks.
  - **Verified Patch Synthesis & Decoupling**:
    - Automated Dependency Inversion (DIP) interface protocol extraction via `CycleDecouplerEngine`.
    - AST-level safe dead code removal via `DeadCodePruner` and `RefactorEngine`.
    - Computes unified diffs for `--dry-run` inspection without mutating the workspace.
  - **Post-Repair Verification & Atomic Rollback Gate**:
    - Automatically audits invariants following patch application.
    - Instantly triggers transactional rollback (`RefactorEngine.rollback`) if cycle violations persist.
  - **Git Branch & Commit Automation**:
    - Stages modified files and crafts commit messages: `refactor(arch): auto-repair <issue_type> (<plan_id>)`.
    - Optional branch targeting with `--branch <name>`.
  - **CLI & MCP Tooling**:
    - CLI: `agtoosa ci repair [--base <ref>] [--apply] [--dry-run] [--branch <name>] [--json]`.
    - MCP Tool: `agtoosa_auto_repair_pr`.

- **DEV-032 (Stage 32) — Continuous Performance Regression Benchmarking CI** [✅ Done — Rating: 74/100]
  - **Objective**: Automated AST benchmark harness that discovers modified symbols from PR diffs, executes calibrated nanosecond latency and memory micro-benchmarks, and compares outcomes against historical telemetry or baseline snapshots to block performance regressions.
  - **AST-Targeted Benchmark Discovery (`BenchmarkHarness`)**:
    - Discovers benchmarkable functions, methods, and HTTP endpoints touched in PR diffs or uncommitted trees.
    - Executes calibrated iterations (50–100 runs) with warmup passes to eliminate JIT/cold-start noise.
    - Employs `time.perf_counter_ns` and `tracemalloc` to compute p50, p95, p99, min, max, average latencies, throughput (ops/sec), and peak memory delta.
  - **Dual Baseline Strategy (`BenchmarkBaselineStore`)**:
    - Persistent golden baselines stored in `.agtoosa/benchmarks/baseline.json` with snapshot tagging support.
    - Automatic fallback and live seeding from OpenTelemetry / profiler traces stored in `GraphStore.runtime_telemetry` (DEV-017 / DEV-030).
  - **Statistical Regression Analyzer (`RegressionAnalyzer`)**:
    - Calculates latency percent shift: $\Delta\% = \frac{\text{Current } p95 - \text{Baseline } p95}{\text{Baseline } p95} \times 100\%$.
    - Circuit breaker SLA enforcement: Flags regressions exceeding `--threshold` (default: $+10.0\%$).
    - Formats GitHub PR markdown summary tables and JSON reports.
  - **Developer, CLI & MCP Surfaces**:
    - CLI: `agtoosa ci benchmark [--base <ref>] [--threshold <pct>] [--strict] [--save-baseline] [--output <path>] [--json]`.
    - CLI: `agtoosa benchmark run [--target <name_or_path>] [--iterations <N>] [--threshold <pct>] [--save-baseline] [--json]`.
    - CLI: `agtoosa benchmark snapshot [--name <tag>] [--json]`.
    - MCP Tool: `agtoosa_run_performance_benchmark`.
    - CI Workflow: `.github/workflows/agtoosa-benchmark.yml`.

---

---

## Milestone 14: Multimodal Ingestion, Living C4 Architecture Wiki & Verified Knowledge Intelligence (v0.7.0 & v0.8.0)

> **Strategic Objective**: Absorb and fundamentally supersede the open-source capabilities of [Graphify](https://github.com/Graphify-Labs/graphify). While Graphify operates as a passive, unverified reader that offloads unsanitized LLM hallucinations into static files, Agtoosa2 delivers an enterprise-grade, mathematically verified, bidirectional knowledge OS connecting unstructured artifacts directly to concrete AST and runtime models.

### Comprehensive Competitive Research: Graphify vs. Agtoosa2

| Capability / Dimension | Graphify Reference Baseline | Agtoosa2 Next Frontier (Milestone 14) |
|---|---|---|
| **Input Modalities** | Local files, PDFs, images via raw prompt | **Multi-format Ingester (`agtoosa ingest / add`)**: Native PDF papers, specs, Markdown/Notion workspaces, web URLs (arXiv, RFCs, GitHub issues) |
| **Diagrams & Visuals** | LLM describes image text/OCR | **Visual Architecture Parser & Drift Verification**: Extracts components from Mermaid, PlantUML, Excalidraw, PNG/SVG diagrams, and whiteboard photos; binds visual boxes and arrows to concrete SQLite AST symbols |
| **Visual-to-Code Alignment** | ❌ Blind (no code verification) | **Visual-to-Code Drift Engine**: Mathematically checks if diagram connections match AST callgraphs and flags architectural drift |
| **Community Clustering** | Basic flat Louvain clustering | **Hierarchical Leiden Community Engine**: Multi-tier partitioning (Domains $\to$ Subsystems $\to$ Modules $\to$ Components) |
| **Architecture Wiki** | Flat markdown files (`graphify-out/wiki/`) | **Living C4 Architecture Wiki (`agtoosa wiki build`)**: Obsidian `[[wikilinks]]`, dynamic C4 container/component diagrams, and Robert C. Martin package metrics ($C_a, C_e, I, A, D$) hosted natively in Studio Web |
| **Audit & Reporting** | Static text `GRAPH_REPORT.md` | **Actionable Socratic Audit (`agtoosa audit`)**: Computes God nodes and surprising cross-modality links, attaching executable 1-click refactoring blueprints (`CycleDecouplerEngine`) |
| **Semantic Extraction Safety**| Blind trust of LLM subagent output | **Zero-Trust Hallucination Guard**: Validates agent extracted symbols against SQLite AST index; flags non-existent references as `HALLUCINATED_UNVERIFIED` |
| **Query & Token Budgeting** | Naive BFS/DFS string truncation | **Topology-Weighted AST Skeleton Pruning**: PageRank-guided context compilation fitting valid syntax skeletons into strict token limits (`--budget 1500`) |
| **Agent Slash Command** | Single-host Claude Code skill | **Universal Multi-Host Skill**: Drop-in `/agtoosa` skills for Claude Code, Cursor, Gemini CLI, Windsurf, and Antigravity |

---

### Detailed Stage Specifications

- **DEV-033 (Stage 33) — Multimodal Knowledge Ingestion & Visual-to-Code Architecture Drift Verification** [📋 Planned — Rating: 95/100]
  - **Objective**: Ingest unstructured multimodal knowledge artifacts (PDF papers, specifications, web URLs, architecture diagrams, whiteboard photos) and verify them against the codebase AST to detect visual specification drift.
  - **Multi-Format Document Parser (`agtoosa/parser/multimodal/`)**:
    - **PDF Ingestion**: Parses academic papers, RFCs, and product specifications, extracting title, abstract, methodology, sections, formulas, and bibliographic citations.
    - **Web URL Ingestion (`agtoosa add <url>`)**: Fetches arXiv papers, GitHub issues, RFCs, and technical blog posts, extracting clean Markdown and metadata.
    - **Markdown / Notion Ingestion**: Discovers frontmatter tags, document cross-references, and requirement tables.
  - **Visual Diagram & Whiteboard Extractor**:
    - Parses vector diagrams (Mermaid `.mmd`, PlantUML `.puml`, Excalidraw `.excalidraw`) and raster images (architecture screenshots, whiteboard sketches) via connected assistant vision.
    - Extracts conceptual nodes (systems, components, databases) and directed relationships (calls, sends, reads, writes).
  - **Visual-to-Code Drift Engine (`VisualDriftDetector`)**:
    - Matches visual entities against indexed SQLite AST nodes (`NodeType.ENDPOINT`, `NodeType.CLASS`, `NodeType.SERVICE`).
    - Flags **Ghost Nodes**: Visual components depicted in diagrams that have no matching implementation in code.
    - Flags **Path Mismatches**: Diagrams asserting $A \to B$ when the AST proves $A \to C \to B$ or $B \to A$.
  - **CLI & MCP Tooling**:
    - CLI: `agtoosa ingest <path|url> [--mode deep] [--tag <domain>] [--json]`.
    - CLI: `agtoosa add <url> [--author <name>] [--contributor <name>]`.
    - CLI: `agtoosa graph drift visual [--strict] [--json]`.
    - MCP Tool: `agtoosa_ingest_multimodal_source`, `agtoosa_check_visual_drift`.

- **DEV-034 (Stage 34) — Hierarchical Leiden Community Clustering & Living C4 Autonomous Wiki** [📋 Planned — Rating: 93/100]
  - **Objective**: Synthesize a living, browsable, cross-linked codebase documentation wiki powered by hierarchical Leiden community clustering and Robert C. Martin package metrics.
  - **Hierarchical Leiden Community Engine (`agtoosa/graph/community.py`)**:
    - Partitions heterogeneous knowledge graphs (code, endpoints, topics, specs, docs) into multi-tier clusters:
      $$\text{Level 1: Architectural Domains} \longrightarrow \text{Level 2: Subsystems} \longrightarrow \text{Level 3: Component Modules}$$
    - Computes modularity quality scores to eliminate isolated or degenerate subgraphs.
  - **Living C4 Architecture Wiki Generator (`agtoosa/graph/wiki.py`)**:
    - Generates `.agtoosa/wiki/` containing structured Markdown articles for each detected community.
    - Features Obsidian-compatible `[[wikilinks]]` enabling bidirectional graph browsing in Obsidian and modern Markdown editors.
    - Embeds dynamic Mermaid C4 container and component diagrams auto-generated for that specific subsystem.
  - **Robert C. Martin Package Coupling & Distance Metrics**:
    - Computes Afferent Coupling ($C_a$), Efferent Coupling ($C_e$), Instability ($I = \frac{C_e}{C_a + C_e}$), Abstractness ($A$), and Normalized Distance from the Main Sequence:
      $$D = |A + I - 1| \quad (D = 0 \text{ is optimal balance; } D \to 1 \text{ is Pain/Uselessness zone})$$
  - **Native Studio Web Integration**:
    - Adds a dedicated "Living Wiki" tab to [Agtoosa Studio Web](agtoosa/graph/web/index.html) with full-text search, community navigation, and 1-click links to the C4 visualizer and editor CodeLens.
  - **CLI & MCP Tooling**:
    - CLI: `agtoosa wiki build [--output <dir>] [--format obsidian|markdown] [--metrics] [--serve]`.
    - CLI: `agtoosa wiki metrics [--json]`.
    - MCP Tool: `agtoosa_get_architecture_wiki`.

- **DEV-035 (Stage 35) — Zero-Trust Hallucination Guard & Subagent Semantic Extraction Engine** [📋 Planned — Rating: 90/100]
  - **Objective**: Provide parallel agentic semantic extraction for non-code assets with tri-state confidence tagging, guarded by bidirectional AST symbol verification to prevent graph corruption from LLM hallucinations.
  - **Deterministic AST Baseline First (Zero Token Cost)**:
    - Never re-extracts code files using LLMs. Code structure, classes, functions, and imports are 100% indexed by native AST parsers.
  - **Parallel Subagent Extraction Coordinator**:
    - Batches non-code files (PDFs, docs, images) into balanced chunks (15–20 files) for parallel processing by AI coding agents.
    - Enforces standardized JSON output schemas matching Agtoosa2's node/edge specification.
  - **Tri-State Provenance Classification**:
    - Explicitly tags every relationship: `EXTRACTED` (verifiable syntax/citation), `INFERRED` (reasonable semantic deduction), `AMBIGUOUS` (uncertain connection flagged for review).
  - **Zero-Trust Bidirectional Grounding (`HallucinationGuard`)**:
    - Intercepts all semantic edge submissions claiming relations to code symbols.
    - Queries the SQLite symbol index: If an LLM invents a method `AuthService.verifyJwtToken()` that does not exist in AST records, the edge is flagged as `HALLUCINATED_UNVERIFIED` and suggests the closest Levenshtein fuzzy-match (`AuthService.validate_token`).
  - **Persistent SHA-256 Incremental Semantic Cache**:
    - Hashes document contents; re-indexing skips unchanged files with sub-millisecond cache hits stored in `.agtoosa/cache/semantic/`.
  - **CLI & MCP Tooling**:
    - CLI: `agtoosa extract semantic [--chunk-size <N>] [--strict-grounding] [--json]`.
    - MCP Tool: `agtoosa_validate_semantic_graph`.

- **DEV-036 (Stage 36) — Socratic Architecture Audit & 1-Click God-Node Refactoring Blueprints** [📋 Planned — Rating: 88/100]
  - **Objective**: Elevate passive graph reports into active architectural audits that discover God nodes, cyclic hotspots, and surprising cross-modality connections, attaching actionable 1-click refactoring blueprints.
  - **Automated Audit Generator (`GRAPH_REPORT.md` / `agtoosa audit`)**:
    - Synthesizes a structured report in repository root or `.agtoosa/` covering:
      - **God Nodes**: High-degree and high-betweenness centrality hubs dominating the codebase.
      - **Cyclic Hotspots**: Tarjan cycles requiring structural decoupling.
      - **Cross-Modality Latent Couplings**: Uncovers implicit dependencies between PDF requirements/specifications and code modules lacking tests or formal evidence.
  - **Actionable 1-Click Refactoring Blueprints**:
    - Connects directly with [CycleDecouplerEngine](agtoosa/refactor/decoupler.py) and [RefactorEngine](agtoosa/refactor/engine.py).
    - Attaches executable Dependency Inversion (DIP) interface extractions and safe dead-code deletion patches to every reported God node.
  - **Socratic Coding Agent Prompts**:
    - Generates tailored inquiry prompts for AI coding agents (Claude, Cursor, Antigravity) that highlight unverified assumptions before sprint execution.
  - **CLI & MCP Tooling**:
    - CLI: `agtoosa audit [--output <path>] [--format markdown|json] [--generate-blueprints]`.
    - MCP Tool: `agtoosa_get_socratic_audit`.

- **DEV-037 (Stage 37) — Universal Agent Slash Command Skill & Token-Budgeted Topology Traversal** [📋 Planned — Rating: 92/100]
  - **Objective**: Deliver a unified drop-in slash command skill across all major AI agent hosts with topology-weighted context pruning under strict token budgets.
  - **Universal Multi-Host Skill Packaging**:
    - Provides pre-configured skill bundles for:
      - **Claude Code**: `~/.claude/skills/agtoosa/SKILL.md`
      - **Antigravity / Gemini CLI**: `.agents/skills/agtoosa/SKILL.md`
      - **Cursor & Windsurf**: Rules and native MCP bindings
    - Commands: `/agtoosa ingest`, `/agtoosa query`, `/agtoosa path`, `/agtoosa explain`, `/agtoosa wiki`, `/agtoosa audit`.
  - **Token-Budgeted AST Context Pruning (`TopologyContextCompiler`)**:
    - Supports strict token constraints (`--budget <N>`, e.g., 1500 tokens).
    - Uses PageRank centrality and edge weight prioritization (`CALLS` > `IMPORTS` > `REFERENCES`) to prune ASTs into valid, compilable code skeletons (classes, signatures, type hints, docstrings) instead of naive character slicing.
  - **CLI & MCP Tooling**:
    - CLI: `agtoosa skill install [--target all|claude|cursor|gemini|antigravity]`.
    - CLI: `agtoosa query "<question>" [--budget <tokens>] [--strategy bfs|dfs|pagerank|hybrid] [--json]`.
    - MCP Tool: `agtoosa_budgeted_query`.

---

## Foundation Gate: EPIC-001 — Trusted Knowledge Intelligence (DEV-040–049)

> **Full epic:** [EPIC-001 — Trusted Knowledge Intelligence](specs/epic-001-trusted-knowledge-intelligence.md).
> **Research:** [Graphify parity and graph trust](research/2026-09-13-graphify-parity-and-trust.md) (R-01–14).

Milestone 14 expands what the graph *contains*. EPIC-001 establishes that what the graph contains is *true*, and it gates Milestone 14 rather than following it. The ordering is deliberate: a richer graph amplifies incorrect relationships as readily as correct ones, so accuracy precedes breadth across all currently supported languages.

Two corrections this epic applies to the roadmap above, recorded so they are not silently reintroduced:

- Earlier Master Plan text described Graphify as single-host, Louvain-only, and blindly trusting of semantic output. The pinned reference does not support those characterisations, and the "supersedes Graphify" framing in Milestone 14 should be read as a design intent, not a measured result.
- Graphify's published benchmark figures are conversational-memory scores. They do not establish multilingual static-analysis correctness and must not be transferred into Agtoosa2 performance claims. DEV-046 defines the evaluation that would actually support a comparison.

| Story | Title | Addresses | Depends on |
|---|---|---|---|
| **DEV-040** | Parser coverage and language adapters | R-01 | — |
| **DEV-041** | Scoped identity and honest resolution | R-02/03/05 | DEV-040 |
| **DEV-042** | Atomic snapshots, incremental equivalence, preservation | R-04/05/06 | DEV-040/041 |
| **DEV-043** | Versioned explainable interfaces | R-03/08 | DEV-040–042 |
| **DEV-044** | Verified repair and conservative dead-code actions | R-10 | DEV-043 |
| **DEV-045** | Real benchmark evidence | R-09 | DEV-043 |
| **DEV-046** | Held-out evaluation, parity ledger, release gate | R-01–11 | DEV-040–045 |
| **DEV-047** | Source rationale and decision provenance | R-12 | DEV-040/041 |
| **DEV-048** | Community detection correctness across install profiles | R-13 | DEV-042 |
| **DEV-049** | Semantic provider gateway and egress boundary | R-14 | DEV-043; gates all semantic consumers |

DEV-047–049 were added on 2026-09-14 from a second parity audit (findings R-12–14). That audit independently reproduced R-01 and raised no correction to R-01–11; its two other proposals duplicated DEV-040 and DEV-045/046 and were dropped before filing.

**Foundation gate:** AC-01–25 carry evidence, every designated ambiguous-case fixture resolves zero wrong concrete targets, and publication/migration/stale-patch/rollback regressions pass. AC-26/27 are required when the first semantic consumer ships. Milestone 14 opens only after this gate; DEV-038/039 remain deferred behind it.

---

## Future Frontiers: Milestone 15 (v0.9.0)

| Rank | Cycle ID | Title | Rating | Target Milestone | Strategic Value & Architectural Impact |
|:---:|---|---|:---:|---|---|
| 🥇 | **DEV-038** | Zero-Knowledge Architecture Cryptographic Attestation | **70 / 100** | Milestone 15 (v0.9.0) | **Cryptographic Security Proofs**: Produces cryptographically signed architectural attestations verifying compliance with layer boundary invariants without exposing proprietary source code. |
| 🥈 | **DEV-039** | Autonomous Cross-Language Microservice Synthesis | **68 / 100** | Milestone 15 (v0.9.0) | **Multi-Language Generation**: Generates strongly-typed gRPC and OpenAPI client/server adapters directly from federated multi-repo graph models. |




