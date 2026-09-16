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

    elif action == "causal":
        from agtoosa.observability.causal import CausalEngine
        from agtoosa.graph.query import resolve_node

        source_val = getattr(args, "source_flag", None) or getattr(args, "source", None)
        target_val = getattr(args, "target_flag", None) or getattr(args, "target", None)
        if not source_val or not target_val:
            print("❌ Both source (cause) and target (effect) are required for causal inference.")
            return 1

        src_node = resolve_node(store, source_val)
        tgt_node = resolve_node(store, target_val)

        src_id = src_node["id"] if src_node else source_val
        tgt_id = tgt_node["id"] if tgt_node else target_val

        nodes = store.get_all_nodes()
        edges = store.get_all_edges()

        causal_eng = CausalEngine(nodes, edges)

        adj_set = causal_eng.find_minimal_adjustment_set(src_id, tgt_id)
        is_admissible, msg = causal_eng.is_backdoor_admissible(src_id, tgt_id, adj_set or set())

        data_file = getattr(args, "data", None)
        obs_data = []
        causal_res = None
        if data_file:
            data_path = Path(data_file)
            if not data_path.is_absolute():
                data_path = (workspace_root / data_path).resolve()
            if data_path.exists():
                try:
                    obs_data = json.loads(data_path.read_text(encoding="utf-8"))
                    causal_res = causal_eng.compute_causal_effect(src_id, tgt_id, obs_data)
                except Exception as e:
                    print(f"⚠️  Failed to parse contingency data file: {e}")

        as_json = getattr(args, "json", False)

        result = {
            "source": src_id,
            "source_name": src_node["name"] if src_node else src_id,
            "target": tgt_id,
            "target_name": tgt_node["name"] if tgt_node else tgt_id,
            "is_admissible": is_admissible,
            "minimal_adjustment_set": list(adj_set) if adj_set else [],
            "status_message": msg
        }
        if causal_res:
            result["causal_effect"] = causal_res

        if as_json:
            print(json.dumps(result, indent=2))
        else:
            print("\n🔮 Causal Architecture Inference: Pearl's Do-Calculus (DEV-055)")
            print("=" * 75)
            print(f"Cause Variable (X):          {result['source_name']} ({result['source']})")
            print(f"Effect Variable (Y):         {result['target_name']} ({result['target']})")
            print(f"Back-Door Admissible:        {'✅ YES' if is_admissible else '❌ NO'}")
            print(f"Minimal Adjustment Set (Z):  {', '.join(result['minimal_adjustment_set']) if result['minimal_adjustment_set'] else 'None required (unconfounded)'}")

            if causal_res:
                print("\n📊 Empirical Interventional Estimation:")
                print(f"   • Average Causal Effect (ACE):   {causal_res['average_causal_effect']}")
                print(f"   • Naive Observational Diff:      {causal_res['naive_observational_diff']}")
                print(f"   • Confounding Detected:          {'⚠️  YES (Correlation != Causation)' if causal_res['is_confounded'] else '✅ NO (Observational holds)'}")
            else:
                print("\n💡 Tip: Provide empirical event observations with '--data <contingency.json>' to estimate quantitative ACE.")
            print("=" * 75 + "\n")

        return 0

    return 0
