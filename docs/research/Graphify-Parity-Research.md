# Competitive Research Dossier — Graphify Parity & Residual Gap Analysis

> **Reference subject:** [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) (package `graphifyy`, command `graphify`, Apache-2.0 + MIT dual-licensed, active `v8` branch).
> **Subject under test:** Agtoosa2 `v0.6.0` — 32 stages delivered.
> **Research date:** 2026-09-14.
> **Method:** Graphify's published README capability surface, benchmarks, and CLI/MCP inventory, read against a line-level audit of the Agtoosa2 source tree.
> **Purpose:** Establish which Graphify capabilities Milestone 14 (DEV-033 … DEV-037) already supersedes, and isolate the residual gaps that no planned cycle currently covers. Those residuals become Milestone 16.

---

## 1. Graphify's actual capability surface

Recorded verbatim from the reference README so future cycles measure against facts, not impressions.

| Dimension | Graphify baseline |
|---|---|
| **Parse strategy** | tree-sitter concrete syntax trees — deterministic, offline, no LLM, **$0 per-token for code** |
| **Language breadth** | **37 tree-sitter grammars**: TypeScript, JavaScript, JSX, TSX, Vue, Svelte, Astro, Rust, Go, C, C++, Zig, Metal, CUDA, Java, Kotlin, Scala, Python, Ruby, PHP, Lua, Julia, OCaml, Common Lisp, Elixir, C#, Swift, Dart, Groovy, Terraform, HCL, Fortran, Pascal, Verilog, VHDL, SQL, Bash, PowerShell, plus regex extractors for Salesforce Apex and Robot Framework |
| **Edge confidence** | Tri-state tagging: `EXTRACTED` (explicit in source), `INFERRED` (derived by resolution), `AMBIGUOUS` (uncertain) |
| **Rationale capture** | Comments matching `# NOTE:`, `# WHY:` are promoted to **first-class graph nodes** |
| **Community detection** | **Leiden** algorithm via `graspologic`, or native implementation on Python 3.13+ |
| **God nodes** | Most-connected concepts surfaced as information-flow hubs |
| **Corpus breadth** | Code, Markdown, ReStructuredText, YAML, HTML, plain text, SQL schemas, package manifests, DOCX, XLSX, PDF, PNG/JPG/WebP/GIF, MP4/MP3/WAV (local transcription via `faster-whisper`), Google Workspace Sheets/Docs/Slides |
| **LLM layer** | Pluggable backends — Claude, Gemini, OpenAI, DeepSeek, Ollama, Bedrock, Azure — used only for non-code semantic passes and community labelling |
| **Outputs** | `graph.html` (force-directed viewer), `GRAPH_REPORT.md`, `graph.json` |
| **Distribution** | `graphify install --platform` registers a `/graphify` skill across **20+ assistants** — Claude Code, Cursor, Gemini CLI, GitHub Copilot CLI, Codex, Aider, VS Code Copilot Chat, CodeBuddy, OpenCode, Kilo Code, Factory Droid, Trae, Hermes, Amp, Kiro IDE, Devin CLI, Google Antigravity — plus the cross-framework `.agents/skills/` standard, `PreToolUse` hooks, and always-on instruction files |
| **MCP surface** | `query_graph`, `get_node`, `get_neighbors`, `shortest_path`, `list_prs`, `get_pr_impact`, `triage_prs` over stdio and HTTP, with optional API-key auth |
| **Published benchmarks** | **LOCOMO (n=300): recall@10 = 0.497, QA accuracy = 45.3%**; **LongMemEval-S (n=50): QA accuracy = 76%**; claims to outperform mem0 and supermemory |
| **Ignore semantics** | `.graphifyignore` merged over `.gitignore`, `.gitignore` syntax |

---

## 2. Where Agtoosa2 already wins

These are structural advantages Graphify has no analogue for, and they are already shipped — not planned:

| Agtoosa2 capability | Module | Graphify equivalent |
|---|---|---|
| Verifiable `Spec → Build → Review → Ship` delivery gates with proof chains | `agtoosa/core/lifecycle.py` | ❌ none |
| CI architecture-drift gate + merge blocking | `action.yml`, `agtoosa/review/ci.py` | ❌ none |
| Autonomous refactor engine with atomic rollback | `agtoosa/refactor/`, `agtoosa/repair/agent.py` | ❌ none |
| Runtime blast radius from OTLP/Jaeger/Zipkin traces | `agtoosa/observability/` | ❌ none |
| C4 architecture-as-code with CI drift linter | `agtoosa/c4/` | ❌ none |
| Monorepo boundary enforcement | `agtoosa/review/monorepo.py` | ❌ none |
| Cross-repo federation via OpenAPI/gRPC/GraphQL contracts | `agtoosa/federation/` | ❌ none |
| Performance regression benchmarking CI | `agtoosa/benchmark/` | ❌ none |
| Transactional SQLite store with FTS5 + WAL, zero runtime dependencies | `agtoosa/graph/store.py` | JSON file output |

Graphify is a **read-only comprehension tool**. Agtoosa2 is a comprehension tool that also governs, verifies, and repairs. Milestone 14 correctly frames this as "supersede, not imitate."

---

## 3. Gap audit — evidence table

Every row below was verified against source, not inferred.

| # | Gap | Graphify | Agtoosa2 today | Evidence | Covered by Milestone 14? |
|:--:|---|---|---|---|---|
| 1 | **Concrete-syntax parse fidelity** | tree-sitter CST for all 37 languages | Real AST for **Python only** (`ast` module). JS/TS, Go, Rust, Java, Kotlin, C/C++, C#, SQL are **regular-expression matched** | `agtoosa/parser/js_ts_parser.py` (`IMPORT_ESM_REGEX`, `CLASS_REGEX`); `agtoosa/parser/polyglot_parser.py` (`GO_FUNC_REGEX`, `RUST_FN_REGEX`, `JAVA_METHOD_REGEX`) | ❌ **No** |
| 2 | **Language breadth** | 37 grammars | **14 extensions** in `PolyglotParser.SUPPORTED_EXTENSIONS` + `.py`/`.js`/`.ts`/`.sh`. Missing: Ruby, PHP, Swift, Dart, Scala, Elixir, Lua, Julia, Zig, OCaml, Vue, Svelte, Astro, Terraform/HCL, PowerShell, Groovy, Verilog, VHDL, Fortran | `agtoosa/parser/polyglot_parser.py:14-29` | ❌ **No** |
| 3 | **Retrieval-quality proof** | LOCOMO recall@10 0.497; LongMemEval-S QA 76% — published, reproducible | `README.md` claims ">70% token reduction" with **no harness that measures it**. `agtoosa/benchmark/` measures *execution latency*, not retrieval quality | `agtoosa/benchmark/harness.py` (perf only) | ❌ **No** |
| 4 | **Rationale nodes** | `# NOTE:` / `# WHY:` promoted to graph nodes | **Zero occurrences** — no rationale extraction anywhere in the parser subsystem | grep for `WHY:`/`rationale` across `agtoosa/parser/`, `agtoosa/core/` returns nothing | ❌ **No** |
| 5 | **Zero-dep community detection** | Leiden (graspologic or native) | `networkx.greedy_modularity_communities` **only when networkx is installed**; otherwise falls back to **union-find connected components** — reachability, not community detection | `agtoosa/graph/metrics.py:203-274` | ⚠️ **Partial** — DEV-034 specifies Hierarchical Leiden but does not address the zero-dependency fallback path |
| 6 | **LLM provider transport** | Pluggable: Claude, Gemini, OpenAI, DeepSeek, Ollama, Bedrock, Azure | **No LLM integration exists anywhere in the codebase.** Only outbound HTTP is the `urllib` GitHub client in `agtoosa/review/pr_bot.py` | no `anthropic`/`openai`/`genai` import in the tree | ⚠️ **Partial** — DEV-033/035/036 all *consume* a semantic layer; none *defines* the transport |
| 7 | **Edge confidence** | Tri-state `EXTRACTED`/`INFERRED`/`AMBIGUOUS` | `Edge.provenance` is a **free-form `str`** defaulting to `"extracted"`, with three informal values in a trailing comment and no numeric confidence | `agtoosa/core/model.py:85` | ✅ **Yes** — DEV-035 formalises tri-state provenance |
| 8 | **Corpus breadth** | PDF, DOCX/XLSX, images, A/V transcripts, HTML/RST/YAML, Google Workspace | `.md`/`.markdown` **only**, and only recognises `docs/specs/spec-DEV-*.md` and `docs/adr/ADR-*.md` — ordinary prose is silently dropped | `agtoosa/parser/doc_parser.py:20,47,126` | ✅ **Yes** — DEV-033 |
| 9 | **Multi-assistant distribution** | 20+ hosts | MCP server + VS Code/Cursor extension only | `agtoosa/mcp/server.py`, `extension/` | ✅ **Yes** — DEV-037 |
| 10 | **Architecture wiki / god nodes** | `GRAPH_REPORT.md`, community wiki | PageRank + Tarjan report exists | `agtoosa/graph/metrics.py` | ✅ **Yes** — DEV-034, DEV-036 |
| 11 | **Semantic search quality** | Real embedding backends | "Dense semantic vectors" are **MD5-hashed subword buckets** — a hashing trick, not a learned embedding. No semantic generalisation: synonyms collide arbitrarily and near-synonyms never match | `agtoosa/graph/embeddings.py:70` (`hashlib.md5(term.encode(...))`) | ⚠️ **Partial** — no cycle addresses embedding quality |

---

## 4. Residual gaps → Milestone 16

Rows 1, 2, 3, 4 are **wholly uncovered**; rows 5, 6, 11 are **partially covered** in the sense that planned cycles depend on infrastructure nobody has specified. These consolidate into four cycles:

| Cycle | Closes rows | Rating | Rationale |
|---|---|:--:|---|
| **DEV-040** — Tree-sitter Universal Concrete-Syntax Parser Backend | 1, 2 | **97/100** | The foundation gap. Every downstream capability — impact radius, context packs, the repair engine, the DEV-033 visual-drift matcher, the DEV-034 wiki — reads from the graph the parser produces. A regex parser that misses an arrow function produces a graph that silently lacks that call edge, and *every* consumer inherits the error. This is the single highest-leverage cycle in the entire plan. |
| **DEV-041** — Retrieval Quality & Token-Efficiency Benchmark Harness | 3, 11 | **86/100** | Graphify publishes numbers; Agtoosa2 publishes an unverified claim. Without a harness, no cycle in Milestone 14 or 16 can prove it improved anything — and the MD5-hash embedding weakness (row 11) is invisible until measured. |
| **DEV-042** — Rationale & Decision Provenance Extraction | 4 | **78/100** | Cheapest cycle in the plan, disproportionate payoff: intent captured in comments is exactly what a context pack cannot reconstruct from syntax, and it links naturally to the existing ADR node type. |
| **DEV-043** — Offline-First Semantic Provider Gateway & Zero-Dependency Louvain | 5, 6 | **84/100** | DEV-033, DEV-035 and DEV-036 each assume a semantic layer exists. One shared, redacting, budget-capped, cache-backed gateway must be specified once rather than three times — and the same cycle replaces the union-find community fallback with a real modularity optimiser so the zero-dependency install is not second-class. |

---

## 5. Non-negotiable constraints carried into Milestone 16

Derived from the existing architecture, not invented here:

1. **`pyproject.toml` keeps `dependencies = []`.** Verified: the runtime is pure standard library. New capability arrives as extras (`treesitter`, `llm`, `media`, `office`), never as a core dependency.
2. **Every optional path degrades, never fails.** No tree-sitter grammar → the existing regex parser handles that file. No provider key → deterministic passes only. This is why Agtoosa2 can run air-gapped and Graphify cannot.
3. **Offline by default.** No network call without explicit opt-in. Graphify's semantic pass is opt-out; Agtoosa2's must be opt-in.
4. **`BaseParser` is the extension point.** New parsers implement `can_parse`/`parse` (`agtoosa/parser/base.py`) and register in `ParserEngine.parsers` (`agtoosa/parser/__init__.py:22`). The node/edge model (`agtoosa/core/model.py`) is extended, never forked.
5. **Schema changes need a migration path.** `SCHEMA_VERSION = 1` in `agtoosa/graph/store.py` with no migration logic — the first cycle that alters the schema must establish one.

---

## 6. Open questions for cycle authors

- **Grammar distribution.** `tree-sitter-languages` ships prebuilt wheels but lags upstream grammar releases; `tree-sitter-language-pack` is more current. Pin choice belongs in the DEV-040 spec, with a documented fallback when a wheel is unavailable for the host platform.
- **Benchmark corpus licensing.** LOCOMO and LongMemEval-S are external datasets. DEV-041 should ship a self-hosted corpus derived from this repository as the always-runnable default, with external suites opt-in, so CI never depends on a third-party download.
- **Provider defaults.** DEV-043 must not hardcode model identifiers from memory. The implementing session is required to consult current Claude API reference material before writing request shapes, model IDs, or cost estimates.
- **Embedding upgrade path.** Row 11 is scoped into DEV-041 as *measurement* only. Whether to replace the MD5-hash vectors with a real local embedding model is a decision that should follow the benchmark evidence, not precede it.
