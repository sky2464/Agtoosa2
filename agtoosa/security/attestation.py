"""Zero-Knowledge Architecture Cryptographic Attestation Engine.

Generates and verifies cryptographically signed architectural compliance proofs,
salted blind commitments, and Merkle tree roots without revealing confidential
symbol names, file paths, or proprietary source code.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import secrets
from typing import Any, Dict, List, Optional, Tuple

from agtoosa.graph.store import GraphStore
from agtoosa.graph.metrics import MetricsEngine
from agtoosa.review.intelligence import ReviewIntelligenceEngine


class ArchitectureAttestationEngine:
    """Zero-knowledge cryptographic attestation for software architecture invariants."""

    PROTOCOL_VERSION = "1.0"

    def __init__(self, store: GraphStore, workspace_root: Optional[Path] = None):
        self.store = store
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.intelligence = ReviewIntelligenceEngine(store, self.workspace_root)
        self.metrics = MetricsEngine(store)

    @staticmethod
    def blind_id(raw_id: str, salt: str) -> str:
        """Compute salted blind commitment for a symbol or node identifier."""
        salted_data = f"{salt}:{raw_id}".encode("utf-8")
        return hashlib.sha256(salted_data).hexdigest()

    @staticmethod
    def compute_merkle_root(leaf_hashes: List[str]) -> str:
        """Construct a deterministic Merkle root from a collection of leaf hashes."""
        if not leaf_hashes:
            return hashlib.sha256(b"").hexdigest()

        # Sort deterministically
        current_level = sorted(leaf_hashes)

        while len(current_level) > 1:
            next_level: List[str] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                else:
                    right = left  # Duplicate odd tail
                combined = f"{left}:{right}".encode("utf-8")
                next_level.append(hashlib.sha256(combined).hexdigest())
            current_level = next_level

        return current_level[0]

    def generate_attestation(
        self,
        signing_key: Optional[str] = None,
        salt: Optional[str] = None,
        include_leaves: bool = False
    ) -> Dict[str, Any]:
        """Generate a zero-knowledge architectural compliance attestation.

        Guarantees that no plain text symbols, paths, or code logic are included.
        """
        active_salt = salt or secrets.token_hex(16)

        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        tier_counts = {
            "tier_1_entrypoints": 0,
            "tier_2_services": 0,
            "tier_3_domain_core": 0,
            "unclassified": 0
        }

        blinded_node_tiers: Dict[str, int] = {}
        for node in nodes:
            blinded = self.blind_id(node["id"], active_salt)
            tier = self.intelligence._get_path_tier(node.get("path", ""))
            if tier == 1:
                tier_counts["tier_1_entrypoints"] += 1
                blinded_node_tiers[blinded] = 1
            elif tier == 2:
                tier_counts["tier_2_services"] += 1
                blinded_node_tiers[blinded] = 2
            elif tier == 3:
                tier_counts["tier_3_domain_core"] += 1
                blinded_node_tiers[blinded] = 3
            else:
                tier_counts["unclassified"] += 1

        # Evaluate layer boundary compliance & construct leaves
        leaf_hashes: List[str] = []
        violations_count = 0
        blinded_violations: List[Dict[str, Any]] = []

        for edge in edges:
            edge_type = edge.get("edge_type", "")
            if edge_type not in ("imports", "calls"):
                continue

            src_id = edge["source_id"]
            tgt_id = edge["target_id"]

            src_node = self.store.get_node(src_id)
            tgt_node = self.store.get_node(tgt_id)
            if not src_node or not tgt_node:
                continue

            src_tier = self.intelligence._get_path_tier(src_node.get("path", ""))
            tgt_tier = self.intelligence._get_path_tier(tgt_node.get("path", ""))

            blind_src = self.blind_id(src_id, active_salt)
            blind_tgt = self.blind_id(tgt_id, active_salt)

            # Invariant: Tier X must never import Tier Y where X > Y (lower tier importing higher tier)
            if src_tier and tgt_tier and src_tier > tgt_tier:
                violations_count += 1
                blinded_violations.append({
                    "blind_source": blind_src,
                    "blind_target": blind_tgt,
                    "source_tier": src_tier,
                    "target_tier": tgt_tier,
                    "edge_type": edge_type
                })
            else:
                leaf_payload = f"{blind_src}:{blind_tgt}:{edge_type}".encode("utf-8")
                leaf_hashes.append(hashlib.sha256(leaf_payload).hexdigest())

        # Cycle detection
        cycles = self.metrics.detect_cycles()
        cycles_count = len(cycles)

        merkle_root = self.compute_merkle_root(leaf_hashes)

        # Workspace state fingerprint
        workspace_raw = f"{len(nodes)}:{len(edges)}:{merkle_root}".encode("utf-8")
        workspace_hash = hashlib.sha256(workspace_raw).hexdigest()

        payload: Dict[str, Any] = {
            "version": self.PROTOCOL_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "salt": active_salt,
            "merkle_root": merkle_root,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "tier_distribution": tier_counts,
            "cycles_count": cycles_count,
            "violations_count": violations_count,
            "compliant_leaf_count": len(leaf_hashes),
            "workspace_hash": workspace_hash,
            "blinded_violations": blinded_violations[:10]  # capped sample if any
        }

        if include_leaves:
            payload["leaf_hashes"] = sorted(leaf_hashes)

        if signing_key:
            canonical_repr = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            signature = hmac.new(
                signing_key.encode("utf-8"),
                canonical_repr.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            payload["signature"] = signature
        else:
            payload["signature"] = None

        return payload

    @classmethod
    def verify_attestation(
        cls,
        attestation: Dict[str, Any],
        signing_key: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """Verify an architectural attestation document in zero-knowledge.

        Returns (is_valid, validation_log).
        """
        errors: List[str] = []

        if not isinstance(attestation, dict):
            return False, ["Attestation payload must be a JSON object."]

        version = attestation.get("version")
        if version != cls.PROTOCOL_VERSION:
            errors.append(f"Unsupported protocol version '{version}'. Expected '{cls.PROTOCOL_VERSION}'.")

        # 1. Cryptographic Signature Verification
        expected_sig = attestation.get("signature")
        if signing_key:
            if not expected_sig:
                errors.append("Signing key provided but attestation is unsigned.")
            else:
                clone = {k: v for k, v in attestation.items() if k != "signature"}
                canonical_repr = json.dumps(clone, sort_keys=True, separators=(",", ":"))
                computed_sig = hmac.new(
                    signing_key.encode("utf-8"),
                    canonical_repr.encode("utf-8"),
                    hashlib.sha256
                ).hexdigest()
                if not hmac.compare_digest(computed_sig, expected_sig):
                    errors.append("Cryptographic signature mismatch: attestation may have been tampered with.")

        # 2. Invariant Verification
        violations = attestation.get("violations_count", 0)
        if violations > 0:
            errors.append(f"Attestation records {violations} layer boundary violation(s).")

        cycles = attestation.get("cycles_count", 0)
        if cycles > 0:
            errors.append(f"Attestation records {cycles} cyclic dependency violation(s).")

        # 3. Merkle Integrity Verification
        merkle_root = attestation.get("merkle_root")
        if not merkle_root or not isinstance(merkle_root, str) or len(merkle_root) != 64:
            errors.append(f"Invalid or malformed Merkle root '{merkle_root}'.")

        # If optional leaves are provided, verify the Merkle root directly
        leaf_hashes = attestation.get("leaf_hashes")
        if isinstance(leaf_hashes, list) and leaf_hashes:
            recomputed_root = cls.compute_merkle_root(leaf_hashes)
            if recomputed_root != merkle_root:
                errors.append("Merkle root mismatch when recomputing from provided leaf hashes.")

        is_valid = len(errors) == 0
        if is_valid:
            log = [
                "Zero-Knowledge Attestation Verified Successfully:",
                f"  - Protocol: v{version}",
                f"  - Merkle Root: {merkle_root}",
                f"  - Compliant Edges: {attestation.get('compliant_leaf_count', 0)}",
                f"  - Layer Boundary Violations: 0",
                f"  - Cyclic Dependencies: 0",
                f"  - Signature Verified: {'Yes' if signing_key and expected_sig else 'Unsigned'}"
            ]
            return True, log

        return False, errors
