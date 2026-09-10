# Agtoosa2 — Capability Matrix & Parity Definition

> **Reference Benchmark:** Graphify Open-Source Capabilities & Enterprise Graph OS.  
> **Status:** Stage 11 Delivered & Verified (`v0.2.1-dev`) — 70/70 Automated Tests Passing.

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
| **IDE Extension Integration** | VS Code / Cursor extension | **Stage 13** (DEV-013)| Editor tree view, code lens, real-time blast radius | Extension test suite |
| **Hybrid GraphRAG v2** | `agtoosa context compile --hybrid`| **Stage 14** (DEV-014)| Local ONNX vector embeddings, hybrid FTS5 + vector | `tests/test_hybrid_rag.py` |
