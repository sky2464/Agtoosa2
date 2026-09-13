"""CLI commands for runtime observability and telemetry heatmaps (DEV-017 / Stage 17)."""

import json
from pathlib import Path
from typing import Any

from agtoosa.graph.store import GraphStore
from agtoosa.cli.graph_cmd import get_default_db_path
from agtoosa.observability.ingester import TelemetryIngester


def cmd_telemetry(args: Any, workspace_root: Path) -> int:
    """Dispatcher for 'agtoosa telemetry' subcommands."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    ingester = TelemetryIngester(store, workspace_root)

    action = getattr(args, "telem_action", None)

    if action == "ingest":
        target_file = Path(args.file)
        if not target_file.is_absolute():
            target_file = (workspace_root / target_file).resolve()

        try:
            res = ingester.ingest_file(target_file, format_hint=getattr(args, "format", None))
            print("📈 Runtime Telemetry Ingestion Complete:")
            print(f"   • File: {target_file.name}")
            print(f"   • Detected Format: {res['format'].upper()}")
            print(f"   • Records Ingested: {res['ingested_records']}")
            return 0
        except Exception as e:
            print(f"❌ Failed to ingest telemetry: {e}")
            return 1

    elif action == "traces":
        target_file = Path(args.file)
        if not target_file.is_absolute():
            target_file = (workspace_root / target_file).resolve()

        from agtoosa.observability.traces import TraceTopologyEngine
        trace_engine = TraceTopologyEngine(store, workspace_root)
        stitch_ast = not getattr(args, "no_stitch", False)

        try:
            res = trace_engine.ingest_file(
                target_file,
                format_hint=getattr(args, "format", None),
                stitch_ast=stitch_ast
            )
            if getattr(args, "json", False):
                print(json.dumps(res, indent=2))
                return 0

            print("🌐 Distributed Trace & Service Topology Ingestion Complete:")
            print(f"   • Trace File: {target_file.name}")
            print(f"   • Detected Format: {res['format'].upper()}")
            print(f"   • Total Spans Parsed: {res['total_spans']}")
            print(f"   • Services Discovered: {res['services_discovered']}")
            print(f"   • Network Edges Reconstructed: {res['network_edges_created']}")
            print(f"   • AST Endpoints Stitched: {res['stitched_ast_endpoints']}")
            return 0
        except Exception as e:
            print(f"❌ Failed to ingest distributed traces: {e}")
            return 1

    elif action == "status":
        all_t = store.get_all_telemetry()
        total_calls = sum(t["call_count"] for t in all_t.values())
        total_errors = sum(t["error_count"] for t in all_t.values())

        if getattr(args, "json", False):
            print(json.dumps({
                "tracked_nodes_count": len(all_t),
                "total_calls": total_calls,
                "total_errors": total_errors,
                "overall_error_rate": total_errors / total_calls if total_calls > 0 else 0.0
            }, indent=2))
            return 0

        print("📊 Runtime Observability Status:")
        print(f"   • Tracked Symbols / Nodes: {len(all_t)}")
        print(f"   • Total Recorded Invocations: {total_calls:,}")
        print(f"   • Total Runtime Errors: {total_errors:,}")
        if total_calls > 0:
            print(f"   • Global Error Rate: {(total_errors / total_calls) * 100:.2f}%")
        else:
            print("   • Telemetry is empty. Ingest with 'agtoosa telemetry ingest <file>'.")
        return 0

    elif action == "heatmap":
        top_k = getattr(args, "top", 20)
        hotspots = ingester.compute_heatmaps(top_k=top_k)

        if getattr(args, "json", False):
            print(json.dumps([h.to_dict() for h in hotspots], indent=2))
            return 0

        print(f"🔥 Runtime Execution Heatmap (Top {len(hotspots)} Hotspots):\n")
        if not hotspots:
            print("   No telemetry data recorded yet. Ingest traces with 'agtoosa telemetry ingest <file>'.")
            return 0

        level_icons = {
            "CRITICAL": "🔴 CRITICAL",
            "HIGH": "🟠 HIGH",
            "MEDIUM": "🟡 MEDIUM",
            "LOW": "🔵 LOW",
            "COLD": "⚪ COLD",
        }

        print(f"   {'Level':<12} {'Composite':<10} {'Calls':<10} {'Avg Latency':<14} {'Symbol / Target'}")
        print("   " + "-" * 75)
        for h in hotspots:
            icon = level_icons.get(h.heat_level, h.heat_level)
            print(
                f"   {icon:<12} {h.composite_heat:<10.3f} {h.call_count:<10} "
                f"{h.avg_duration_ms:<14.2f}ms {h.name} ({h.path or 'unmapped'})"
            )
        return 0

    elif action == "clear":
        cleared = store.clear_telemetry()
        print(f"🧹 Cleared {cleared} runtime telemetry records.")
        return 0

    return 0
