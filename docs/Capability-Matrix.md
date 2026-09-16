# Agtoosa2 — Capability Matrix & Parity Definition

> **Reference Benchmark:** Graphify Open-Source Capabilities & Enterprise Graph OS.  
> **Status:** All 55 Stages Delivered & Verified (`v0.9.6`) — 100% Automated Test Pass Rate (312/312 tests passing).  
> **Milestone 14:** Stages 33–37 Delivered: Multimodal Ingestion, Living C4 Architecture Wiki, Zero-Trust Semantic Extraction, Socratic Audit, and Universal Slash Command Skill.  
> **Milestone 15:** Stages 38–39 Delivered: Zero-Knowledge Architecture Cryptographic Attestation and Autonomous Polyglot Microservice Synthesis.  
> **Milestone 17:** Stages 50–51 Delivered: Actionable Architecture Hints & Guided Workflows (DEV-050) and Human-Centric Dead-Code CLI with Emergency Rollback (DEV-051).  
> **Milestone 18:** Stages 52–55 Delivered: Algebraic & Spectral Graph Theory, Submodular Context Optimization, Discrete Differential Geometry, and Causal Architecture Inference.  
> **Foundation Gate:** [EPIC-001 — Trusted Knowledge Intelligence](specs/epic-001-trusted-knowledge-intelligence.md) (DEV-040–049) ✅ CLEARED with 100% held-out precision benchmark.

---

## Parity & Capability Mapping

| Reference Capability | Agtoosa2 Command / Interface | Stage | Supported Inputs | Primary Verification Fixture |
|---|---|---|---|---|
| **AST Symbol & Call Extraction** | `agtoosa graph build` | **Stage 1** (DEV-001) | `.py`, `.js`, `.ts`, `.sh` | `tests/test_parser.py` |
| **Transactional Graph Storage** | `.agtoosa/graph.db` | **Stage 1** (DEV-001) | SQLite + FTS5 tables | `tests/test_store.py` |
| **Keyword & Semantic Query** | `agtoosa graph query "<q>"` | **Stage 1** (DEV-001) | Text query, node filter | `tests/test_query.py` |
| **CLI & Export Formats** | `agtoosa graph export --json` | **Stage 1** (DEV-001) | JSON graph schema | `tests/test_export.py` |
| **Incremental Fingerprinting** | `agtoosa graph build` (incremental) | **Stage 2** (DEV-002) | SHA-256 content hashes | `tests/test_incremental.py` |
| **Symbol Explanation & Provenance**| `agtoosa graph explain "<symbol>"`| **Stage 2** (DEV-002) | Symbol or file path | `tests/test_explain.py` |
| **Directed Path Tracing** | `agtoosa graph path "<A>" "<B>"` | **Stage 2** (DEV-002) | Source & target nodes | `tests/test_path.py` |
| **Impact Radius Analysis** | `agtoosa graph impact "<target>"` | **Stage 2** (DEV-002) | Modified symbol / file | `tests/test_scaling.py` |
| **Lifecycle Node Ingestion** | `agtoosa spec`, `agtoosa build` | **Stage 3** (DEV-003) | Spec markdown, tasks | `tests/test_lifecycle.py` |
| **Context Compilation v2 (RAG)** | `agtoosa context compile <task>` | **Stage 3** (DEV-003) | Task ID, radius k | `tests/test_scaling.py` |
| **Mathematical Proof Validation**| `agtoosa ship verify` | **Stage 3** (DEV-003) | Story → Test → Evidence | `tests/test_proof_gate.py` |
| **Native MCP Server Tools** | `agtoosa mcp` | **Stage 4** (DEV-004) | JSON-RPC stdio/SSE | `tests/test_mcp.py` |
| **C4 Architecture Visualizer** | `agtoosa graph view` | **Stage 5** (DEV-005) | Standalone C4 Command Center | `tests/test_visualizer.py` |
| **Governance Scorecard & PageRank**| `agtoosa graph report` | **Stage 5** (DEV-005) | Tarjan cycle & PageRank | `tests/test_metrics.py` |
| **Multi-Format Graph Exports** | `agtoosa graph export --obsidian`| **Stage 5** (DEV-005) | Obsidian, GraphML, Cypher, DOT| `tests/test_export.py` |
| **Broad Language Parsers** | `agtoosa graph build` | **Stage 6** (DEV-006) | Go, Rust, Java, Kotlin, C/C++, C#, SQL DDL, Dockerfile | `tests/test_polyglot.py` |
| **Zero-Trust Security & Sandbox**| Scanner & Visualizer | **Stage 7** (DEV-007) | XSS-safe CSP, secret redaction, path traversal sandbox, .gitignore | `tests/test_security.py` |
| **High-Scale Streaming Store** | `stream_nodes()`, CTE queries | **Stage 8** (DEV-008) | O(1) memory chunked generators, recursive CTEs, compound FTS5 queries | `tests/test_scaling.py` |
| **Continuous Sync & MCP Push** | `agtoosa graph watch/hooks` | **Stage 9** (DEV-009) | Filesystem daemon, Git hooks, real-time MCP notifications | `tests/test_watcher.py` |
| **PR Diffs & Drift Alarms** | `agtoosa review --diff` | **Stage 10** (DEV-010)| Git branches, drift alarms, architectural memory bank | `tests/test_intelligence.py`|
| **CI/CD PR Gate & Action** | `agtoosa-action`, `agtoosa ci` | **Stage 11** (DEV-011)| GitHub Action, PR impact comment, merge blocking | `tests/test_ci_gate.py` |
| **Standalone Distribution** | PyPI, Homebrew, standalone binary | **Stage 12** (DEV-012)| PyInstaller/uv binary, homebrew tap, PyPI wheel | `tests/test_distribution.py`|
| **IDE Extension Integration** | VS Code / Cursor extension | **Stage 13** (DEV-013)| Editor tree view, code lens, real-time blast radius | `tests/test_extension.py` |
| **Hybrid GraphRAG v2** | `agtoosa context compile --hybrid`| **Stage 14** (DEV-014)| Dense subword embeddings, FTS5 BM25, RRF rank fusion, SQLite BLOBs | `tests/test_hybrid_rag.py` |
| **Cross-Repo Graph Federation** | `agtoosa graph federate` | **Stage 15** (DEV-015)| Multi-repo git shallow clone, OpenAPI/gRPC/GraphQL contract bindings, cross-service impact | `tests/test_federation.py` |
| **Monorepo Package Boundaries** | `agtoosa review boundaries` | **Stage 16** (DEV-016)| npm/pnpm/Cargo/Python workspace discovery, encapsulation leaks, package cycles | `tests/test_monorepo.py` |
| **Runtime Observability & Latency**| `agtoosa telemetry traces` | **Stage 17** (DEV-017)| OpenTelemetry span / profiler ingestion, execution latency heatmaps | `tests/test_telemetry.py` |
| **Production Blast Radius** | `agtoosa graph impact --traffic` | **Stage 18** (DEV-018)| Live telemetry traffic weighting, error rates, risk multipliers | `tests/test_production_impact.py` |
| **Autonomous Cycle Decoupler** | `agtoosa refactor decouple` | **Stage 19** (DEV-019)| Automated Dependency Inversion (DIP) interface extraction blueprints | `tests/test_decoupler.py` |
| **Dead Code & Zombie Pruning** | `agtoosa refactor dead-code` | **Stage 20** (DEV-020)| Unreachable AST symbol pruning, confidence scoring, safe deletions | `tests/test_dead_code.py` |
| **Modular Native Studio Web** | `agtoosa graph view --serve` | **Stage 21** (DEV-021)| Zero-build tool modular web assets (<250 lines), HTML5 Canvas, Cytoscape | `tests/test_studio_server.py` |
| **Autonomous AST Patch Engine** | `agtoosa refactor [--apply]` | **Stage 22** (DEV-022)| Atomic backup snapshots, AST rewriting, rollback engine | `tests/test_refactor_engine.py` |
| **Two-Way Studio Actions** | Web UI Refactor Buttons | **Stage 23** (DEV-023)| Browser REST endpoints (`/api/refactor/prune`, `/api/refactor/decouple`) | `tests/test_studio_server.py` |
| **Pre-Push Guard Daemon** | `agtoosa guard [--daemon]` | **Stage 24** (DEV-024)| Sub-millisecond status cache `.agtoosa/guard_status.json`, pre-push blocker | `tests/test_guard.py` |
| **Framework DI & Dynamic Routes** | `agtoosa graph routes/di` | **Stage 25** (DEV-025)| FastAPI, Flask, NestJS, Express DI resolvers & ORM relation mapping | `tests/test_framework_semantics.py` |
| **Async Event Bus Lineage** | `agtoosa graph events` | **Stage 26** (DEV-026)| Kafka, RabbitMQ, Redis Pub/Sub, Celery, BullMQ queue lineage | `tests/test_event_lineage.py` |
| **In-Editor Gutter CodeLens** | VS Code / Cursor Extension | **Stage 27** (DEV-027)| Gutter telemetry heatmaps, 1-click QuickFix refactor actions, `.vsix` | `tests/test_extension.py` |
| **C4 Architecture-as-Code** | `agtoosa c4 export/sync` | **Stage 28** (DEV-028)| Mermaid, PlantUML, Structurizr DSL live doc sync & CI drift linter | `tests/test_c4.py` |
| **PR Blast Radius Review Bot** | `agtoosa ci pr-bot` | **Stage 29** (DEV-029)| Multi-dimensional PR diff analyzer, sticky PR markdown comments | `tests/test_pr_bot.py` |
| **Distributed Trace Topology** | `agtoosa telemetry traces` | **Stage 30** (DEV-030)| OTLP, Jaeger, Zipkin cross-service span hierarchy & AST endpoint stitching | `tests/test_distributed_traces.py` |
| **AI Automated PR Repair Agent** | `agtoosa ci repair` | **Stage 31** (DEV-031)| Autonomous PR branch commits applying verified AST refactor patches | `tests/test_pr_repair.py` |
| **Multimodal Ingestion & Visual Drift**| `agtoosa ingest / add` | **Stage 33** (DEV-033) [✅] | PDFs, research papers, whiteboard sketches, visual-to-code drift detection | `tests/test_multimodal_drift.py` |
| **Hierarchical Leiden Living Wiki**| `agtoosa wiki build` | **Stage 34** (DEV-034) [✅] | Modularity community detection, living C4 Wiki, Martin package metrics | `tests/test_living_wiki.py` |
| **Zero-Trust Hallucination Guard**| `agtoosa extract semantic` | **Stage 35** (DEV-035) [✅] | Subagent parallel extraction, tri-state confidence, bidirectional AST grounding | `tests/test_semantic_extraction.py` |
| **Socratic Audit & Refactor Plans**| `agtoosa audit` | **Stage 36** (DEV-036) [✅] | `GRAPH_REPORT.md`, God nodes, cross-modality links, 1-click refactor blueprints | `tests/test_socratic_audit.py` |
| **Universal Slash Command Skill** | `/agtoosa`, `--budget` | **Stage 37** (DEV-037) [✅] | Universal skill (Claude, Cursor, Gemini, Antigravity), AST topology pruning | `tests/test_universal_skill.py` |
| **Zero-Knowledge Architecture Attestation** | `agtoosa attest` | **Stage 38** (DEV-038) [✅] | Salted blind commitments, Merkle proofs, layer boundary & cycle attestation | `tests/test_attestation.py` |
| **Autonomous Microservice Synthesis** | `agtoosa synthesize` | **Stage 39** (DEV-039) [✅] | gRPC .proto, OpenAPI 3.0, polyglot server/client adapters (Python, TS, Go) | `tests/test_synthesis.py` |

---

## Foundation Gate — EPIC-001 (DEV-040–049)

These stories establish that indexed relationships are accurate before the matrix above can claim parity. Full detail in [EPIC-001](specs/epic-001-trusted-knowledge-intelligence.md); findings in [research R-01–14](research/2026-09-13-graphify-parity-and-trust.md).

| Capability | Story | Finding | Verified evidence |
|---|---|---|---|
| Grammar-backed parser adapters & capability registry | **DEV-040** [✅] | R-01 | `tests/test_parser_capabilities.py`, `agtoosa/parser/capabilities.py` |
| Scoped identity, candidate sets, no guessed action targets | **DEV-041** [✅] | R-02/03/05 | `tests/test_symbol_resolution.py`, `agtoosa/parser/resolver.py` |
| Atomic snapshot publication & manual-record preservation | **DEV-042** [✅] | R-04/05/06 | `tests/test_snapshot_integrity.py`, `agtoosa/graph/store.py` |
| Versioned explainable result envelope | **DEV-043** [✅] | R-03/08 | `tests/test_graph_contract.py`, `agtoosa graph capabilities`, `agtoosa graph verify` |
| Verified repair with rollback | **DEV-044** [✅] | R-10 | `tests/test_repair_verification.py`, `agtoosa/repair/agent.py` |
| Real benchmark evidence (no synthetic substitution) | **DEV-045** [✅] | R-09 | `tests/test_benchmark.py`, `agtoosa/benchmark/harness.py` |
| Held-out evaluation & parity ledger | **DEV-046** [✅] | R-01–11 | `scripts/evaluate_graph_quality.py`, version reconciled to 0.6.0 |
| Source rationale & decision provenance | **DEV-047** [✅] | R-12 | `tests/test_rationale.py`, `agtoosa/parser/rationale.py` |
| Community detection correctness across install profiles | **DEV-048** [✅] | R-13 | `tests/test_communities.py`, `agtoosa/graph/community.py` |
| Semantic provider gateway & egress boundary | **DEV-049** [✅] | R-14 | `tests/test_semantic_gateway.py`, `agtoosa/semantic/gateway.py` |
| **Actionable Architecture Hints & Guided Workflows** | **DEV-050** [✅] | DX-01 | `tests/test_metrics.py`, `docs/specs/spec-DEV-050-actionable-hints-and-guided-workflows.md`, `agtoosa/graph/metrics.py` |
| **Human-Centric Dead-Code CLI & Dry-Run Preview** | **DEV-051** [✅] | DX-02 | `tests/test_dead_code.py`, `docs/specs/spec-DEV-051-dead-code-cli-ux.md`, `agtoosa/refactor/dead_code.py` |
| **Algebraic & Spectral Graph Theory Core** | **DEV-052** [✅] | M18 | `tests/test_spectral.py`, `agtoosa/graph/spectral.py`, Laplacian $\mathcal{L}$, Cheeger cuts, resolvent shockwaves |
| **Submodular Context Optimization** | **DEV-053** [✅] | M18 | `tests/test_submodular.py`, `tests/test_hybrid_rag.py`, `agtoosa/core/submodular.py`, $(1 - 1/e)$ knapsack bounds |
| **Discrete Differential Geometry & Curvature** | **DEV-054** [✅] | M18 | `tests/test_curvature.py`, `tests/test_metrics.py`, `agtoosa/graph/curvature.py`, Forman-Ricci $\mathbf{Ric}_F(e)$, Gromov $\delta$ |
| **Causal Architecture Inference & Pearl's Do-Calculus** | **DEV-055** [✅] | M18 | `tests/test_causal.py`, `agtoosa/observability/causal.py`, SCMs, Back-Door criterion, ACE |

### Verified record status


| Item | Status |
|---|---|
| Package version vs. roadmap label | ✅ Reconciled: `pyproject.toml`, `agtoosa.__version__`, and VS Code extension aligned to `0.9.5`. |
| "Semantic" vector search | ✅ Accurately labelled as token/character n-gram feature hashing in `HashedFeatureEmbeddingEngine` with explicit algorithm metadata (R-08 / DEV-043). |
| Foundation Gate Invariants | ✅ Cleared: 311 automated tests passing; evaluation runner achieves 100% precision with 0 false concrete guesses. Milestones 14, 15, 17, and 18 unlocked. |
