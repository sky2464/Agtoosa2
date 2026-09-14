# Specification: DEV-040 Tree-sitter Universal Concrete-Syntax Parser Backend

## Status
Planned — Milestone 16 (v1.0.0)

## Priority Score
**97 / 100** — the highest-rated cycle in the Master Plan. Foundation fidelity: every downstream capability reads the graph this layer produces, so its accuracy ceiling is the product's accuracy ceiling.

## Research Basis
Established by the [Graphify Parity Research Dossier](../research/Graphify-Parity-Research.md) (2026-09-14). The reference implementation parses **37 tree-sitter grammars** deterministically and offline at zero per-token cost. A line-level audit of this repository found Agtoosa2 uses a real syntax tree for **Python only**.

| Language family | Agtoosa2 today | Mechanism | Source |
|---|---|---|---|
| Python | ✅ Real AST | stdlib `ast` module | `agtoosa/parser/python_parser.py` |
| JavaScript / TypeScript | ⚠️ Regex | `IMPORT_ESM_REGEX`, `CLASS_REGEX`, function regexes | `agtoosa/parser/js_ts_parser.py` |
| Go, Rust, Java, Kotlin, C/C++, C#, SQL | ⚠️ Regex | `GO_FUNC_REGEX`, `RUST_FN_REGEX`, `JAVA_METHOD_REGEX`, … | `agtoosa/parser/polyglot_parser.py` |
| Ruby, PHP, Swift, Dart, Scala, Elixir, Lua, Julia, Zig, OCaml, Vue, Svelte, Astro, Terraform/HCL, PowerShell, Groovy, Verilog, VHDL, Fortran | ❌ Absent | — | not in `SUPPORTED_EXTENSIONS` |

## Problem Statement

1. **Regular expressions cannot model nesting.** `RUST_FN_REGEX` and `GO_FUNC_REGEX` match line-anchored declarations. An arrow function assigned inside a callback, a closure returned from a factory, or a method on an anonymous class object is structurally invisible — the symbol is never created, so the call edge that would have pointed at it is never created either.
2. **Scope is guessed, not resolved.** `JAVA_METHOD_REGEX` matches method signatures without knowing which class body encloses them. Methods are attached to files rather than to their owning type, which corrupts `CONTAINS` edges and inflates apparent module coupling.
3. **The defect is silent and it propagates.** A missing call edge does not raise an error; it produces a confidently wrong answer. `agtoosa graph impact` under-reports blast radius. `agtoosa context compile` omits a caller the agent needed. `CycleDecouplerEngine` fails to see a cycle. The DEV-033 visual-drift detector reports a diagram arrow as a **Ghost Node** when the code is correct and the parser simply missed it. The DEV-034 wiki documents a subsystem boundary that does not exist.
4. **Coverage is a third of the reference.** 14 extensions against 37 grammars. Entire ecosystems — Rails, Laravel, iOS, Flutter, Phoenix, Terraform estates, modern frontend SFCs — cannot be indexed at all.

No cycle in Milestone 14 or 15 addresses this. Those cycles all *consume* the parser's output.

## Objectives

1. **Universal Grammar Backend (`agtoosa/parser/treesitter_parser.py`)**
   - Implement `BaseParser` (`can_parse` / `parse`, per `agtoosa/parser/base.py`).
   - Register **first** in `ParserEngine.parsers` (`agtoosa/parser/__init__.py`) so it wins `can_parse()` whenever the grammar for that file loads successfully.
   - Selection is decided **per file**, never globally: a repository may be parsed by tree-sitter for Go and by the regex fallback for Kotlin in the same build.

2. **Grammar & Query Registry (`agtoosa/parser/grammars.py`)**
   - Map file extension → grammar name → S-expression queries for each extractable construct: definitions, calls, imports, inheritance, decorators/annotations.
   - Queries are data, not code, so adding a language is a registry entry rather than a new parser class.
   - Target set (~40): the 14 existing extensions plus Ruby, PHP, Swift, Dart, Scala, Elixir, Lua, Julia, Zig, OCaml, Vue, Svelte, Astro, JSX/TSX, Terraform/HCL, PowerShell, Groovy, Verilog, VHDL, Fortran.

3. **Fidelity Gains Beyond Regex**
   - Nested, anonymous, and arrow functions, with closures bound to their enclosing scope.
   - Method bodies correctly scoped to their owning class, producing accurate `CONTAINS` edges.
   - Generic type parameters and decorator/annotation arguments preserved in node metadata.
   - Precise `start_line` / `end_line` per node and exact call-site line numbers.

4. **Graceful Degradation Chain (non-negotiable)**
   - Grammar unavailable for the host platform, or file fails to parse → fall through to `PythonASTParser`, `JavaScriptTypeScriptParser`, or `PolyglotParser` exactly as today.
   - A missing wheel degrades **fidelity**, never the build. `agtoosa graph build` must succeed with zero extras installed.
   - Tree-sitter edges are written with `provenance="extracted"`; regex-fallback edges with `provenance="inferred"`, so DEV-042's confidence model and DEV-035's `HallucinationGuard` can weight them differently.

5. **Developer & Agent Surfaces**
   - CLI: `agtoosa graph build [--parser-report]` — per-file report of which backend parsed it and, on fallback, why.
   - CLI: `agtoosa graph parsers [--json]` — available grammars, degraded languages, and host-platform wheel status.

## Architecture

### Parser Resolution Order

```
ParserEngine.parsers = [
    TreeSitterParser(),      # NEW — wins when its grammar loads
    PythonASTParser(),       # fallback: stdlib ast (already exact)
    ShellScriptParser(),
    JavaScriptTypeScriptParser(),
    MarkdownDocParser(),
    PolyglotParser(),
    PrismaParser(),
]
```

`TreeSitterParser.can_parse()` returns `True` only when both the extension is registered **and** the grammar loads on this host. Any other outcome hands the file to the existing chain untouched, which is why the cycle cannot regress current behaviour.

### Packaging

`pyproject.toml` keeps `dependencies = []`. A pinned `treesitter` extra is added, and `full` becomes the union of all extras.

Grammar-pack selection is an open decision recorded in the dossier: `tree-sitter-languages` ships prebuilt wheels but lags upstream grammar releases, while `tree-sitter-language-pack` tracks current grammars. The implementing cycle must pin one, document the platform-fallback policy when no wheel exists for the host, and record the rationale in ADR form.

### Node & Edge Model

No new `NodeType` or `EdgeType` members are required — the existing model in `agtoosa/core/model.py` is sufficient. Tree-sitter contributes **more and better-scoped instances** of existing types, not new kinds. This keeps every existing consumer (Studio, MCP, exports, refactor engine) working without modification.

## Acceptance Criteria

1. `agtoosa graph build` succeeds on a clean checkout with **no extras installed**, and `--parser-report` shows every file routed to a fallback parser.
2. With the `treesitter` extra installed, the same build routes registered languages to `TreeSitterParser` and node/edge counts **increase**.
3. The parity harness asserts tree-sitter extracts a **strict superset** of the regex parser's symbols on identical fixtures — never fewer.
4. At least one fixture per newly supported language yields correct definition, call, and import edges.
5. A fixture containing a nested arrow function and a method on an anonymous object produces symbols that the regex parser demonstrably misses.
6. `agtoosa graph report` cycle count and health score do not regress on this repository.
7. `agtoosa ci check`, `agtoosa guard`, and `agtoosa c4 sync --check` all still pass.

## Verification Fixture

`tests/test_treesitter.py`, containing:
- Per-language fixture files with expected symbol/edge assertions.
- A **parity harness** running both backends over the same fixture and asserting the superset property.
- A degradation test forcing grammar-load failure and asserting the fallback chain produces today's exact output.
- A zero-extras test guarded so it runs in the dependency-free CI leg.
