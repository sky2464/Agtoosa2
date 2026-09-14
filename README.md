# Agtoosa2 🚀

**The Graph-Native Engineering Operating System for AI Coding Agents and Developers.**

Agtoosa2 unifies code comprehension, project planning, and delivery assurance into a single, queryable local knowledge graph. Built from the ground up to replace legacy template generators, Agtoosa2 provides zero-bloat, cross-platform engineering intelligence.

## Why Agtoosa2?

Grep and "find references" show you where a symbol appears. Agtoosa2 gives your codebase — and your AI agent — an actual model of it, so these stop being manual work:

- **Know the blast radius before you touch code.** `agtoosa graph impact <symbol>` traces the real call/import graph across code, specs, and tests — not just text matches.
- **Prove a change is done, not just merged.** Delivery gates (`Spec → Build → Review → Ship`) are backed by graph edges (`IMPLEMENTS`, `VERIFIES`, `EVIDENCED_BY`), so `agtoosa ship verify` checks a story has passing tests and evidence behind it — no manual checklist.
- **Stop paying for context your agent doesn't need.** Context Compilation v2 hands AI agents a bounded, precision subgraph instead of whole files, targeting >70% token reduction.
- **One MCP server, any agent.** `agtoosa mcp` exposes graph search, impact analysis, and task context as MCP tools that Claude Code, Cursor, Windsurf, Copilot, and Gemini CLI can all call directly, instead of scraping terminal output.
- **Cross-repo impact in microservice setups.** `agtoosa graph federate` links repos via OpenAPI/gRPC/GraphQL contracts so impact analysis crosses service boundaries.
- **Catches drift in CI, not in prod.** The bundled GitHub Action posts impact comments and can block merges on graph-verified architectural drift.
- **Zero infrastructure.** Everything lives in one local SQLite file (`.agtoosa/graph.db`) — no vector DB, no daemon, no cloud dependency to stand up.

**The short version:** your AI agent stops guessing about your codebase because it now has a queryable, provable model of it.

## Core Capabilities

- 🧠 **Unified Knowledge Graph**: Connects code AST symbols, specifications (Stories & Criteria), tasks, and test evidence in a transactional SQLite store.
- ⚡ **Zero External Daemons**: Runs locally with SQLite FTS5 and sub-second query latency.
- 🎯 **Graph Context Compilation v2**: Extracts precision subgraphs for AI coding agents, slashing context bloat by >70%.
- 🛡️ **Verifiable Delivery Gates**: Enforces `Spec → Build → Review → Ship` transitions with mathematical proof chains.
- 🔌 **Native Agent Protocols**: Exposes CLI commands and a native Model Context Protocol (MCP) server for modern AI tools.
- 📊 **Architecture Health & Visualizer**: Generates standalone offline Cytoscape.js HTML viewers, cycle detection, PageRank hub rankings, and Obsidian vaults.

## Quick Start

```bash
# Initialize and build the project graph
python3 -m agtoosa.cli.main graph build

# Check graph status and indexed metrics
python3 -m agtoosa.cli.main graph status

# Query symbols, definitions, or architectural concepts
python3 -m agtoosa.cli.main graph query "UserAuth"

# Run architectural health audit, cycle detection, and PageRank report
python3 -m agtoosa.cli.main graph report

# Generate standalone offline interactive HTML visualizer
python3 -m agtoosa.cli.main graph view --output .agtoosa/graph_view.html

# Export graph to Obsidian markdown vault, GraphML, Cypher, or DOT
python3 -m agtoosa.cli.main graph export --format obsidian -o .agtoosa/obsidian_vault
python3 -m agtoosa.cli.main graph export --format graphml -o .agtoosa/graph.graphml
```

## Documentation

- [Master Plan](docs/Master-Plan.md): Roadmap and delivery stages.
- [Master Architecture](docs/Master-Architecture.md): Architecture, C4 diagrams, and quality attributes.
- [ADR-001](docs/adr/ADR-001-unified-graph-native-architecture.md): Architectural decision record for the Python graph engine.
- [Capability Matrix](docs/Capability-Matrix.md): Functional parity mapping against reference capabilities.
- [Graphify Parity Research Dossier](docs/research/Graphify-Parity-Research.md): Evidence-backed competitive gap analysis driving the Milestone 16 roadmap.
- [DEV-001 Specification](docs/specs/spec-DEV-001-native-graph.md): Stage 1 specification.
- [DEV-005 Specification](docs/specs/spec-DEV-005-visualizer-and-reports.md): Stage 5 interactive visualizer & report specification.

