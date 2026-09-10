"""CLI commands for autonomous architecture refactoring (DEV-019 & DEV-020)."""

import json
from pathlib import Path
from typing import Any

from agtoosa.graph.store import GraphStore
from agtoosa.cli.graph_cmd import get_default_db_path
from agtoosa.refactor.decoupler import CycleDecouplerEngine


def cmd_refactor_decouple(args: Any, workspace_root: Path) -> int:
    """Analyze cyclic dependencies and generate architectural decoupling blueprints."""
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

    return 0
