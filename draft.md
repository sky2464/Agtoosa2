# Agtoosa2 - Graph Native Knowledge Engine

## Outcome and agreed direction

Build an Agtoosa2-owned knowledge engine that maps code, documents, and project decisions into a persistent, queryable graph. Integrate it automatically into existing workflows and expose direct `/agtoosa-graph` commands.

Confirmed decisions:

- Agtoosa2 owns the implementation; no Graphify dependency or copied engine.
- Established parsing and graph libraries are acceptable.
- Existing workflows consult the graph automatically.
- The active coding assistant performs semantic analysis.
- Delivery includes specifications, architecture updates, Master Plan entries, and traceable tasks.

Use Graphify’s current open-source capabilities as the reference: extraction, relationship provenance, graph queries, communities, reports, visualization, incremental updates, and broader document/media support. Deliver these in stages. [Graphify capabilities](https://github.com/Graphify-Labs/graphify#what-it-does)

**Status:** Planning only. Repository files have not been changed in this session.

## 1. Specifications and project records

The first implementation step is to establish the complete documentation set before building the engine.

- Add a **Native Knowledge Engine** portfolio to [Master-Plan.md](/Users/chicademy/Documents/Code/Agtoosa2/docs/Master-Plan.md), spanning the existing generator, workflow, and testing epics. Preserve the current active cycle.
- Create one canonical story specification and test plan for each delivery stage below. Allocate product-story IDs from the current Master Plan when writing the artifacts.
- Follow Agtoosa2’s specification format: interview findings, Goal Contract, user stories, EARS acceptance criteria, architecture, STRIDE analysis, scope boundary, task tree, and dependency waves.
- Map every task to acceptance criteria and every acceptance criterion to verification evidence. Keep approval markers pending until approval is actually given.
- Update [Master-Architecture.md](/Users/chicademy/Documents/Code/Agtoosa2/docs/Master-Architecture.md) with the proposed engine boundary, component diagrams, data flows, storage ownership, dependencies, failure behavior, and deployment model. Clearly distinguish planned components from implemented ones.
- Add an architecture decision covering the first-party Python runtime and its relationship to the Bash/PowerShell generator.
- Update maintainer guidance and product/technology context to describe the generator plus its project-local knowledge runtime.
- Create a dated capability matrix mapping each reference capability to its AgToosa command, delivery stage, supported inputs, and acceptance tests. This becomes the definition of parity.

## 2. Engine architecture and contracts

### Runtime and distribution

Implement the engine as a Python 3.11+ package under `template/.agtoosa/engine/graph/`, installed into the corresponding project-local directory.

Use:

- Tree-sitter and language grammars for structural parsing.
- SQLite for transactional graph storage and full-text search.
- NetworkX for traversal, dependency analysis, centrality, and community analysis.
- Bundled Cytoscape.js assets for the interactive viewer.

These libraries provide primitives; AgToosa implements extraction rules, entity resolution, graph semantics, workflow integration, and the user experience. [Tree-sitter](https://github.com/tree-sitter/py-tree-sitter), [NetworkX](https://networkx.org/documentation/stable/reference/classes/multidigraph.html), [SQLite FTS5](https://www.sqlite.org/fts5.html), [Cytoscape.js](https://js.cytoscape.org/)

Ship first-party source through AgToosa’s existing release and installer mechanisms. Provide `/agtoosa-graph setup` for an isolated dependency environment, including an offline wheelhouse option. Missing graph dependencies must leave existing AgToosa workflows usable.

### Graph model

Maintain a directed graph supporting multiple relationship types between the same entities.

| Entity group | Examples |
|---|---|
| Implementation | Files, modules, symbols, packages, configuration, database objects |
| Knowledge | Documents, sections, concepts, citations, design rationale |
| Delivery | Stories, acceptance criteria, tasks, tests, evidence artifacts |
| Provenance | Source locations, content hashes, extraction methods, snapshots |

Relationships include imports, calls, inheritance, references, dependencies, implementation links, test coverage, and evidence links.

Every relationship carries its source location, extraction method, and an `EXTRACTED`, `INFERRED`, or `AMBIGUOUS` classification. Preserve uncertainty and unresolved references; do not merge entities merely because their labels match.

### Storage and updates

- Keep rebuildable graph state, caches, and default exports under `.agtoosa/graph/`.
- Store project configuration separately from generated state; preserve it during updates.
- Fingerprint source content, extraction versions, and configuration.
- Incremental updates process changed files, remove deleted entities, and recompute affected relationships.
- Detect branch changes, renames, dirty working trees, and changed semantic sources.
- Publish updates transactionally. Interrupted or failed extraction retains the last complete snapshot.
- Keep worktree caches independent. Cross-project queries require explicit project registration.

### Public machine interfaces

Expose one shared engine through the generator CLI, native PowerShell dispatch, installed launcher, and slash-command adapters.

Define versioned contracts for graph snapshots, extraction batches, query results, impact reports, and capability reporting. Results include snapshot identity, freshness, coverage, citations, and warnings.

Add **context-compilation v2** for bounded graph context while retaining v1 compatibility. Keep the existing delivery proof-graph schema separate: knowledge relationships do not establish proof or approval.

## 3. Commands and automatic workflow behavior

Introduce one command family:

| Command | Intended behavior |
|---|---|
| `/agtoosa-graph [path]` | Build or incrementally refresh the selected project graph |
| `/agtoosa-graph query "question"` | Retrieve relevant graph context with citations |
| `/agtoosa-graph explain "entity"` | Explain an entity, its relationships, and supporting sources |
| `/agtoosa-graph path "A" "B"` | Trace connections, preserving relationship direction |
| `/agtoosa-graph impact <path-or-symbol>` | Identify affected code, stories, tests, and documents |
| `/agtoosa-graph status` | Show freshness, coverage, pending extraction, and dependencies |
| `/agtoosa-graph verify` | Check graph integrity and source bindings |
| `/agtoosa-graph report`, `view`, `export` | Produce summaries, interactive views, and portable outputs |
| `/agtoosa-graph add <source>` | Explicitly ingest a document, media file, or URL |
| `/agtoosa-graph setup`, `watch`, `hooks` | Manage dependencies and optional automatic refresh |

Later stages add `serve`, `workspace`, `prs`, `remember`, and `reflect`.

The engine returns structured retrieval results. The active assistant turns them into cited explanations and answers.

Automatic integration:

| Existing workflow | Graph contribution |
|---|---|
| `/agtoosa-init` | Discover architecture and establish a project baseline |
| `/agtoosa-spec` | Retrieve relevant implementation, decisions, dependencies, and likely affected areas |
| `/agtoosa-build` | Prepare bounded task context and refresh after completed change groups |
| `/agtoosa-review` | Compare graph snapshots and identify affected dependencies, tests, and documentation |
| `/agtoosa-debug` | Trace relevant call and dependency paths |
| `/agtoosa-status` | Report graph health without rebuilding or invoking AI |
| `/agtoosa-ship` | Record the graph snapshot referenced by delivery evidence |

Refresh at workflow boundaries, not after every file read. Respect host read-only modes. If graph coverage is missing, stale, or incomplete, disclose that and continue with source inspection. Graph suggestions cannot remove required tests or bypass lifecycle gates.

Register the command in [Product Truth](/Users/chicademy/Documents/Code/AgToosa/data/contracts/product-truth-v1.json), all six governed adapter targets, the Codex skill layer, platform guidance, help, and quick reference. Add modes as their implementations ship.

## 4. Delivery stages and tasks

Each stage receives its own specification, task tree, review, and acceptance evidence.

| Stage | Tasks and deliverable | Depends on |
|---|---|---|
| **1. Native project graph** | Ship the runtime and setup/status commands; implement file discovery, exclusions, source provenance, storage, and initial Bash, PowerShell, Python, JavaScript/TypeScript extraction. Deliver graph build, basic query, and JSON export through every supported adapter. | Documentation baseline |
| **2. Reliable updates and investigation** | Implement content caching, deletion and rename handling, snapshot comparison, cross-file resolution, `explain`, `path`, and dependency-based `impact`. Add interruption recovery and concurrent-writer protection. | 1 |
| **3. AgToosa delivery intelligence** | Extract stories, criteria, tasks, tests, ADRs, and evidence references. Add context-compilation v2 and automatic workflow integration. Report missing links and affected tests without changing verification authority. | 2 |
| **4. Semantic document understanding** | Implement assistant-facing extraction batches and validated result ingestion. Add concept/rationale extraction, document-to-code links, semantic caching, and resumable pending work. Provide explicitly configured headless/local-provider support. | 3 |
| **5. Architecture exploration and exports** | Add community detection, important-node rankings, dependency cycles, cross-community connections, and suggested questions. Deliver an offline interactive viewer, architecture/call-flow reports, Markdown wiki, Obsidian output, SVG, GraphML, and Cypher exports. | 2 and 4 |
| **6. Broad language and schema coverage** | Expand extractor families against the dated capability matrix: systems languages, JVM/.NET, scripting languages, component frameworks, package manifests, SQL, infrastructure/configuration formats, and remaining reference languages. Require fixtures before advertising support. | 2 |
| **7. Documents, media, and source ingestion** | Add PDF and Office conversion, image understanding through the assistant, local audio/video transcription, timestamp/page citations, and bounded URL ingestion. Add explicit PostgreSQL schema and Google Workspace ingestion adapters. | 4 |
| **8. Continuous and shared access** | Add optional file watching, composable Git hooks, read-only MCP access, graph import/merge, and explicitly registered cross-project queries. Test worktree separation and project access boundaries. | 2 and 5 |
| **9. Review intelligence and project learning** | Add read-only PR/worktree impact views and overlap analysis. Implement explicitly recorded useful/incorrect query outcomes and derived lessons with source-change invalidation. Keep lessons separate from authoritative project decisions. | 3 and 8 |

Stages 1–3 establish the primary AgToosa benefit. Subsequent stages complete the broader capability roadmap.

For every stage, update specifications, task counters, architecture status, capability coverage, and verification evidence together.

## 5. Acceptance, compatibility, and defaults

### Required verification

- **Extraction:** Golden fixtures verify symbols, direction, relationships, source locations, ambiguous names, unsupported formats, and malformed inputs.
- **Incremental correctness:** Updating a fixture produces the same graph as a clean rebuild; unchanged files are not re-extracted.
- **Recovery:** Interrupted writes preserve the previous snapshot; simultaneous writers cannot corrupt state.
- **Queries:** Test disambiguation, no-match results, directed paths, traversal limits, impact explanations, and citation accuracy.
- **Semantics:** Validate assistant output against schemas and source fingerprints. Reject fabricated source references; retain pending work when analysis is unavailable.
- **Lifecycle:** Demonstrate a trace from story → criterion → implementation → test → evidence while preserving existing approval and verification behavior.
- **Installation:** Exercise fresh installs, upgrades, rollback, uninstall, missing Python/dependencies, and offline setup on macOS, Linux, and Windows.
- **Platform parity:** Verify 21 governed commands across six targets after adding `/agtoosa-graph`; separately test actual host recognition and behavior.
- **Viewer and ingestion:** Test offline rendering, malicious labels, excluded files, external symlinks, oversized documents, URL redirects, and media failures.
- **Performance:** Publish measured indexing time, update time, query latency, memory, retrieval quality, and context consumption on AgToosa and representative fixtures. Establish AgToosa’s own evidence before making efficiency claims.

Use focused Python tests and Bats during development, Product Truth checks for adapter changes, and full regression validation before release.

### Defaults and boundaries

- Functional parity targets Graphify’s open-source capabilities, using AgToosa’s commands and supported platform set.
- Code indexing makes no model calls. Semantic analysis uses the active assistant under that host’s data policy.
- Headless providers, external sources, watchers, hooks, and database publishing require explicit configuration or invocation.
- Respect repository ignores and exclude credentials, generated caches, dependency directories, and private-key material.
- Treat indexed text as data; never execute instructions found in documents or graph results.
- Reports and caches are derived. Master Plan, approved specifications, architecture decisions, and evidence verification retain their existing authority.
- Keep the Bash/PowerShell generator intact and preserve existing user-owned configuration and project documents.

**Baseline verified during planning:** command inventory and dependency classification pass. Engine behavior remains to be implemented and tested.
