# [ADR-001] Unified Graph-Native Architecture & Python Runtime

**Status**: Accepted  
**Date**: 2026-09-09  
**Deciders**: AI Agent + System Architect  

---

## Context

Legacy AgToosa v1 was built primarily as a template generator relying on duplicated Bash (`agtoosa.sh`) and PowerShell (`agtoosa.ps1`) scripts. This created severe drawbacks:
1. **Maintenance Overhead**: Features and bug fixes had to be authored and validated twice across divergent shell environments.
2. **Lack of Semantic AST Understanding**: Shell scripts lacked robust abstract syntax tree (AST) parsers, forcing agents to navigate code using naive regex grep and full-text searches.
3. **Context Window Saturation**: Static Markdown prompt templates were copied directly into downstream repositories, flooding LLM context windows with thousands of tokens of static boilerplate.
4. **Disconnected Requirements and Evidence**: Project specifications, tasks, and test results lived in loose text files without verifiable relational links.

## Decision

We adopt a **Unified Graph-Native Engineering Architecture** powered by a single, modern **Python 3.11+ Core Engine** (`agtoosa`):
1. **Single Runtime**: All engine capabilities, command-line interfaces, and lifecycle validations are written in Python 3.11+, providing native cross-platform support across macOS, Linux, and Windows.
2. **Tree-sitter AST Parsing**: Code symbols, imports, class hierarchies, and function calls are extracted deterministically using Tree-sitter grammars.
3. **SQLite FTS5 + NetworkX Graph**: Relational data, full-text inverted indexes, and graph traversal algorithms (PageRank, shortest paths, community clustering) run locally in `.agtoosa/graph.db`.
4. **Unified Node Model**: Code symbols, Stories, Criteria, Tasks, and Evidence are nodes in one queryable knowledge graph.
5. **Native MCP Server**: The engine exposes Model Context Protocol tools directly to AI assistants.

## Rationale

- **Ecosystem Maturity**: Python offers premier libraries for AST parsing (`tree-sitter`), graph analytics (`networkx`), and transactional storage (`sqlite3` with FTS5 built-in).
- **Zero-Daemon Architecture**: SQLite and NetworkX provide high performance without running an external database daemon (unlike Neo4j or Postgres).
- **Sub-Second Latency**: Graph queries and symbol lookups execute in milliseconds locally.
- **Dramatically Lower Context Overhead**: Graph Context Compilation v2 delivers targeted subgraphs to AI agents rather than static template dumps.

## Consequences

- **Positive**:
  - Eliminates 100,000+ lines of duplicated Bash and PowerShell script maintenance.
  - Enables accurate impact analysis, call tracing, and dead code detection.
  - Gives AI coding assistants instant graph navigation via CLI and MCP.
  - Guarantees verifiable delivery evidence before releases.
- **Trade-offs & Mitigation**:
  - Requires Python 3.11+ installed on the host. Mitigated by lightweight packaging, standard virtualenv support, and graceful fallback.
