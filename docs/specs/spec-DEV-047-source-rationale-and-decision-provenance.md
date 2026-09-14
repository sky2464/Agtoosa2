# Spec: DEV-047 — Source Rationale and Decision Provenance

> **Story ID:** DEV-047  
> **Parent Epic:** [EPIC-001 — Trusted Knowledge Intelligence](epic-001-trusted-knowledge-intelligence.md)  
> **Milestone:** Foundation Gate  
> **Status:** ✅ Done  
> **Impact Rating:** 86 / 100  
> **Research Basis:** Finding R-12 (comment rationale discarded at parse time)  
> **Spec Created:** 2026-09-13  

---

## 1. Requirements & Goal Contract

### Goal Contract
DEV-047 resolves research finding R-12: existing code parsers discarded `# WHY:`, `# NOTE:`, `# HACK:`, and `# ASSUMPTION:` comments, depriving AI coding agents of essential decision rationale and architectural intent. DEV-047 introduces `agtoosa/parser/rationale.py` to scan comment markers, bind each rationale to its enclosing symbol scope (or file span if module-level) without guessing, extract lifecycle citations (`ADR-*`, `DEV-*`), and apply secret redaction before persisting into the knowledge graph.

### User Stories
- **US-1**: As an AI coding assistant, I want context packs to include `# WHY:` and `# HACK:` comments adjacent to symbols so I do not inadvertently revert deliberate architectural trade-offs.
- **US-2**: As a developer, I want my decision rationale to link to cited ADRs (`doc:ADR-001`) with `EVIDENCED_BY` edges in the knowledge graph.
- **US-3**: As a security officer, I want credentials or secrets accidentally placed in comment notes to be redacted before entering graph nodes.

### Acceptance Criteria (EARS)
- **AC-22 (Scoped Symbol Binding)**: WHEN a comment rationale is inside a function or class line range, it SHALL be bound to that enclosing symbol's ID. When at module level, it SHALL remain at file span without being guessed onto neighboring symbols.
- **AC-23 (Citations & Redaction)**: WHEN comment text references `ADR-\d+` or `DEV-\d+`, the extractor SHALL generate `EVIDENCED_BY` edges to cited documents. Any secret patterns SHALL be redacted via `redact_secrets`.

---

## 2. Implementation Verification
- Module: `agtoosa/parser/rationale.py`
- Test suite: `tests/test_rationale.py` (3 tests passing)
