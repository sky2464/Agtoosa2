# Specification: DEV-043 Offline-First Semantic Provider Gateway & Zero-Dependency Louvain

## Status
Planned — Milestone 16 (v1.0.0)

## Priority Score
**84 / 100** — the shared substrate three Milestone 14 cycles assume but none defines.

## Research Basis
From the [Graphify Parity Research Dossier](../research/Graphify-Parity-Research.md) (2026-09-14):

| Capability | Graphify | Agtoosa2 verified state |
|---|---|---|
| LLM transport | Pluggable: Claude, Gemini, OpenAI, DeepSeek, Ollama, Bedrock, Azure | **No LLM integration exists anywhere.** The sole outbound HTTP client is the `urllib` GitHub client in `agtoosa/review/pr_bot.py` |
| Community detection | Leiden via `graspologic`, or native on Python 3.13+ | `networkx.greedy_modularity_communities` **only when networkx is installed**; otherwise union-find connected components (`agtoosa/graph/metrics.py:203-274`) |

DEV-033 (multimodal ingestion), DEV-035 (subagent semantic extraction), and DEV-036 (Socratic audit) each consume a semantic layer. None of them specifies the transport, the caching, the redaction, or the budget ceiling. Specifying it three times, inconsistently, is the failure mode this cycle prevents.

## Problem Statement

1. **Three cycles depend on infrastructure nobody owns.** Without a single gateway, each of DEV-033/035/036 grows its own provider handling — and each would need to independently get secret redaction, cost control, and cache invalidation right.
2. **The zero-dependency install gets a degraded graph.** `_detect_communities` falls back to union-find when networkx is absent. Union-find computes **connected components** — which nodes can reach each other — not communities. On a typical codebase where nearly everything is transitively connected, this returns one enormous component and calls it a community. DEV-034's hierarchical Leiden partitioning has nothing meaningful to build on in the dependency-free path.
3. **Any LLM layer is a data-egress surface.** Source code, comments, and document text would leave the machine. Without redaction, budget caps, and explicit opt-in enforced in one place, the airgapped and enterprise story Agtoosa2 currently has over Graphify is lost the moment the first semantic cycle ships.

## Objectives

1. **Provider Gateway (`agtoosa/semantic/provider.py`)**
   - Provider-agnostic transport over Claude, OpenAI, Gemini, Bedrock, Azure, and Ollama, built on `urllib.request` in the zero-dependency core — the identical technique `agtoosa/review/pr_bot.py` already uses for GitHub REST.
   - Optional SDKs only where a provider requires request signing; absence degrades to "that provider unavailable", never to a failed build.
   - **Model identifiers, request shapes, parameter names, and cost tables must be taken from current Claude API reference material at implementation time — never written from memory.**

2. **Zero-Trust Egress Controls (non-negotiable)**
   - **Secret redaction before any payload leaves the machine**, reusing the existing scanner in `agtoosa/core/security.py`.
   - Hard token-budget ceiling per pass, with `--dry-run` producing a cost estimate and sending nothing.
   - **No network call occurs without explicit opt-in** — a CLI flag or a configured provider in `.agtoosa/config.json`. Absent that, every semantic pass is a deterministic no-op. Graphify's semantic pass is opt-out; Agtoosa2's is opt-in.
   - Workspace-boundary and path-traversal guards from DEV-007 apply to every file the gateway reads.

3. **SHA-256 Content-Keyed Response Cache**
   - Cache keyed on content hash, mirroring the fingerprint discipline already in `agtoosa/parser/__init__.py`.
   - Re-indexing unchanged files costs zero tokens and zero network calls.
   - Cache lives under `.agtoosa/` and is excluded from commits by the existing ignore rules.

4. **Zero-Dependency Community Detection (`agtoosa/graph/communities.py`)**
   - Extract community logic out of `agtoosa/graph/metrics.py` into a dedicated module.
   - Implement **pure-Python Louvain** (modularity-optimising) as the real default — no networkx required.
   - Optional Leiden refinement pass when `networkx` / `graspologic` is present, feeding DEV-034's hierarchical Domain → Subsystem → Module partitioning.
   - **Remove the union-find fallback entirely.** Reachability masquerading as community structure is worse than a slower correct answer.

5. **Developer & Agent Surfaces**
   - CLI: `agtoosa semantic status [--json]` — configured provider, cache hit rate, tokens spent, opt-in state.
   - CLI: `agtoosa semantic enrich [--provider <name>] [--dry-run] [--budget <tokens>]`.
   - CLI: `agtoosa graph communities [--json]`.
   - MCP Tool: `agtoosa_get_communities`.

## Architecture

### Gateway Position

```
DEV-033 ingestion ─┐
DEV-035 extraction ─┼─▶ SemanticGateway ─▶ redact ─▶ budget check ─▶ cache lookup
DEV-036 audit     ─┘                                                      │
                                                                   miss ──┴──▶ provider
                                                                   hit  ─────▶ cached
```

One gateway, three consumers. Redaction, budgeting, caching, and opt-in enforcement are implemented once and cannot be bypassed by a consumer.

### Community Detection Replacement

`agtoosa/graph/metrics.py::_detect_communities` currently branches:

| Condition | Today | After this cycle |
|---|---|---|
| networkx present | `greedy_modularity_communities` | Louvain + optional Leiden refinement |
| networkx absent | **union-find connected components** | Louvain (pure Python) |

Both paths now optimise modularity. The dependency-free install is no longer second-class.

## Acceptance Criteria

1. With no provider configured, every semantic CLI path completes as a deterministic no-op and **makes zero network calls** (asserted by a socket-level guard in tests).
2. A payload containing credential-shaped strings is redacted before transmission; the test asserts on the serialized request body, not on intent.
3. `--dry-run` returns a cost estimate and transmits nothing.
4. Exceeding `--budget` halts the pass cleanly with a partial result, never a truncated or corrupt write.
5. A second `semantic enrich` run over an unchanged workspace produces a 100% cache hit rate and spends zero tokens.
6. Pure-Python Louvain produces a **strictly higher modularity score** than connected-components on a fixture with known ground-truth communities.
7. Louvain results are stable across runs given a fixed seed.
8. `agtoosa graph report` and DEV-034's wiki consume the new community output without modification to their call sites.

## Verification Fixtures

- `tests/test_semantic_gateway.py` — stubbed provider only, **no live calls in CI**; asserts redaction on the wire, cache hit/miss behaviour, budget enforcement, and the offline no-op path.
- `tests/test_communities.py` — modularity comparison against connected-components on a known partition, seed stability, and graceful use of the Leiden refinement when networkx is present.
