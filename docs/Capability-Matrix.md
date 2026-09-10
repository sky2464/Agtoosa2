# Agtoosa2 — Capability Matrix & Parity Definition

> **Reference Benchmark:** Graphify Open-Source Capabilities.  
> **Status:** Stages 1–5 complete; Stage 6 (DEV-006) in active delivery; Stages 7–9 mapped.

---

## Parity & Capability Mapping

| Reference Capability | Agtoosa2 Command / Interface | Stage | Supported Inputs | Primary Verification Fixture |
|---|---|---|---|---|
| **AST Symbol & Call Extraction** | `agtoosa graph build` | **Stage 1** (DEV-001) | `.py`, `.js`, `.ts`, `.sh` | `tests/fixtures/polyglot_sample/` |
| **Transactional Graph Storage** | `.agtoosa/graph.db` | **Stage 1** (DEV-001) | SQLite + FTS5 tables | `tests/test_store.py` |
| **Keyword & Semantic Query** | `agtoosa graph query "<q>"` | **Stage 1** (DEV-001) | Text query, node filter | `tests/test_query.py` |
| **CLI & Export Formats** | `agtoosa graph export --json` | **Stage 1** (DEV-001) | JSON graph schema | `tests/test_export.py` |
| **Incremental Fingerprinting** | `agtoosa graph build` (incremental) | **Stage 2** (DEV-002) | SHA-256 content hashes | `tests/test_incremental.py` |
| **Symbol Explanation & Provenance**| `agtoosa graph explain "<symbol>"`| **Stage 2** (DEV-002) | Symbol or file path | `tests/test_explain.py` |
| **Directed Path Tracing** | `agtoosa graph path "<A>" "<B>"` | **Stage 2** (DEV-002) | Source & target nodes | `tests/test_path.py` |
| **Impact Radius Analysis** | `agtoosa graph impact "<target>"` | **Stage 2** (DEV-002) | Modified symbol / file | `tests/test_impact.py` |
| **Lifecycle Node Ingestion** | `agtoosa spec`, `agtoosa build` | **Stage 3** (DEV-003) | Spec markdown, tasks | `tests/test_lifecycle_graph.py`|
| **Context Compilation v2 (RAG)** | `agtoosa context compile <task>` | **Stage 3** (DEV-003) | Task ID, radius k | `tests/test_context_compiler.py`|
| **Mathematical Proof Validation**| `agtoosa ship verify` | **Stage 3** (DEV-003) | Story → Test → Evidence | `tests/test_proof_gate.py` |
| **Native MCP Server Tools** | `agtoosa mcp` | **Stage 4** (DEV-004) | JSON-RPC stdio/SSE | `tests/test_mcp_server.py` |
| **Interactive Graph Visualizer** | `agtoosa graph view` | **Stage 5** (DEV-005) | Cytoscape.js web bundle | `tests/test_visualizer.py` |
| **Community Clustering & PageRank**| `agtoosa graph report` | **Stage 5** (DEV-005) | NetworkX algorithms | `tests/test_metrics.py` |
| **Markdown Wiki / Obsidian Export**| `agtoosa graph export --obsidian`| **Stage 5** (DEV-005) | Markdown vault | `tests/test_obsidian_export.py`|
| **Broad Language Parsers** | `agtoosa graph build` | **Stage 6** (DEV-006) | Rust, Go, Java, C/C++, SQL | `tests/fixtures/languages/` |
| **Document & PDF Parsing** | `agtoosa graph add <file>` | **Stage 7** (DEV-007) | PDF, Docx, Markdown | `tests/test_doc_parser.py` |
| **Filesystem Watcher & Hooks** | `agtoosa graph watch/hooks` | **Stage 8** (DEV-008) | File events, Git hooks | `tests/test_watcher.py` |
| **PR Diffs & Architectural Memory**| `agtoosa graph prs/remember` | **Stage 9** (DEV-009) | Git branches, reflections | `tests/test_memory.py` |
