# Spec: DEV-042 — Atomic Snapshots, Incremental Equivalence, and Manual Record Preservation

> **Story ID:** DEV-042  
> **Parent Epic:** [EPIC-001 — Trusted Knowledge Intelligence](epic-001-trusted-knowledge-intelligence.md)  
> **Milestone:** Foundation Gate  
> **Status:** 📋 In Progress  
> **Impact Rating:** 93 / 100  
> **Research Basis:** Findings R-04 (non-atomic indexing), R-05 (lost relationships from target edits), R-06 (clean rebuild conflates derived and manual records)  
> **Dependencies:** DEV-040, DEV-041  
> **Spec Created:** 2026-09-13  

---

## 1. Requirements & Goal Contract

### Goal Contract
DEV-042 guarantees transactional snapshot integrity and data ownership separation in `GraphStore`. Previously, clean rebuilds (`store.clear()`) indiscriminately wiped manual lifecycle records (stories, criteria, tasks, ADRs, test evidence). Indexing occurred across disconnected SQL transactions, meaning a parse failure left partial or corrupted graphs. DEV-042 introduces atomic snapshot publication, separates derived extraction nodes from manual lifecycle records, and guarantees that clean rebuilds preserve user-authored specifications and evidence.

### User Stories
- **US-1**: As an engineering manager using `agtoosa ship verify`, I want `agtoosa graph build --clean` to refresh the code AST without deleting existing stories, criteria, tasks, or evidence links.
- **US-2**: As an AI coding agent, when an indexing job is interrupted or encounters a syntax crash, I want the store to retain the previous valid complete snapshot rather than a broken, partial graph.
- **US-3**: As a developer, when a called function is renamed or moved, I want the indexer to recompute references from callers rather than leaving dangling or deleted edges.

### Acceptance Criteria (EARS)
- **AC-07 (Atomic Publication & Rollback)**: WHEN an indexing batch is published, it SHALL commit nodes, edges, fingerprints, and snapshot metadata in a single atomic transaction. Any error SHALL trigger rollback, preserving the prior valid snapshot.
- **AC-08 (Incremental Equivalence)**: GIVEN identical repository state, an incremental index update SHALL produce equivalent nodes and edges as a clean index run.
- **AC-09 (Manual Record Preservation)**: WHEN `store.clear(preserve_manual=True)` or `store.clear_derived()` is invoked, all nodes with types `story`, `criterion`, `task`, `adr`, `doc`, or `evidence` SHALL be preserved.

---

## 2. Implementation Verification
- Module: `agtoosa/graph/store.py`, `agtoosa/parser/__init__.py`
- Test suite: `tests/test_snapshot_integrity.py`
