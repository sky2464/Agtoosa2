"""CLI commands for autonomous architecture refactoring (DEV-019, DEV-020, DEV-022)."""

import json
from pathlib import Path
from typing import Any

from agtoosa.refactor.engine import RefactorEngine
from agtoosa.refactor.dead_code import format_dead_code_text, format_diffstat


def cmd_refactor_decouple(args: Any, workspace_root: Path) -> int:
    """Analyze cyclic dependencies and generate architectural decoupling blueprints."""
    from agtoosa.cli.graph_cmd import get_default_db_path
    from agtoosa.graph.store import GraphStore
    from agtoosa.refactor.decoupler import CycleDecouplerEngine

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    engine = CycleDecouplerEngine(store, workspace_root)
    report = engine.analyze_cycles()


    if getattr(args, "json", False):
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print(f"🔄 Automated Cycle Decoupler:")
    print(f"   • Total Cycles Detected: {report.total_cycles_detected}")

    if not report.strategies:
        print("\n   ✨ Zero cyclic dependencies detected in architecture graph! Graph is perfectly acyclic (DAG).")
        return 0

    print(f"\n   📋 Proposed Decoupling Blueprints ({len(report.strategies)}):")
    for idx, strat in enumerate(report.strategies, start=1):
        print(f"\n   [{idx}] Pattern: 💡 {strat.strategy_type}")
        print(f"       Cycle: {' ➔ '.join(strat.cycle)}")
        print(f"       Recommended Cut: {strat.cut_edge[0]} ➔ {strat.cut_edge[1]}")
        print(f"       Rationale: {strat.rationale}")
        print(f"       Steps:")
        for s in strat.refactor_steps:
            print(f"         {s}")
        print(f"\n       Generated Blueprint Stub:")
        for line in strat.generated_code_stub.splitlines():
            print(f"         {line}")

    if getattr(args, "apply", False) or getattr(args, "dry_run", False):
        dry_run = getattr(args, "dry_run", False)
        refactor_engine = RefactorEngine(workspace_root)
        plan = refactor_engine.create_decouple_plan(report.strategies[0])
        res = refactor_engine.apply_plan(plan, dry_run=dry_run)

        if dry_run:
            print("\n🔍 Dry Run Unified Diffs:")
            for path, diff in res.get("diffs", {}).items():
                print(f"--- {path} ---")
                print(diff)
        else:
            print(f"\n🚀 Applied decoupling plan ({res['files_affected']} file(s) created/modified)")
            print(f"   📦 Backup ID: {res['backup_id']} (use 'agtoosa refactor rollback {res['backup_id']}' to revert)")

    return 0


def cmd_refactor_dead_code(args: Any, workspace_root: Path) -> int:
    """Identify dead code / zombie symbols and generate safe deletion blueprints."""
    from agtoosa.cli.graph_cmd import get_default_db_path
    from agtoosa.graph.store import GraphStore
    from agtoosa.refactor.dead_code import DeadCodePruner

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    min_confidence = getattr(args, "min_confidence", "low")
    verbose = getattr(args, "verbose", False)
    show_diff = getattr(args, "diff", False)
    pruner = DeadCodePruner(store, workspace_root)

    report = pruner.analyze(min_confidence=min_confidence)

    if getattr(args, "json", False):
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print(format_dead_code_text(report, verbose=verbose))

    if getattr(args, "apply", False) or getattr(args, "dry_run", False):
        dry_run = getattr(args, "dry_run", False)
        target_confidence = min_confidence if min_confidence != "low" else "high"
        refactor_engine = RefactorEngine(workspace_root)
        plan = refactor_engine.create_dead_code_plan(report.zombies, min_confidence=target_confidence)

        if not plan.actions:
            print(f"\nℹ️  No safe symbols meeting confidence threshold '{target_confidence}' to prune.")
            return 0

        res = refactor_engine.apply_plan(plan, dry_run=dry_run)

        if dry_run:
            diffs = res.get("diffs", {})
            print(f"\n🔍 Dry Run Preview: {res['files_affected']} file(s) would be modified ({len(plan.actions)} symbols):")
            print(format_diffstat(diffs))

            if show_diff:
                print("\n📄 Full Unified Diffs:")
                for path, diff in diffs.items():
                    print(f"\n--- {path} ---")
                    print(diff)
            else:
                print("\n💡 Tip: Pass --diff to inspect full unified patch diffs.")

            print("\n💡 Next Steps:")
            print("   • Inspect full patch diffs:   agtoosa refactor dead-code --dry-run --diff")
            print("   • Target specific confidence: agtoosa refactor dead-code --min-confidence high --dry-run")
            print("   • Apply safe pruning:         agtoosa refactor dead-code --apply")
            print("   • Export machine JSON:        agtoosa refactor dead-code --json")
        else:
            if res.get("status") == "rolled_back_on_failure":
                print(f"\n❌ Refactoring Verification Failed: {res.get('error')}")
                print(f"🛡️  Automatic Rollback Triggered: All files restored to backup snapshot '{res.get('backup_id')}'.")
                print("   Your codebase was not modified and remains fully healthy.")
                return 1

            print(f"\n🚀 Pruned {len(plan.actions)} dead symbol(s) across {res['files_affected']} file(s)")
            print(f"   📦 Backup ID: {res['backup_id']}")
            print(f"   🔄 To rollback, run: agtoosa refactor rollback {res['backup_id']}")

    return 0



def cmd_refactor_rollback(args: Any, workspace_root: Path) -> int:
    """Roll back an applied refactoring using backup ID."""
    refactor_engine = RefactorEngine(workspace_root)
    success = refactor_engine.rollback(args.backup_id)
    if success:
        print(f"✅ Successfully rolled back refactoring snapshot '{args.backup_id}'. Original files restored.")
        return 0
    else:
        print(f"❌ Rollback failed: Backup snapshot '{args.backup_id}' not found.")
        return 1


def cmd_refactor_backups(args: Any, workspace_root: Path) -> int:
    """List available refactoring backups."""
    refactor_engine = RefactorEngine(workspace_root)
    backups = refactor_engine.list_backups()
    if not backups:
        print("ℹ️  No refactoring backup snapshots found.")
        return 0

    print(f"📦 Available Refactoring Backups ({len(backups)}):")
    for b in backups:
        print(f"   • {b['plan_id']} ({b.get('created_at', 'unknown date')})")
        print(f"     Description: {b.get('description', '')}")
        print(f"     Files ({len(b.get('files', []))}): {', '.join(f['path'] for f in b.get('files', []))}")
    return 0
