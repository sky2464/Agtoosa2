# Research: Graphify parity and Agtoosa2 graph trust

**Research date:** 2026-09-13.  
**Agtoosa2 baseline:** `8fd913a009db1209b84498aef72bc3fea75b4b76` (`origin/main`, fetched and pulled before this documentation update).  
**Graphify reference:** `v8` resolved through `git ls-remote` to `fe66389083369c3159aa391117185c8f58b4d07c`.  
**Related epic:** [EPIC-001 — Trusted Knowledge Intelligence](../specs/epic-001-trusted-knowledge-intelligence.md).

## 1. Conclusion and research boundaries

Agtoosa2 should establish trustworthy extraction, resolution, updates, and verification before expanding the graph's inputs or automation. A richer graph amplifies incorrect relationships as well as correct ones. The first release therefore covers every currently supported language and schema family, not only Python and JavaScript.

This report combines source inspection of Agtoosa2, public Graphify documentation, and test results obtained earlier in the same review session. It is not a runtime evaluation of Graphify, an exhaustive security audit, or proof that either product is superior. Feature documentation and passing unit tests are different kinds of evidence.

User decisions recorded during planning:

- Accuracy precedes breadth; all current languages belong in the first accuracy milestone.
- Code indexing stays offline. Semantic understanding uses the active assistant or explicitly configured local/cloud providers; cloud access is optional.
- Agtoosa2 owns the implementation; established libraries are primitives, and Graphify is a capability reference.
- The latest instruction requests a future-development epic and research documentation. All implementation tasks below remain planned.

## 2. Graphify reference and corrections

The pinned [README](https://github.com/Graphify-Labs/graphify/blob/fe66389083369c3159aa391117185c8f58b4d07c/README.md) documents local grammar-based code extraction, broad language support, document/media ingestion, provenance, query/path/explain, Leiden communities, reports/wiki/exports, incremental hooks, MCP, and multiple assistant integrations, including Codex. These are advertised capabilities, not independently measured results.

The [architecture documentation inspected on v8](https://github.com/Graphify-Labs/graphify/blob/v8/ARCHITECTURE.md) describes extraction validation, uncertainty labels, URL/path safety checks, a modular pipeline, watch helpers, and graph serving. The page was inspected as a branch view; preserve an immutable copy/hash alongside the actual benchmark run before treating it as a reproducibility artifact.

Consequently, earlier Master Plan descriptions of Graphify as single-host, Louvain-only, or blindly accepting every semantic output were unsupported. Agtoosa2's proposed benefits must be evaluated against the real reference. Absence of a feature from inspected documentation is not proof that it does not exist.

The publisher's [benchmark report](https://github.com/Graphify-Labs/graphify/blob/v8/BENCHMARKS.md), marked updated 2026-07-05, reports memory and code-intelligence evaluations. Its conversational-memory scores do not establish multilingual static-analysis correctness. Its code example uses a small question set; results have not been independently reproduced here. Do not transfer these numbers into Agtoosa2 performance claims.

## 3. Agtoosa2 findings and implementation consequences

Paths below refer to the Agtoosa2 baseline above. Function names provide stable lookup anchors; these are observed mechanisms and their implications, not results of a newly executed adversarial test suite.

| Finding | Source evidence | Consequence and future owner |
|---|---|---|
| R-01: Most advertised AST coverage is regex extraction | [JS/TS parser](../../agtoosa/parser/js_ts_parser.py), [polyglot parser](../../agtoosa/parser/polyglot_parser.py), [shell parser](../../agtoosa/parser/shell_parser.py), and Prisma extraction in [frameworks](../../agtoosa/parser/frameworks.py) use regex patterns. Python uses standard-library `ast`. Optional tree-sitter dependencies are declared but are not selected by `ParserEngine`. | Report actual parser capability; add grammar-backed adapters with language-specific tests. DEV-040. |
| R-02: Name collisions can produce wrong links | `ParserEngine._resolve_cross_file_symbols` in [parser orchestration](../../agtoosa/parser/__init__.py) stores one `symbol_map[name]` target. Import/call resolution uses this global map. | Bind within lexical/module/package scope; retain multiple candidates and unresolved references. DEV-041. |
| R-03: Query ambiguity is hidden | `resolve_node` in [query.py](../../agtoosa/graph/query.py) selects a name with `LIMIT 1`, then can fall back to the first full-text result. | Return candidate sets and explicit resolution status. Actionable operations must not use a guessed target. DEV-041/043. |
| R-04: An index run is not one atomic publication | `index_workspace` removes old file data and writes fingerprints before `insert_batch`; [GraphStore](../../agtoosa/graph/store.py) opens separate transactions for these methods. Parser exceptions are swallowed. | Stage extraction before publication; commit graph, references, fingerprints, and metadata together. Expose failures and retain the last good snapshot. DEV-042. |
| R-05: Unchanged callers can lose relationships | `remove_file` deletes edges whose source OR target is removed; unchanged files are skipped, while resolved placeholders have already been overwritten. | Keep original reference facts and recompute affected resolution. Test target-only edits and compare against clean rebuilds. DEV-041/042. |
| R-06: Clean rebuild conflates derived and recorded data | `GraphStore.clear` deletes every node and edge, including the shared categories used for lifecycle/evidence records. | Separate ownership; preserve manual records and validate links during migrations and rebuilds. DEV-042. |
| R-07: General knowledge ingestion is limited | [MarkdownDocParser](../../agtoosa/parser/doc_parser.py) recognizes specific spec/ADR/task patterns; general Markdown primarily becomes a file node. [Scanner](../../agtoosa/parser/scanner.py) excludes PDFs and common raster formats and caps ordinary inputs at 2 MiB. | Add sections/content/citations and optional media adapters with explicit limits. Existing DEV-033/035, after foundation. |
| R-08: "Semantic" vectors are hashed text features | `SemanticEmbeddingEngine.embed_text` in [embeddings.py](../../agtoosa/graph/embeddings.py) hashes tokens and character n-grams into buckets. No learned semantic model is used there. | Label the existing method accurately; evaluate synonym/concept retrieval separately before introducing optional model providers. DEV-043/046 and DEV-035/037. |
| R-09: Benchmark fallback does not measure the target | `_resolve_callable` in [harness.py](../../agtoosa/benchmark/harness.py) substitutes `synthetic_probe` when loading fails; Python imports can execute module code. | Return unsupported/skipped outcomes; require explicit runnable benchmark adapters and controlled execution. Never count synthetic results as application evidence. DEV-045. |
| R-10: Repair verification overstates evidence | `apply_and_verify` in [repair agent](../../agtoosa/repair/agent.py) returns `verified: true` for dry runs; the post-apply path audits without explicitly rebuilding the graph or running project tests, and its issue check focuses on cycles. | Bind patches to source hashes, reindex, check the specific finding, run required checks, and rollback failures before recording verification. DEV-044. |
| R-11: Project records exceed available evidence | The upstream Master Plan labels v0.6.0 GA and all stages verified while [pyproject.toml](../../pyproject.toml) still declares 0.5.0. The capability matrix cites absent `test_incremental.py`, `test_explain.py`, `test_path.py`, and `test_proof_gate.py`. | Distinguish package version, roadmap labels, existing tests, and measured acceptance. Repair links and avoid claiming a release or parity from a stage count. DEV-046. |
| R-12: Source-comment rationale is discarded at parse time | No parser under [`agtoosa/parser/`](../../agtoosa/parser/) recognizes `WHY:`, `NOTE:`, `HACK:`, or `ASSUMPTION:` markers; comments are read for docstrings only. [MarkdownDocParser](../../agtoosa/parser/doc_parser.py) covers document prose, not code comments. | Extract decision rationale recorded beside the code it explains and bind it to the enclosing symbol with a citation. A context pack currently supplies mechanism without stated intent. DEV-047. |
| R-13: The dependency-free community fallback measures reachability, not communities | `_detect_communities` in [metrics.py](../../agtoosa/graph/metrics.py) uses `networkx.community.greedy_modularity_communities` when NetworkX is importable and otherwise groups nodes by union-find connected components. Connected components answer "what is reachable", not "what clusters". | The optional-dependency path and the core path must answer the same question. Provide a first-party modularity optimizer so a dependency-free install is not silently given a different algorithm. DEV-048. |
| R-14: The stated semantic-provider policy has no implementation or owner | Constraint §2 of [EPIC-001](../specs/epic-001-trusted-knowledge-intelligence.md) requires assistant-or-configured providers with no automatic cloud fallback, but no provider transport, redaction boundary, budget ceiling, or response cache exists. The only outbound HTTP client is the `urllib` GitHub client in [pr_bot.py](../../agtoosa/review/pr_bot.py). | Specify the egress boundary once, before DEV-033/035/036 each grow their own. Redaction, budgets, caching, and opt-in enforcement cannot be per-consumer. DEV-049. |

## 4. Current language coverage to retain and improve

| Family | Current mechanism | Required accuracy work |
|---|---|---|
| Python | Standard-library AST | Nested/qualified identity, relative imports, aliases, class/member scope, ambiguity for dynamic dispatch. |
| JS/TS, JSX/TSX, module variants | Regex | Grammar-backed definitions/references, ESM/CommonJS exports and aliases, package boundaries, overload/member distinctions. |
| Shell/Bash/Zsh | Regex | Functions, literal source paths, command references; explicitly limit unsupported dialect constructs and dynamic paths. |
| Go | Regex | Package/import scope, aliases, receiver methods, visibility, interfaces without fabricated runtime targets. |
| Rust | Regex | Module/use paths, aliases, traits/impls, namespace distinctions and unresolved macro-generated references. |
| Java/Kotlin | Regex | Package/import scope, nested classes, overloads, member resolution, unknown reflective calls. |
| C/C++ | Regex | Include context, namespaces, translation units, signatures; expose preprocessing and pointer-dispatch uncertainty. |
| C# | Regex | Namespaces, using aliases, partial/nested types, overloads, unresolved reflection. |
| SQL | Regex | Dialect-labelled table/view identities, schemas, quoted identifiers and foreign-key targets. |
| Dockerfile | Regex | Stage identity, FROM/COPY stage references and variable-dependent uncertainty. |
| Prisma | Regex | Model identity, relation fields and targets, mappings, ignored/generated inputs. |

Accuracy means correct assertions within declared coverage and visible uncertainty elsewhere. It does not mean solving all dynamic behavior or compiler semantics. A grammar validates syntax structure; it does not independently resolve every relationship.

## 5. Baseline verification and evidence limitations

Earlier in this review, against code at `d2d4cdb`:

```text
.venv/bin/python -m pytest -q
200 passed; 5 Studio cases failed at socket.bind with PermissionError

.venv/bin/python -m pytest tests/test_studio_server.py -q
5 passed after allowing localhost socket access
```

Thus all 205 existing tests passed across two runs, not one unrestricted full-suite run. The subsequent upstream commit `8fd913a` changes planning documents. This documentation update does not rerun runtime tests or establish new acceptance evidence. Existing tests do not establish relationship precision, clean/incremental equivalence under all edits, a safe repair pipeline, or a Graphify comparison.

## 6. Evaluation design for DEV-046

1. Freeze both implementations, parser/provider versions, dependency lock data, OS/CPU/RAM, datasets, ignore rules, graph options, random seeds, and budgets in a run manifest. Use the Graphify commit above for the first comparison; changing it creates a new baseline.
2. Build independently labelled fixtures for every family in section 4. Include equal names in different scopes, aliases, external dependencies, cycles, overloads, malformed files, and unsupported dynamic behavior. Keep development fixtures separate from a held-out evaluation split; do not tune on held-out results.
3. Label nodes, directed typed relationships, source spans, and cases where abstention is correct. Measure edge precision/recall per language and relationship type, false concrete resolutions on ambiguous inputs, and citation correctness. Report denominators, unsupported cases, and macro-averages so a large Python set cannot hide weak languages.
4. Exercise add/edit/delete/rename/branch-switch/parser-upgrade sequences. Compare normalized snapshots from incremental and fresh indexing, excluding only timestamps and publication IDs. Inject failure before publication and concurrent source edits; retained old snapshots must remain identifiable as stale.
5. Use the same question set for retrieval and answers. Measure recall@k, answer correctness, citation support, unknown-answer handling, contradiction reporting, input/output tokens, and configured provider costs. Lexical retrieval, hashed-feature retrieval, and optional learned embeddings are separate variants.
6. Measure cold/warm indexing, incremental updates, query p50/p95, peak memory, and snapshot size on the same machine. Use repeated runs and publish raw samples; do not compare microbenchmark latency directly with production trace latency.
7. Hard correctness gates: zero wrong concrete resolutions on designated ambiguity cases; all publication/migration/stale-patch/rollback regressions pass; all emitted citations bind to the reported snapshot. Publish quality and performance measurements even when they are worse. "Parity" requires passing every in-scope checklist item; "better" is restricted to a metric supported by the paired evaluation.

## 7. Implications for existing future stages

- DEV-033: Start with general documents/configuration/schema content, then optional PDF/Office, images, audio/video, and URLs. Missing graph coverage cannot prove a diagram entity is fictitious; an indirect path can be a valid diagram abstraction.
- DEV-034: Hierarchy, wiki maintenance, C4 integration, and explainable package metrics are hypotheses to evaluate, not proof of superiority. Missing abstraction information yields unavailable metrics rather than invented scores.
- DEV-035: Validate source citations and relationships, not only symbol existence. A missing symbol is unresolved/unverified; fuzzy matches are suggestions and never automatic substitutions. Provider/model/prompt versions participate in cache keys.
- DEV-036: Prioritize cited findings, uncertainty, and test selection. High centrality alone cannot justify an executable refactor or deletion.
- DEV-037: Include Codex and host-specific activation conventions. Budget provenance and uncertainty alongside content; measure context utility rather than promising an arbitrary token-reduction percentage. Automatic graph consultation falls back to source inspection.
- DEV-038/039: Keep attestation and synthesis deferred until graph, evidence, and repair gates are accepted. A signature proves artifact origin/integrity, not architectural truth; cryptographic signing alone is not a zero-knowledge proof.
