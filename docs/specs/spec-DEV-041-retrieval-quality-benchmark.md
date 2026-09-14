# Specification: DEV-041 Retrieval Quality & Token-Efficiency Benchmark Harness

## Status
Planned — Milestone 16 (v1.0.0)

## Priority Score
**86 / 100** — the measurement instrument every other cycle depends on to demonstrate it improved anything.

## Research Basis
From the [Graphify Parity Research Dossier](../research/Graphify-Parity-Research.md) (2026-09-14):

| | Graphify | Agtoosa2 |
|---|---|---|
| LOCOMO (n=300) | recall@10 **0.497**, QA accuracy **45.3%** | not measured |
| LongMemEval-S (n=50) | QA accuracy **76%** | not measured |
| Token efficiency | reported per-corpus | `README.md` asserts ">70% token reduction" with no harness behind it |
| Embedding backend | pluggable real embedding models | MD5-hashed subword buckets (`agtoosa/graph/embeddings.py:70`) |

## Problem Statement

1. **The headline claim is unverified.** `README.md` and the Capability Matrix both state Context Compilation v2 targets ">70% token reduction". Nothing in the repository measures it. The claim is the product's central value proposition and it rests on assertion.
2. **The existing benchmark harness measures the wrong axis.** `agtoosa/benchmark/harness.py` (DEV-032) measures *execution latency and memory* of benchmarked symbols. It says nothing about whether a compiled context pack contains the information an agent needed.
3. **A known weakness is invisible without measurement.** `SemanticEmbeddingEngine.embed_text` hashes subword terms with `hashlib.md5` into fixed buckets. This is a hashing trick, not a learned embedding: synonyms collide arbitrarily, and near-synonyms never match. Whether this materially hurts retrieval is currently unknowable.
4. **No cycle can prove its own value.** DEV-040 will improve parse fidelity and DEV-043 will improve community structure — but without a retrieval scorer, neither can produce evidence, and regressions would pass unnoticed.

## Objectives

1. **Retrieval Scorer (`agtoosa/benchmark/retrieval.py`)**
   - Metrics: `recall@k`, `MRR`, `nDCG`, answer accuracy, **tokens-to-answer**, and wall-clock latency.
   - Retrieval strategies measured head-to-head:
     - `grep` — raw keyword match, the status-quo agent behaviour.
     - `files` — whole-file dump, the naive-context baseline.
     - `vector` — `SemanticEmbeddingEngine` alone.
     - `agtoosa` — full Context Compilation v2 pack, hybrid RRF path included.
   - Sits beside the performance harness rather than replacing it, reusing `BenchmarkBaselineStore` snapshot and tagging semantics from DEV-032.

2. **Dataset Layer (`agtoosa/benchmark/datasets.py`)**
   - **Self-hosted corpus (default, CI-safe)**: a question set hand-labelled against this repository's own modules, tests, and specs, committed as fixtures. CI never depends on a third-party download.
   - **External suites (opt-in)**: LOCOMO / LongMemEval-S-shaped task format, so published reference figures sit directly beside Agtoosa2's own.
   - Dataset licensing is respected by keeping external corpora opt-in and unbundled.

3. **Scorecard Output**
   - Markdown table suitable for direct inclusion in `README.md`, showing each strategy against each metric with the delta versus the `grep` baseline.
   - JSON output for CI consumption and historical tracking.

4. **Attribution Discipline**
   - Run once **before** DEV-040 and DEV-043 to record a baseline, and again **after** each, so every cycle's contribution to retrieval quality is separately attributable rather than lumped into one release-level claim.

5. **Developer & Agent Surfaces**
   - CLI: `agtoosa benchmark retrieval [--suite <name>] [--baseline grep|files|vector] [--save-baseline] [--json]`.

## Architecture

### Scoring Flow

```
question set ──┬─▶ grep baseline      ──┐
               ├─▶ whole-file dump    ──┤
               ├─▶ vector-only        ──┼─▶ scorer ─▶ {recall@k, MRR, nDCG,
               └─▶ agtoosa context    ──┘              accuracy, tokens, ms}
                                                            │
                                                            ▼
                                              Markdown scorecard + JSON
```

Each question carries a labelled set of gold node IDs. A strategy's returned context is scored on whether those nodes appear, at what rank, and at what token cost. Token counting uses a single documented tokenizer so figures are comparable across runs.

### Relationship to the Embedding Question

This cycle **measures** the MD5-hash embedding weakness; it does not fix it. Whether to replace `SemanticEmbeddingEngine` with a real local embedding model is a decision that should follow the evidence rather than precede it. If the `vector` baseline scores at or near the `grep` baseline, that is the signal to act — and it will be a measured signal, not a hunch.

## Acceptance Criteria

1. `agtoosa benchmark retrieval` runs to completion on a clean checkout with **no extras installed**, using the self-hosted corpus.
2. Scores are deterministic: two consecutive runs on an unchanged graph produce identical metrics.
3. All four strategies are scored in a single run and reported in one table.
4. Tokens-to-answer is reported for every strategy, making the ">70% token reduction" claim either demonstrable or falsifiable.
5. `--save-baseline` persists a tagged snapshot that a later run can diff against.
6. A deliberately degraded graph (fixture with edges removed) produces measurably lower recall, proving the harness is sensitive to graph quality.

## Verification Fixture

`tests/test_retrieval_bench.py` — scorer correctness against hand-computed recall@k / MRR / nDCG values, determinism across repeated runs, and token-counter stability. The full suite is executed as a CLI run rather than a unit test, so CI time stays bounded.
