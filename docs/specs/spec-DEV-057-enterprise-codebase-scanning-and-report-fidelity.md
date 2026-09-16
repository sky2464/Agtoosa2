# DEV-057: Enterprise Polyglot Noise Exclusion, Dynamic Semantics & Architecture Report Fidelity

> **Cycle:** DEV-057  
> **Milestone:** Milestone 20 (Enterprise Codebase Scale & Multi-Ecosystem Fidelity)  
> **Status:** Completed  
> **Type:** Feature  

---

## 1. Problem Statement

When scanning, parsing, indexing, and evaluating complex software architectures at scale, real-world enterprise codebases contain vast volumes of non-source noise, build output, transient artifacts, auto-generated boilerplate, dynamic runtime boundaries, and sensitive credentials:

1. **Noise Ingestion & Entity Flooding**: Without comprehensive multi-ecosystem exclusion rules, package caches (`node_modules`, `venv`, `vendor`, `.gradle`, `target`, `Pods`), build outputs (`dist`, `.next`, `.turbo`, `build`, `__pycache__`), lockfiles (`*.lock`, `go.sum`), media assets (`.svg`, video, audio, fonts), and heavy ML weights (`*.safetensors`, `*.pt`, `*.onnx`) flood the knowledge graph with thousands of synthetic or disconnected nodes, burying the team's actual code.
2. **Security & Credential Exposure**: Unfiltered scanning risks ingesting secret configuration files (`.env`, `credentials.json`, `*.pem`, `id_rsa`) or unredacted API tokens and database URIs in docstrings into local databases or AI token packs.
3. **Dynamic Semantics & AST Blind Spots**:
   - **Path Aliasing**: Modern codebases use path mappings (e.g. `tsconfig.json` `paths`, Vite/Webpack aliases, monorepo workspaces). Inability to resolve these aliases causes hundreds of valid internal imports to appear as broken or unresolved symbols.
   - **Type-Only vs Runtime Coupling**: Treating TypeScript `import type` or Python `if TYPE_CHECKING:` as runtime execution edges produces false circular dependency alarms on harmless static typing cycles.
   - **Dependency Injection & Event Lineage**: Static AST extractors fail to connect abstract interfaces to runtime-injected implementations (Spring, NestJS, FastAPI `Depends()`) and asynchronous publishers to subscribers (Kafka, RabbitMQ, Redis, SQS), incorrectly flagging active implementations as dead code.
4. **Metric Distortion & Gravity Skew**:
   - Generic utility functions (`logger.info`, `uuid`, `formatDate`) accumulate thousands of incoming calls, distorting PageRank and overshadowing critical domain aggregates.
   - Naive cycle detection across documentation links or static types penalizes healthy codebases.
   - Naive isolation checks flag passive configuration or documentation files as dead code.

---

## 2. Acceptance Criteria

- **AC-1 (Universal Exclusion Taxonomy & Noise Filtering)**: WHEN `agtoosa graph build` scans any workspace, the scanner SHALL recursively prune all package stores (`node_modules`, `venv`, `vendor`, `.gradle`, `target`, `Pods`), build/transpilation outputs (`dist`, `.next`, `.turbo`, `build`, `__pycache__`), lockfiles (`*.lock`, `package-lock.json`, `go.sum`), media assets (`.svg`, `.png`, `.jpg`, `.mp4`, `.woff`), big data files (`.parquet`, `.avro`, large `.dump`/`.sqlite`), and AI/ML model weights (`*.safetensors`, `*.pt`, `*.onnx`), ensuring zero non-code noise entities enter the knowledge graph.
- **AC-2 (Zero-Trust Security & Secrets Shield)**: WHEN discovering files, the scanner SHALL reject sensitive credential files (`.env*`, `*.pem`, `*.key`, `id_rsa*`, `service_account*.json`, `credentials.json`) and redact tokens, private keys, API keys, and connection passwords from docstrings/comments before AST node persistence.
- **AC-3 (Configurable Path Aliasing & Monorepo Workspace Resolution)**: WHEN resolving cross-file imports, the resolver SHALL ingest workspace path mappings from `tsconfig.json` (`compilerOptions.paths`), `pyproject.toml`, or monorepo package manifests, resolving aliases (e.g. `@/components/*`, `@core/*`) to canonical internal source targets rather than leaving them unresolved.
- **AC-4 (Type-Only vs Runtime Edge Disambiguation)**: WHEN parsing TypeScript (`import type`) or Python (`if TYPE_CHECKING:`), the parser SHALL categorize these edges as `EdgeType.TYPE_DEPENDS_ON` and exclude them from runtime circular dependency evaluation (`detect_cycles`), preventing type cycles from penalizing architectural health.
- **AC-5 (Dynamic DI & Event-Driven Semantic Extraction)**: WHEN source code employs Dependency Injection annotations (`@Injectable`, `@Autowired`, `Depends()`) or message broker events (Kafka, RabbitMQ, Redis, Celery, SQS), the engine SHALL bridge abstract interfaces to concrete implementations and publishers to subscribers via semantic runtime edges (`EdgeType.INJECTS`, `EdgeType.PUBLISHES`, `EdgeType.SUBSCRIBES`).
- **AC-6 (Metric Protection & Domain Hub Classification)**: WHEN computing PageRank, cycle detection, and isolated node health metrics, the engine SHALL distinguish generic infrastructure utilities (`logger`, `uuid`, `utils`) from core business domain hubs, scope cycle detection strictly to runtime code execution edges, and restrict isolated node penalties to executable code units.

---

## 3. Capability Requirements

### R-1: Multi-Ecosystem Exclusion Registry
The scanner must maintain a unified, configurable exclusion registry covering:
- **Dependency stores**: Node, Python, Go, PHP, Ruby, Java, Rust, Swift/CocoaPods.
- **Transpilation & Bundler outputs**: Webpack, Vite, Next.js, Nuxt, SvelteKit, Turbo, Parcel.
- **Lockfiles & Checksums**: npm, yarn, pnpm, bun, poetry, pipenv, cargo, composer, bundler.
- **Binary Media & Datasets**: Vector/raster graphics, fonts, audio, video, Parquet/Avro dumps, ML checkpoints.

### R-2: Path Alias & Workspace Resolver
- Parse `tsconfig.json` and `jsconfig.json` to extract `compilerOptions.baseUrl` and `paths`.
- Parse monorepo workspace configurations (`pnpm-workspace.yaml`, `lerna.json`, root `package.json` workspaces).
- Resolve aliased imports to their relative filesystem targets prior to symbol candidate matching.

### R-3: Type-Aware Edge Classification
- Differentiate between compile-time / type-checking imports and runtime imports.
- Maintain separate edge channels: `EdgeType.IMPORTS` (runtime) vs `EdgeType.TYPE_DEPENDS_ON` (type-only).
- Ensure cycle decoupling algorithms target runtime dependency cycles.

### R-4: Architectural Scorecard Protection
- Prevent passive files (documentation, project manifests, configuration) from triggering dead-code isolation deductions.
- Ensure automated test callers directly map to code verification coverage proofs.
- Attenuate ubiquitous infrastructure helpers from dominating domain centrality reports.

---

## 4. Tasks & Deliverables

- [x] **Task 57.1**: Expand `agtoosa/parser/scanner.py` with multi-ecosystem `DEFAULT_IGNORE_DIRS` and `DEFAULT_IGNORE_EXTENSIONS` for dependencies, build outputs, lockfiles, media, and ML weights.
- [x] **Task 57.2**: Implement path alias configuration reader in `agtoosa/parser/resolver.py` supporting `tsconfig.json` and monorepo workspace packages.
- [x] **Task 57.3**: Implement type-only import disambiguation in `agtoosa/parser/js_ts_parser.py` and `agtoosa/parser/python_parser.py` using `EdgeType.TYPE_DEPENDS_ON`.
- [x] **Task 57.4**: Extend `agtoosa/parser/frameworks.py` and `event_lineage.py` to bridge IoC interfaces and message broker topic linkages.
- [x] **Task 57.5**: Enhance `agtoosa/graph/metrics.py` with domain-weighted PageRank classification to separate infrastructural helpers from core business hubs.
- [x] **Task 57.6**: Add comprehensive automated test coverage in `tests/test_enterprise_scanner.py` verifying noise exclusion, path aliasing, and metric fidelity.
