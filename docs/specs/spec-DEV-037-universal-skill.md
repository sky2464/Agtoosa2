# DEV-037: Universal Multi-Host Agent Skill & Token-Budgeted Topology Traversal

## Status
- **Status:** ✅ Implemented & Verified
- **Cycle ID:** DEV-037
- **Layer:** Core Agent Integration / Context Compiler / Distribution
- **Dependencies:** DEV-040, DEV-041, DEV-043, DEV-048, DEV-033, DEV-034, DEV-036

## Context & Problem Statement
Modern AI software engineers utilize heterogeneous agent harnesses: Claude Code, Antigravity/Gemini CLI, Cursor, and Windsurf. While standard tools dump excessive file contents into agent context windows, exceeding token limits and inducing attention degradation, graph-guided context compilation can select only the highest-centrality skeleton nodes within a strict token budget. Furthermore, agent developers need a zero-friction CLI installer to equip their agents with Agtoosa2 commands.

## Acceptance Criteria
- **AC-1 (Universal Skill Bundles)**: WHEN installed, the engine SHALL produce standard agent skill bundles for Claude Code, Antigravity, and Cursor.
- **AC-2 (Token-Budgeted Context Compiler)**: WHEN compiling context, `TopologyContextCompiler` SHALL enforce strict token budgets while preserving high-centrality symbols and provenance.
- **AC-3 (Skill Installation CLI)**: WHEN `agtoosa skill install` is executed, the CLI SHALL install skill definitions into target agent host environments.

## Architectural Decision & Invariants
1. **Universal Skill Bundles**:
   - Standardized markdown instruction format with YAML frontmatter conforming to Anthropic, Cursor, and Antigravity skill specifications.
   - Hosts supported:
     - Claude Code: `~/.claude/skills/agtoosa/SKILL.md` or `.claude/skills/agtoosa/SKILL.md`
     - Antigravity / Gemini CLI: `.agents/skills/agtoosa/SKILL.md`
     - Cursor: `.cursor/rules/agtoosa.mdc`
   - Equips agents with `/agtoosa` workflows: query, explain, path, routes, di, wiki, audit, drift.
2. **Token-Budgeted Topology Context Compiler (`TopologyContextCompiler`)**:
   - Given a query or target symbol and strict `--budget <tokens>` constraint (e.g. 1500 tokens):
     - Calculates node importance scores combining PageRank centrality, lexical relevance, and edge weight priorities (`CALLS` > `IMPORTS` > `REFERENCES`).
     - Extracts compact code skeletons (classes, methods, docstrings, parameter types) rather than raw unparsed character blocks.
     - Enforces hard token ceiling (estimated via 4 chars per token rule of thumb or word count).
3. **CLI Commands**:
   - `agtoosa skill install [--target all|claude|cursor|gemini|antigravity] [--path <dir>]`
   - `agtoosa query "<question>" [--budget <tokens>] [--strategy bfs|dfs|pagerank|hybrid] [--json]`
4. **MCP Tool Integration**:
   - `agtoosa_budgeted_query`: Returns token-capped graph topology context pack to connected LLM agents.
