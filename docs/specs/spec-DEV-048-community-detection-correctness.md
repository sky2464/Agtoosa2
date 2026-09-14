# Spec: DEV-048 — Community Detection Correctness Across Install Profiles

> **Story ID:** DEV-048  
> **Parent Epic:** [EPIC-001 — Trusted Knowledge Intelligence](epic-001-trusted-knowledge-intelligence.md)  
> **Milestone:** Foundation Gate  
> **Status:** ✅ Done  
> **Impact Rating:** 85 / 100  
> **Research Basis:** Finding R-13 (connected components vs modularity clustering)  
> **Spec Created:** 2026-09-13  

---

## 1. Requirements & Goal Contract

### Goal Contract
DEV-048 resolves research finding R-13: previous community detection fell back to union-find connected components whenever NetworkX was missing. Connected components compute *reachability*, not *community clustering*, meaning a dependency-free install and a full install answered completely different questions. DEV-048 moves community detection into a dedicated module `agtoosa/graph/community.py`, implements a first-party deterministic greedy modularity optimizer in pure Python, and reports modularity $Q$ and the algorithm used alongside every partition.

### User Stories
- **US-1**: As an engineer running in a zero-dependency environment, I want `agtoosa graph report` to compute true modularity-based communities rather than weakly connected components.
- **US-2**: As an AI coding agent, I want community detection to report `is_available: false` when a graph is too small or sparse rather than fabricating arbitrary single-component clusters.
- **US-3**: As an architect, I want community partitions to be 100% deterministic across multiple runs for identical graph snapshots.

### Acceptance Criteria (EARS)
- **AC-24 (Install Profile Equivalence)**: WHEN community detection is executed on a dependency-free install, it SHALL execute a first-party greedy modularity optimizer rather than a connected-components union-find algorithm.
- **AC-25 (Sparse Graph Handling & Determinism)**: WHEN a graph has fewer than 3 nodes or fewer than 2 edges, the system SHALL report `is_available: false` with an explicit reason. When executed on a partitioned graph, output SHALL be deterministic across runs.

---

## 2. Implementation Verification
- Module: `agtoosa/graph/community.py`
- Metrics integration: `agtoosa/graph/metrics.py`
- Test suite: `tests/test_communities.py` (3 tests passing)
