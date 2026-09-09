"""CLI command implementations for lifecycle commands (context compile, review, ship)."""

import sys
from pathlib import Path
from typing import Any

from agtoosa.graph.store import GraphStore
from agtoosa.cli.graph_cmd import get_default_db_path
from agtoosa.core.context_compiler import ContextCompiler
from agtoosa.core.lifecycle import LifecycleEngine


def cmd_context_compile(args: Any, workspace_root: Path) -> int:
    """Compile a high-signal, bounded context pack for an active task or story."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    compiler = ContextCompiler(store)

    radius = getattr(args, "radius", 2)
    pack = compiler.compile_context(args.target, radius=radius)

    if not pack:
        print(f"❌ Target '{args.target}' not found in knowledge graph.")
        return 1

    output_path = getattr(args, "output", None)
    if output_path:
        out_file = Path(output_path)
        out_file.write_text(pack, encoding="utf-8")
        print(f"✅ Context pack compiled to {out_file} ({out_file.stat().st_size} bytes)")
    else:
        print(pack)

    return 0


def cmd_lifecycle_review(args: Any, workspace_root: Path) -> int:
    """Review repository working tree against graph invariants."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    lifecycle = LifecycleEngine(store, workspace_root)
    res = lifecycle.review()

    print(f"🔍 Agtoosa2 Review Verdict: [{res['verdict']}]")
    print(f"   • Modified Files Checked: {len(res['modified_files'])}")

    if res["affected_stories"]:
        print("   • Directly Affected Stories:")
        for s in res["affected_stories"]:
            print(f"     - {s}")

    if res["findings"]:
        print("\n   ⚠️  Review Findings:")
        for f in res["findings"]:
            print(f"     - [{f['severity']}] {f['message']}")

    return 0 if res["verdict"] == "APPROVED" else 1


def cmd_lifecycle_ship(args: Any, workspace_root: Path) -> int:
    """Mathematically verify proof chain before shipping a story."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    lifecycle = LifecycleEngine(store, workspace_root)

    can_ship, reasons = lifecycle.verify_ship_proof(args.story)

    if can_ship:
        print(f"🚀 SHIP APPROVED: Story '{args.story}' proof graph is complete and verified!")
        print("   All acceptance criteria and assigned tasks have passed.")
        return 0
    else:
        print(f"🚫 SHIP BLOCKED: Story '{args.story}' cannot be shipped.")
        print("   Failure reasons:")
        for r in reasons:
            print(f"     - {r}")
        return 1
