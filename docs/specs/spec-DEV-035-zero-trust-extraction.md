# DEV-035: Zero-Trust Multi-Agent Semantic Extraction & Hallucination Guard

## Status
- **Status:** ✅ Implemented & Verified
- **Cycle ID:** DEV-035
- **Layer:** Semantic / Extraction / Security Boundary
- **Dependencies:** DEV-040, DEV-041, DEV-043, DEV-049

## Context & Problem Statement
In contrast to codebases where AST parsers provide ground truth, extracting concepts and entity relationships from non-code artifacts (requirements, RFCs, PDFs, architectural ADRs, meeting notes) introduces the hazard of LLM hallucinations. If an extraction agent asserts that `Requirement-42` relates to a non-existent method `AuthService.verifyJwtToken()`, the knowledge graph is polluted with zombie references.

## Acceptance Criteria
- **AC-1 (Deterministic Ground-Truth Baseline)**: WHEN extracting relationships, AST code parsers SHALL remain the sole authority, with zero LLM re-extraction of code symbols.
- **AC-2 (Zero-Trust Hallucination Guard)**: WHEN semantic non-code extraction asserts links to code, the `HallucinationGuard` SHALL reject or remediate ungrounded entity references.
- **AC-3 (Persistent Semantic Cache & Gateway)**: WHEN non-code documents are processed, extraction results SHALL be cached content-addressably and bounded by `SemanticGateway`.

## Architectural Decision & Invariants
1. **Deterministic Code Baseline First (Zero LLM Re-Extraction)**:
   - Code files are never parsed via LLMs. AST parsers (tree-sitter/native Python) remain the sole ground-truth authority for code symbols.
2. **Tri-State Confidence Classification**:
   - `EXTRACTED`: Verifiable direct textual quote or syntax citation.
   - `INFERRED`: Reasonable semantic deduction based on documentation context.
   - `AMBIGUOUS`: Uncertain connection where multiple symbol candidates exist or documentation is imprecise.
3. **Zero-Trust Hallucination Guard (`HallucinationGuard`)**:
   - Every semantic relationship proposing a connection to code must be validated against `GraphStore`.
   - If the code symbol does not exist in AST storage, the edge is rejected or flagged with status `HALLUCINATED_UNVERIFIED`.
   - Levenshtein distance fuzzy-matching automatically computes and presents the closest existing code symbols as remediation candidates.
4. **Persistent Content-Addressed Semantic Cache**:
   - SHA-256 digest of non-code document text caches semantic extraction outputs in `.agtoosa/cache/semantic/`, preventing redundant execution and egress token consumption.
5. **Gateway Compliance (DEV-049)**:
   - All LLM interactions flow strictly through `SemanticGateway`, adhering to offline-by-default, secret redaction, and token budgeting rules.

## Interfaces & CLI
- CLI Command: `agtoosa extract semantic [--dir <path>] [--chunk-size <N>] [--strict-grounding] [--json]`
- MCP Server Tool: `agtoosa_validate_semantic_graph`
