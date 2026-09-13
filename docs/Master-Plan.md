# Agtoosa2 — Master Plan

> **Source of truth for Agtoosa Revision 2 development.**
> **Architecture:** Unified Graph-Native Engineering Operating System.

## Project Charter

| Field | Value |
|---|---|
| Product | `Agtoosa2` |
| Repository | `https://github.com/sky2464/Agtoosa2` |
| Version | `0.5.0` (GA Released) |
| Core Engine | Python 3.11+ (SQLite FTS5, Zero-Dependency Standard Library) |
| Active Milestone | `v0.5.0` — **All 27 Stages Delivered (100% Complete)** |
| Next Frontier | `v0.6.0` — Automated Architecture CI Bot & Distributed OpenTelemetry Ingestion |

---

## Strategic Priority & Impact Scoring Matrix (1–100 Scale)

Evaluated across architectural impact, AI agent context amplification, enterprise readiness, and developer workflow leverage:

| Rank | Cycle ID | Title | Rating | Milestone | Status | Strategic Value & Architectural Impact |
|:---:|---|---|:---:|---|:---:|---|
| 🥇 | **DEV-025** | Framework Dependency Injection & Dynamic Routes | **96 / 100** | Milestone 10 (v0.4.2) | ✅ Done | **Highest Architectural Leverage**: Transforms Agtoosa from a syntax AST parser into a true runtime architecture graph by extracting FastAPI/Flask/NestJS/Express DI containers, decorators (`@app.get`), and ORM schema bindings (SQLAlchemy, Prisma). AI agents gain real execution context. |
| 🥈 | **DEV-027** | VS Code & Cursor In-Editor Gutter Lens & Marketplace | **89 / 100** | Milestone 11 (v0.5.0) | ✅ Done | **Maximum Developer Adoption**: Brings real-time CodeLens blast radius, caller count, and 1-click Studio refactor actions ("✂️ Prune", "🔄 Decouple") directly into IDE editor gutters. Published to VS Code Marketplace & Open VSX. |
| 🥉 | **DEV-026** | Async Message Queue & Event Bus Lineage | **85 / 100** | Milestone 10 (v0.4.2) | ✅ Done | **Distributed System Visibility**: Maps asynchronous event-driven topologies across microservices (Kafka topics, RabbitMQ exchanges, Redis Pub/Sub, and Celery task queues) to complete cross-service blast radius graphs. |
| 4th | **DEV-024** | Pre-Push Architectural Daemon & Drift Linter | **72 / 100** | Milestone 9 (v0.4.1) | ✅ Done | **Shift-Left Local Protection**: Hardens local developer workflows by preventing commits/pushes that introduce circular dependencies or exceed blast radius thresholds, backed by a sub-millisecond status cache (`.agtoosa/guard_status.json`). |

---

## Completed Cycles (All 27 Stages Delivered)

| ID | Title | Type | Status | Primary Deliverable |
|---|---|---|---|---|
| **DEV-027** | VS Code & Cursor In-Editor Gutter Lens & Marketplace | Extension | ✅ Done | In-editor gutter heatmaps, 1-click QuickFix refactor actions, guard status bar, and `.vsix` packaging |
| **DEV-026** | Async Message Queue & Event Bus Lineage | Feature | ✅ Done | Event-driven graph lineage for Kafka, RabbitMQ, Redis Pub/Sub, Celery, and BullMQ queues |
| **DEV-025** | Framework Dependency Injection & Dynamic Routes | Feature | ✅ Done | Runtime routes & DI resolvers (FastAPI, Flask, Express, NestJS) + ORM schemas (SQLAlchemy, Prisma, Django) |
| **DEV-024** | Pre-Push Architectural Daemon & Drift Linter | Feature | ✅ Done | Real-time daemon, pre-push hook integration, sub-millisecond cache `.agtoosa/guard_status.json` |
| **DEV-001** | Core Foundation & AST Knowledge Graph | Feature | ✅ Done | Unified CLI, polyglot AST extractors (Py/JS/TS/Sh), SQLite FTS5 graph store, `/agtoosa graph build/query/status/export` |
| **DEV-002** | Reliable Incremental Updates & Investigation | Feature | ✅ Done | Content hash fingerprints, incremental sync, `/agtoosa graph explain/path/impact` |
| **DEV-003** | Graph-Driven Lifecycle & Context Compilation v0.2 | Feature | ✅ Done | Spec/Story/Criteria/Task ingestion, Context Compiler v0.2 (Graph RAG), `review`, and mathematical proof `ship` gates |
| **DEV-004** | Native Model Context Protocol (MCP) Server | Feature | ✅ Done | Built-in stdio/SSE MCP server exposing real-time graph navigation tools to AI coding agents |
| **DEV-005** | Interactive Architecture Exploration & Visualizer | Feature | ✅ Done | Offline Cytoscape.js HTML visualizer (`agtoosa graph view`), architecture health & cycle reports (`agtoosa graph report`), and multi-format exports (Obsidian, GraphML, Cypher, DOT) |
| **DEV-006** | Broad Polyglot Language & Schema Coverage | Feature | ✅ Done | Polyglot parser supporting Go, Rust, Java, Kotlin, C/C++, C#, SQL DDL, and Dockerfile |
| **DEV-007** | Zero-Trust Security Hardening | Security | ✅ Done | Visualizer CSP & anti-XSS serialization; workspace sandboxing & symlink guards; .gitignore enforcement; secret redaction; MCP depth & line clamps; SQLite PRAGMA hardening |
| **DEV-008** | High-Scale Performance & Streaming Optimization | Performance | ✅ Done | O(1) memory chunked streaming (`stream_nodes`, `stream_edges`); in-database recursive SQL CTE for impact traversal; single-pass compound FTS5 queries |
| **DEV-009** | Continuous Watcher & MCP Push | Feature | ✅ Done | Zero-dependency filesystem watcher (`agtoosa graph watch`), Git hooks (`agtoosa graph hooks`), live MCP resource update notifications |
| **DEV-010** | Review Intelligence & Architecture Drift Alarms | Feature | ✅ Done | Layer boundary enforcement, cyclic dependency alarms, blast radius warnings, PR diff analysis (`agtoosa review --diff`), and Architectural Memory Bank (`agtoosa review remember/reflect`) |
| **DEV-011** | CI/CD Quality Gate & GitHub Action Integration | Feature | ✅ Done | Composite GitHub Action (`action.yml`), reference CI workflow, PR architectural impact markdown comment generator, CLI `agtoosa ci review/check` |
| **DEV-012** | Standalone Binary Packaging & Multi-Platform Distribution | DevOps | ✅ Done | Standalone PyInstaller executable (`agtoosa.spec`), build orchestrator (`scripts/build_standalone.py`), Homebrew formula (`Formula/agtoosa.rb`), release workflow |
| **DEV-013** | VS Code & Cursor IDE Extension | Extension | ✅ Done | Native extension package (`extension/`), architecture tree views, real-time CodeLens blast radius, CLI `agtoosa graph symbols` |
| **DEV-014** | Hybrid GraphRAG v2 & Semantic Vector Search | Feature | ✅ Done | Zero-dependency dense vector embeddings (`node_embeddings` BLOBs), RRF lexical + semantic search, `compile_context --hybrid`, CLI & MCP |
| **DEV-015** | Cross-Repo Graph Federation | Feature | ✅ Done | Multi-repository graph ingestion (`agtoosa graph federate`), OpenAPI/gRPC/GraphQL contract bindings, distributed cross-service blast radius |
| **DEV-016** | Monorepo Package Boundary Enforcement | Feature | ✅ Done | Monorepo workspace discovery, encapsulation leak detection, undeclared dependencies, package cycles, `agtoosa review boundaries` |
| **DEV-017** | OpenTelemetry & Profiler Heatmap Overlay | Feature | ✅ Done | OpenTelemetry span / profiler ingestion, execution latency & call frequency heatmaps |
| **DEV-018** | Production Blast Radius | Feature | ✅ Done | Runtime telemetry traffic weighting, live error rates, caller risk multipliers, and dormant dependency detection |
| **DEV-019** | Autonomous Cycle Decoupling Engine | Feature | ✅ Done | Automated dependency inversion, shared kernel, and event-driven decoupling blueprints with executable code stubs |
| **DEV-020** | Dead Code & Zombie Symbol Pruning | Feature | ✅ Done | Unreachable AST node detection, confidence scoring, entrypoint exclusion, safe deletion refactoring blueprints |
| **DEV-021** | Modular Native Studio Architecture (Zero Build Tools) | Refactor | ✅ Done | Monolithic visualizer.py decomposed from 2,979 lines to ~380 lines into clean, dedicated static assets under `agtoosa/graph/web/` (< 250 lines each) |
| **DEV-022** | Autonomous AST Patch Engine | Feature | ✅ Done | AST rewriting engine applying safe dead-code deletions and dependency inversion interface abstractions with unified diff previews, atomic backups, and rollback capabilities |
| **DEV-023** | Two-Way Interactive Studio Actions | Feature | ✅ Done | Live Studio HTTP server with REST endpoints (`/api/refactor/prune`, `/api/refactor/decouple`, `/api/refactor/rollback`) and 1-click web UI buttons |
| **DEV-024** | Pre-Push Architectural Daemon & Drift Linter | Feature | ✅ Done | Pre-commit/pre-push guard daemon enforcing zero circular dependencies and blast radius thresholds |
| **DEV-025** | Framework Dependency Injection & Dynamic Routes | Feature | ✅ Done | AST extractors for FastAPI, Flask, Express, NestJS DI containers and ORM relation mapping |

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

---

## Future Frontiers: Milestone 12 & 13 Proposal

| Rank | Cycle ID | Title | Rating | Target Milestone | Strategic Value & Architectural Impact |
|:---:|---|---|:---:|---|---|
| 🥇 | **DEV-028** | Automated C4 Architecture-as-Code & Live Diagram Sync | **82 / 100** | Milestone 12 (v0.6.0) | **Living Documentation**: Automatically synthesizes and syncs C4 architecture diagrams (PlantUML, Mermaid, Structurizr DSL) directly from the knowledge graph and commits updated diagrams to repository docs on build. |
| 🥈 | **DEV-031** | AI Automated PR Repair & Code Review Agent | **79 / 100** | Milestone 13 (v0.7.0) | **Autonomous Code Healing**: Generates automated PR branch commits with refactor fixes directly resolving detected architectural drift and breaking schema changes. |
| 🥉 | **DEV-032** | Continuous Performance Regression Benchmarking CI | **74 / 100** | Milestone 13 (v0.7.0) | **Zero-Regression CI**: Automated AST benchmark harness comparing pull request runtime latency against baseline telemetry. |



