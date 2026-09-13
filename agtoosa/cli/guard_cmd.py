"""CLI command handler for agtoosa guard (DEV-024 / Stage 24)."""

import json
from pathlib import Path
import sys
import time
from typing import Any

from agtoosa.cli.graph_cmd import get_default_db_path
from agtoosa.graph.store import GraphStore
from agtoosa.review.guard import ArchitecturalGuard, GuardReport
from agtoosa.watcher.hooks import install_git_hooks, remove_git_hooks, get_git_hooks_status


def cmd_guard(args: Any, workspace_root: Path) -> int:
    """Execute pre-push architectural guard, background daemon, or Git hook operations."""
    # 1. Hook Installation / Uninstallation
    if getattr(args, "install_hooks", False):
        res = install_git_hooks(workspace_root)
        if not res:
            print("❌ .git repository not found in workspace.")
            return 1
        print("🪝 Agtoosa Git Hooks Installed:")
        for hook, ok in res.items():
            icon = "✅" if ok else "❌"
            print(f"   {icon} {hook}")
        return 0

    if getattr(args, "uninstall_hooks", False):
        res = remove_git_hooks(workspace_root)
        print("🪝 Agtoosa Git Hooks Removed:")
        for hook, ok in res.items():
            icon = "🗑️" if ok else "⚠️"
            print(f"   {icon} {hook}")
        return 0

    # 2. Status Cache Query
    db_path = get_default_db_path(workspace_root)
    store = GraphStore(db_path)
    guard = ArchitecturalGuard(store, workspace_root)

    if getattr(args, "status", False):
        cached = guard.read_status_cache()
        if not cached:
            if getattr(args, "json", False):
                print(json.dumps({"status": "no_cache", "message": "No guard cache found."}, indent=2))
            else:
                print("ℹ️ No cached guard status found. Run 'agtoosa guard' or 'agtoosa guard --daemon'.")
            return 0

        if getattr(args, "json", False):
            print(json.dumps(cached, indent=2))
            return 0 if cached.get("verdict") != "BLOCKED" else 1

        verdict = cached.get("verdict", "UNKNOWN")
        v_icon = "✅" if verdict == "PASSED" else ("⚠️" if verdict == "WARNING" else "🛑")
        print(f"🛡️  Agtoosa Architectural Guard Status (Cached): {v_icon} {verdict}")
        print(f"   • Timestamp: {cached.get('timestamp')}")
        print(f"   • Duration:  {cached.get('duration_ms')} ms")
        stats = cached.get("stats", {})
        print(f"   • Invariant Stats: {stats.get('cycles', 0)} cycles, {stats.get('layer_violations', 0)} layer breaches, {stats.get('blast_radius_violations', 0)} blast radius warnings, {stats.get('boundary_leaks', 0)} boundary leaks")

        findings = cached.get("findings", [])
        if findings:
            print("\n   🚨 Findings:")
            for f in findings:
                sev = "❌" if f.get("severity") == "ERROR" else "⚠️"
                print(f"     {sev} [{f.get('category')}] {f.get('message')}")
                if f.get("remediation"):
                    print(f"        💡 {f.get('remediation')}")
        return 0 if verdict != "BLOCKED" else 1

    # 3. Daemon Mode
    max_blast = getattr(args, "max_blast_radius", 5)
    is_strict = getattr(args, "strict", False)

    if getattr(args, "daemon", False):
        interval = getattr(args, "interval", 3.0)
        print(f"🛡️  Agtoosa Architectural Guard Daemon Active")
        print(f"   • Workspace:           {workspace_root}")
        print(f"   • Polling Interval:    {interval}s")
        print(f"   • Max Blast Radius:    {max_blast}")
        print(f"   • Strict Mode:         {'Enabled' if is_strict else 'Disabled'}")
        print(f"   • Cache Location:      .agtoosa/guard_status.json")
        print("   • Press Ctrl+C to stop.\n")

        def on_daemon_tick(rep: GuardReport):
            ts = time.strftime("%H:%M:%S")
            icon = "✅" if rep.verdict == "PASSED" else ("⚠️" if rep.verdict == "WARNING" else "🛑")
            print(f"[{ts}] {icon} Guard Verdict: {rep.verdict} ({rep.duration_ms}ms) | {rep.stats['cycles']} cycles, {rep.stats['layer_violations']} layer breaches, {rep.stats['blast_radius_violations']} blast alerts")

        try:
            guard.run_daemon(
                interval=interval,
                max_blast_radius=max_blast,
                strict=is_strict,
                on_tick=on_daemon_tick
            )
        except KeyboardInterrupt:
            print("\n🛑 Guard daemon stopped.")
        return 0

    # 4. Direct Audit
    base_ref = getattr(args, "base_ref", None)
    report = guard.audit(base_ref=base_ref, max_blast_radius=max_blast, strict=is_strict)

    if getattr(args, "json", False):
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.verdict != "BLOCKED" else 1

    # Human-formatted terminal output
    v_icon = "✅" if report.verdict == "PASSED" else ("⚠️" if report.verdict == "WARNING" else "🛑")
    print(f"🛡️  Agtoosa Architectural Guard: {v_icon} {report.verdict} ({report.duration_ms} ms)")
    if report.modified_files:
        print(f"   • Evaluated {len(report.modified_files)} modified file(s)")
    print(f"   • Invariants: {report.stats['cycles']} cycles, {report.stats['layer_violations']} layer breaches, {report.stats['blast_radius_violations']} blast alerts, {report.stats['boundary_leaks']} boundary leaks")

    if report.findings:
        print("\n   🚨 Findings:")
        for f in report.findings:
            sev = "❌" if f.severity == "ERROR" else "⚠️"
            print(f"     {sev} [{f.category}] {f.message}")
            if f.remediation:
                print(f"        💡 {f.remediation}")

    if report.verdict == "BLOCKED":
        print("\n🚫 Push/Commit Blocked: Resolve architectural violations or use 'agtoosa refactor decouple'.")
        return 1
    elif report.verdict == "WARNING" and is_strict:
        print("\n🚫 Guard check failed under --strict mode due to warnings.")
        return 1

    if report.verdict == "PASSED":
        print("\n✨ All architectural invariants satisfied. Safe to push!")

    return 0
