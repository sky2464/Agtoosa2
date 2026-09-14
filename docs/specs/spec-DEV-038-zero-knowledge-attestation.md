# DEV-038: Zero-Knowledge Architecture Cryptographic Attestation

> **Cycle:** DEV-038  
> **Milestone:** Milestone 15 (v0.9.0)  
> **Status:** Active / In Implementation  
> **Type:** Security & Trust Architecture  

---

## 1. Problem Statement

In enterprise ecosystems, regulated industries, vendor audits, and multi-team codebases, organizations must frequently prove that their systems adhere to strict architectural invariants:
- **No Layer Boundary Violations**: Lower tiers (e.g. Domain Core Tier 3) must never import or call upper tiers (e.g. Entrypoints Tier 1).
- **No Circular Dependencies**: Codebase must be strictly acyclic across modules.
- **Controlled Blast Radius**: Foundational symbols do not exceed designated caller thresholds.

However, organizations cannot share proprietary source code, internal file paths, or symbol identifiers with external auditors, customers, or untrusted CI environments.

A **Zero-Knowledge Architecture Cryptographic Attestation** allows a prover (the codebase owner) to generate a mathematically verifiable, tamper-evident attestation certificate that proves compliance with all architectural invariants, while keeping file paths, symbol names, and source logic completely confidential.

---

## 2. Invariants & Mathematical Formulation

### 2.1 Salted Blind Commitments
Each symbol and file path is salted and cryptographically hashed:
$$\text{BlindID}(s) = \text{SHA-256}(\text{salt} \parallel s)$$
The attestation reports only blinded node IDs and their declared/derived architectural tier ($T_1, T_2, T_3$). No plain text symbol names or file paths are included in the public attestation payload.

### 2.2 Merkle Invariant Proofs
1. **Edge Compliance**: Every directed dependency edge $(u, v)$ is evaluated against tier ordering. A valid edge requires:
   $$\text{Tier}(u) \le \text{Tier}(v)$$
   Compliant edges are hashed into leaf nodes:
   $$\text{Leaf}_i = \text{SHA-256}(\text{BlindID}(u) \parallel \text{BlindID}(v) \parallel \text{EdgeType})$$
2. **Merkle Tree Construction**: Leaves are iteratively combined in pairs:
   $$\text{Parent} = \text{SHA-256}(\text{Left} \parallel \text{Right})$$
   yielding a single `merkle_root` representing the entire compliant architecture topology.
3. **Cycle Freedom Proof**: The attestation includes topological sort / Tarjan verification evidence, asserting the count of strongly connected components (SCCs) of size $> 1$ is exactly zero.

### 2.3 Cryptographic Attestation Envelope
The attestation document contains:
- `version`: Protocol version (e.g. `"1.0"`).
- `timestamp`: ISO-8601 UTC timestamp.
- `workspace_hash`: SHA-256 hash of git tree commit or workspace content summary.
- `merkle_root`: Merkle root of compliant architecture graph.
- `node_count`: Total count of blinded nodes.
- `edge_count`: Total count of compliant edges.
- `tier_distribution`: Aggregate count of nodes per tier (Tier 1, Tier 2, Tier 3).
- `cycles_count`: Must be `0` for an invariant-passing codebase.
- `violations_count`: Must be `0` for an invariant-passing codebase.
- `signature`: HMAC-SHA256 signature generated with an attestation signing key:
  $$\text{Signature} = \text{HMAC-SHA256}(\text{key}, \text{canonical\_json}(\text{payload}))$$

### 2.4 Zero-Knowledge Verification
A verifier:
1. Validates the digital signature (if signing key provided) to ensure authenticity.
2. Checks that `violations_count == 0` and `cycles_count == 0`.
3. Verifies the Merkle root and leaf consistency.
4. Verifies timestamp freshness.
5. Returns `(valid, details)` without needing any access to the underlying repository.

---

## 3. Interfaces & Surface Area

### 3.1 Python Engine (`agtoosa/security/attestation.py`)
- `ArchitectureAttestationEngine`:
  - `generate_attestation(store: GraphStore, signing_key: Optional[str] = None, salt: Optional[str] = None) -> Dict[str, Any]`
  - `verify_attestation(attestation: Dict[str, Any], signing_key: Optional[str] = None) -> Tuple[bool, List[str]]`

### 3.2 CLI Commands (`agtoosa/cli/attest_cmd.py`)
- `agtoosa attest generate [--output <path>] [--key <secret>] [--salt <salt>] [--json]`
- `agtoosa attest verify <path> [--key <secret>] [--json]`

### 3.3 MCP Server Tools (`agtoosa/mcp/server.py`)
- `agtoosa_generate_attestation`: Generates zero-knowledge attestation payload for connected agents.
- `agtoosa_verify_attestation`: Verifies zero-knowledge attestation document.

---

## 4. Verification & Testing Strategy
- Unit tests in `tests/test_attestation.py`:
  - Verify blind commitment confidentiality (zero source code, symbol names, or paths leaked).
  - Verify Merkle root determinism.
  - Verify detection and rejection of tampered fields, forged signatures, and violated invariants.
  - Verify CLI commands and MCP tool executions.
