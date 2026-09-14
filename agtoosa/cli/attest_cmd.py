"""CLI command handler for agtoosa attest (DEV-038 / Stage 38)."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from agtoosa.cli.graph_cmd import get_default_db_path
from agtoosa.graph.store import GraphStore
from agtoosa.security.attestation import ArchitectureAttestationEngine


def cmd_attest(args: Any, workspace_root: Path) -> int:
    """Execute zero-knowledge architecture attestation operations."""
    subcommand = getattr(args, "attest_subcommand", None)

    if subcommand == "generate":
        db_path = get_default_db_path(workspace_root)
        if not db_path.exists():
            print(f"❌ Knowledge graph database not found at {db_path}. Run 'agtoosa graph build' first.", file=sys.stderr)
            return 1

        store = GraphStore(db_path)
        engine = ArchitectureAttestationEngine(store, workspace_root)

        signing_key = getattr(args, "key", None)
        salt = getattr(args, "salt", None)
        include_leaves = getattr(args, "include_leaves", False)

        attestation = engine.generate_attestation(
            signing_key=signing_key,
            salt=salt,
            include_leaves=include_leaves
        )

        output_path = getattr(args, "output", None)
        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(json.dumps(attestation, indent=2), encoding="utf-8")
            if not getattr(args, "json", False):
                print(f"🔒 Attestation saved to {out_file.resolve()}")

        if getattr(args, "json", False):
            print(json.dumps(attestation, indent=2))
        else:
            verdict = "COMPLIANT" if attestation["violations_count"] == 0 and attestation["cycles_count"] == 0 else "NON_COMPLIANT"
            icon = "✅" if verdict == "COMPLIANT" else "❌"
            print(f"{icon} Zero-Knowledge Architecture Attestation Certificate:")
            print(f"   • Protocol Version: v{attestation['version']}")
            print(f"   • Merkle Root:      {attestation['merkle_root']}")
            print(f"   • Workspace Hash:   {attestation['workspace_hash']}")
            print(f"   • Blind Nodes:      {attestation['node_count']}")
            print(f"   • Compliant Edges:  {attestation['compliant_leaf_count']}")
            tiers = attestation.get("tier_distribution", {})
            print(f"   • Tiers:            T1:{tiers.get('tier_1_entrypoints', 0)} | T2:{tiers.get('tier_2_services', 0)} | T3:{tiers.get('tier_3_domain_core', 0)}")
            print(f"   • Violations:       {attestation['violations_count']}")
            print(f"   • Cycles:           {attestation['cycles_count']}")
            print(f"   • Signed:           {'Yes (HMAC-SHA256)' if attestation.get('signature') else 'Unsigned'}")

        return 0 if attestation["violations_count"] == 0 and attestation["cycles_count"] == 0 else 1

    elif subcommand == "verify":
        target_path = Path(getattr(args, "path", ""))
        if not target_path.exists():
            print(f"❌ Attestation file '{target_path}' not found.", file=sys.stderr)
            return 1

        try:
            payload = json.loads(target_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"❌ Failed to parse attestation JSON: {e}", file=sys.stderr)
            return 1

        signing_key = getattr(args, "key", None)
        valid, log = ArchitectureAttestationEngine.verify_attestation(payload, signing_key=signing_key)

        if getattr(args, "json", False):
            res = {
                "valid": valid,
                "log": log,
                "merkle_root": payload.get("merkle_root"),
                "version": payload.get("version")
            }
            print(json.dumps(res, indent=2))
        else:
            if valid:
                print("🛡️  Zero-Knowledge Architectural Attestation: VERIFIED VALID")
                for line in log:
                    print(line)
            else:
                print("❌ Zero-Knowledge Architectural Attestation: VERIFICATION FAILED")
                for line in log:
                    print(f"  • {line}")

        return 0 if valid else 1

    else:
        print("Usage: agtoosa attest {generate,verify} [options]", file=sys.stderr)
        return 1
