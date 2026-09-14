"""CLI command handler for agtoosa synthesize (DEV-039 / Stage 39)."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from agtoosa.cli.graph_cmd import get_default_db_path
from agtoosa.graph.store import GraphStore
from agtoosa.federation.synthesis import MicroserviceSynthesizer


def cmd_synthesize(args: Any, workspace_root: Path) -> int:
    """Execute autonomous microservice synthesis operations."""
    sub = getattr(args, "synthesize_subcommand", None)
    if sub != "microservice":
        print("Usage: agtoosa synthesize microservice [options]", file=sys.stderr)
        return 1

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"❌ Knowledge graph database not found at {db_path}. Run 'agtoosa graph build' first.", file=sys.stderr)
        return 1

    store = GraphStore(db_path)
    synthesizer = MicroserviceSynthesizer(store, workspace_root)

    service_name = getattr(args, "service", None)
    target_lang = getattr(args, "target", "python")
    fmt = getattr(args, "format", "all")
    output_str = getattr(args, "output", None)

    inferred_name, endpoints, schemas = synthesizer.discover_service_endpoints(service_name)
    actual_svc = service_name or inferred_name

    output_dir = Path(output_str) if output_str else workspace_root / "generated" / actual_svc

    try:
        created_files = synthesizer.synthesize_microservice_bundle(
            service_name=actual_svc,
            output_dir=output_dir,
            target_lang=target_lang,
            format_type=fmt
        )
    except Exception as e:
        print(f"❌ Synthesis error: {e}", file=sys.stderr)
        return 1

    if getattr(args, "json", False):
        res = {
            "status": "success",
            "service": actual_svc,
            "target_language": target_lang,
            "format": fmt,
            "output_directory": str(output_dir.resolve()),
            "endpoints_count": len(endpoints),
            "schemas_count": len(schemas),
            "files": created_files
        }
        print(json.dumps(res, indent=2))
    else:
        print(f"🚀 Synthesized Microservice Bundle for '{actual_svc}':")
        print(f"   • Endpoints Discovered: {len(endpoints)}")
        print(f"   • Schemas Discovered:   {len(schemas)}")
        print(f"   • Target Language:      {target_lang}")
        print(f"   • Format:               {fmt}")
        print(f"   • Output Directory:     {output_dir.resolve()}")
        print("   • Generated Artifacts:")
        for fname, fpath in created_files.items():
            print(f"     ✅ {fname} -> {fpath}")

    return 0
