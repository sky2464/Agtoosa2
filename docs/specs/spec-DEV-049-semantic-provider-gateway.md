# Spec: DEV-049 — Semantic Provider Gateway and Egress Boundary

> **Story ID:** DEV-049  
> **Parent Epic:** [EPIC-001 — Trusted Knowledge Intelligence](epic-001-trusted-knowledge-intelligence.md)  
> **Milestone:** Foundation Gate  
> **Status:** ✅ Done  
> **Impact Rating:** 92 / 100  
> **Research Basis:** Finding R-14 (stated semantic-provider policy has no implementation or owner; no transport, redaction boundary, budget ceiling, or cache)  
> **Dependencies:** DEV-043; gates all semantic consumers (DEV-033, DEV-035, DEV-036)  
> **Spec Created:** 2026-09-14  

---

## 1. Requirements & Goal Contract

### Goal Contract
DEV-049 establishes the single, unified semantic egress boundary and provider gateway for Agtoosa2. In accordance with zero-trust local-first principles, Agtoosa2 operates strictly offline by default. When semantic features (e.g. multimodal analysis in DEV-033, zero-trust extraction in DEV-035, or socratic audit in DEV-036) require model inference, the requests must route through `SemanticGateway`. The gateway enforces: (1) strict offline-by-default gating requiring explicit user opt-in for remote egress, (2) pre-flight zero-leak secret redaction on all outbound payloads, (3) configurable token and call budget ceilings to prevent cost runaways, and (4) deterministic content-addressed prompt/response caching to eliminate duplicate requests.

### User Stories
- **US-1**: As a security-conscious organization, I want Agtoosa2 to strictly block any outbound cloud API calls by default unless explicit provider credentials and egress permission are configured.
- **US-2**: As an engineer operating on proprietary source code, I want all prompts sent to semantic providers to be scrubbed of API keys, private keys, passwords, and tokens before transmission.
- **US-3**: As a budget manager, I want the semantic gateway to enforce hard token and request ceilings and cache responses by content hash so repetitive queries incur zero additional egress.

### Acceptance Criteria (EARS)
- **AC-26 (Offline-by-Default Egress Boundary)**: WHEN any semantic inference is requested without explicit provider configuration or when offline mode is active, the gateway SHALL reject external network access and raise an `EgressPermissionError` or fall back to local provider without making network calls.
- **AC-27 (Pre-Transmission Redaction & Budget Enforcing Cache)**: WHEN a prompt is submitted for external dispatch, the gateway SHALL redact sensitive credentials via `redact_secrets` before serialization, SHALL check the local content-addressed cache (returning cached responses without network egress), and SHALL enforce maximum token and request budgets, aborting with `BudgetExceededError` if limits are exceeded.

---

## 2. Architecture & Data Flow

```mermaid
flowchart TD
    Consumer[Semantic Consumer: DEV-033/035/036] --> Gateway[SemanticGateway]
    
    Gateway --> CheckEgress{Egress Allowed & Configured?}
    CheckEgress -->|No / Offline| Block[Raise EgressPermissionError or Return Local Fallback]
    
    CheckEgress -->|Yes| Redactor[Redact Secrets from Payload]
    Redactor --> CacheCheck{Prompt Hash in Cache?}
    CacheCheck -->|Hit| CacheReturn[Return Cached Response (0 Tokens)]
    
    CacheCheck -->|Miss| BudgetCheck{Within Token & Call Budget?}
    BudgetCheck -->|Exceeded| BudgetError[Raise BudgetExceededError]
    BudgetCheck -->|Allowed| Dispatch[Dispatch via Transport Adapter]
    
    Dispatch --> SaveCache[Save to Local Content Cache]
    SaveCache --> UpdateBudget[Update Cumulative Token Usage]
    UpdateBudget --> Return[Return Response Envelope]
```

---

## 3. Implementation Verification
- Module: `agtoosa/semantic/gateway.py` and `agtoosa/semantic/__init__.py`
- Automated test suite: `tests/test_semantic_gateway.py`
