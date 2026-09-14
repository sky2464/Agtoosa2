# Specification: DEV-042 Rationale & Decision Provenance Extraction

## Status
Planned — Milestone 16 (v1.0.0)

## Priority Score
**78 / 100** — the cheapest cycle in the plan with disproportionate payoff for AI agent context quality.

## Research Basis
From the [Graphify Parity Research Dossier](../research/Graphify-Parity-Research.md) (2026-09-14):

- Graphify promotes comments matching `# NOTE:` and `# WHY:` into **first-class graph nodes**, and tags every relationship tri-state: `EXTRACTED`, `INFERRED`, `AMBIGUOUS`.
- Agtoosa2 has **zero** rationale extraction anywhere in the parser subsystem, and `Edge.provenance` (`agtoosa/core/model.py:85`) is a free-form `str` defaulting to `"extracted"`, with its three informal values documented only in a trailing comment.

DEV-035 formalises tri-state provenance for *semantic extraction*. This cycle formalises it for the *whole graph*, including the deterministic parser layer, and adds the numeric confidence and schema-migration machinery DEV-035 will rely on.

## Problem Statement

1. **Intent is the one thing syntax cannot reconstruct.** An AST tells an agent that `retry_count = 3`. It cannot tell it `# WHY: upstream rate-limits at 4 req/s, three retries stays under the ceiling`. That sentence is exactly what prevents an agent from "simplifying" the constant to 1. Today it is discarded at parse time.
2. **Rationale is already written and already ignored.** Developers record decisions in comments continuously. The repository parses those files and drops the comments, so a context pack hands an agent the mechanism without the reasoning.
3. **Provenance is untyped and unenforced.** A free-form string with no enumeration means nothing validates it, nothing can filter on it, and DEV-040's extracted-vs-inferred distinction has nowhere trustworthy to land.
4. **There is no schema migration path.** `agtoosa/graph/store.py` declares `SCHEMA_VERSION = 1` with no migration logic. The first cycle to alter the schema must build that machinery, and this is the cheapest place to do it — before DEV-035 and DEV-043 need it under pressure.

## Objectives

1. **Rationale Extractor (`agtoosa/parser/rationale.py`)**
   - Recognise `# WHY:`, `# NOTE:`, `# HACK:`, `# ASSUMPTION:`, and `TODO(owner)` markers across every supported comment syntax (`#`, `//`, `/* */`, `--`, `<!-- -->`).
   - Bind each marker to its enclosing symbol using the parser's existing scope resolution — with DEV-040 landed, this becomes exact rather than proximity-based.
   - Link to `NodeType.ADR` nodes when a decision record is cited by ID (e.g. `# WHY: see ADR-001`), producing a traversable path from a line of code to the decision that justifies it.

2. **Formalised Edge Confidence**
   - Replace the free-form `provenance: str` with an enumeration: `EXTRACTED | INFERRED | AMBIGUOUS | MANUAL`.
   - Add a numeric `confidence` column on `edges`, populated by:
     - DEV-040's parser backend — tree-sitter edges high, regex-fallback edges lower.
     - DEV-043's semantic passes — model-derived edges marked `INFERRED` with a calibrated score.
     - DEV-035's `HallucinationGuard` — ungrounded symbol references marked `AMBIGUOUS`.
   - Expose `--min-confidence <float>` on `graph impact` and `context compile` so blast radius can be restricted to structurally certain edges.

3. **Schema Migration Machinery**
   - Bump `SCHEMA_VERSION` in `agtoosa/graph/store.py` and add the forward-migration path the store currently lacks.
   - An existing `v1` database must migrate in place without a full rebuild, defaulting `provenance` to `EXTRACTED` and `confidence` to `1.0` for pre-existing edges.

4. **Context Pack Integration**
   - Rationale nodes are included in compiled context packs, so an agent reading a symbol also reads why it is the way it is.
   - Rationale text is subject to the existing secret-redaction pass (`agtoosa/core/security.py`) before it enters any pack or MCP response.

5. **Developer & Agent Surfaces**
   - CLI: `agtoosa graph rationale <symbol> [--json]`.
   - CLI: `--min-confidence <float>` on `agtoosa graph impact` and `agtoosa context compile`.
   - MCP Tool: `agtoosa_get_rationale`.

## Architecture

### Node & Edge Model Changes

`agtoosa/core/model.py`:
- Add `NodeType.RATIONALE`.
- Replace `Edge.provenance: str` with the four-member enumeration and add `Edge.confidence: float`.

`agtoosa/graph/store.py`:
- `edges` gains a `confidence` column; `provenance` is constrained to the enumerated set.
- `SCHEMA_VERSION` bump plus a migration registry keyed by version, applied on open.

### Extraction Flow

```
source file ──▶ parser (DEV-040 or fallback)
                    │
                    ├─▶ symbol nodes + edges  (provenance, confidence)
                    └─▶ comment scan ──▶ RATIONALE nodes
                                            │
                                            ├── CONTAINS ◀── enclosing symbol
                                            └── REFERENCES ─▶ ADR node (when cited)
```

Rationale extraction runs inside the existing parse pass, so it costs one additional scan over already-loaded file content and adds no I/O.

## Acceptance Criteria

1. A fixture containing `# WHY:`, `# NOTE:`, `# HACK:`, and `# ASSUMPTION:` markers in Python, JavaScript, Go, and SQL comment syntaxes yields one `RATIONALE` node each, bound to the correct enclosing symbol.
2. A rationale citing `ADR-001` produces a `REFERENCES` edge to the existing ADR node.
3. An existing `SCHEMA_VERSION = 1` database opens, migrates in place, and retains all prior nodes and edges with `provenance=EXTRACTED`, `confidence=1.0`.
4. `agtoosa graph impact <symbol> --min-confidence 0.9` returns a strict subset of the unfiltered result.
5. A rationale comment containing a credential-shaped string is redacted before appearing in any context pack or MCP response.
6. Compiled context packs include rationale for symbols that have it, and are unchanged for symbols that do not.

## Verification Fixtures

- `tests/test_rationale.py` — multi-language marker recognition, symbol binding, ADR linkage, redaction.
- `tests/test_confidence.py` — enumeration enforcement, `--min-confidence` filtering, and a schema-migration round-trip from `SCHEMA_VERSION = 1`.
