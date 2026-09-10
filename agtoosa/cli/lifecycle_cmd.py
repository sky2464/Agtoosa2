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
    """Review repository working tree and PR diff against graph invariants with intelligence alarms."""
    import json
    from agtoosa.review.intelligence import ReviewIntelligenceEngine

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    engine = ReviewIntelligenceEngine(store, workspace_root)

    diff_base = getattr(args, "diff", None)
    report = engine.review(diff_base=diff_base)

    if getattr(args, "json", False):
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.verdict == "APPROVED" else 1

    verdict_icons = {"APPROVED": "✅", "WARNING": "⚠️", "BLOCKED": "🚫"}
    print(f"🔍 Agtoosa2 Architecture Review Verdict: {verdict_icons.get(report.verdict, '❓')} [{report.verdict}]")
    print(f"   • Modified Files Checked: {len(report.modified_files)}")

    if report.affected_stories:
        print(f"   • Directly Affected Stories ({len(report.affected_stories)}):")
        for s in report.affected_stories:
            print(f"     - 🎯 {s}")

    if report.pr_diff_summary:
        summary = report.pr_diff_summary
        print(f"\n   📋 Git PR Diff Analysis vs '{summary['base_ref']}':")
        print(f"     - Directly Modified Symbols: {len(summary['directly_modified_symbols'])}")
        for sym in summary["directly_modified_symbols"][:5]:
            print(f"       • {sym['type'].upper()} {sym['name']} ({sym['path']}) ➔ Impacts {sym['impacted_count']} callers")
        if summary["high_risk_symbols"]:
            print(f"     - ⚠️  HIGH RISK SYMBOLS (>= 5 dependents): {len(summary['high_risk_symbols'])}")

    if report.findings:
        print("\n   🚨 Architectural Drift Findings:")
        for f in report.findings:
            sev_icon = "❌" if f.severity == "ERROR" else "⚠️"
            print(f"     {sev_icon} [{f.category}] {f.message}")
    else:
        print("\n   ✨ Zero architectural drift detected! Layer boundaries and cycles clean.")

    is_strict = getattr(args, "strict", False)
    if report.verdict == "BLOCKED":
        return 1
    elif report.verdict == "WARNING" and is_strict:
        print("\n🚫 Review failed under --strict mode due to outstanding warnings.")
        return 1

    return 0


def cmd_review_remember(args: Any, workspace_root: Path) -> int:
    """Record an architectural decision or design invariant into project memory."""
    from agtoosa.review.memory import ArchitecturalMemory

    db_path = get_default_db_path(workspace_root)
    store = GraphStore(db_path)
    memory = ArchitecturalMemory(store)

    lesson = args.rule
    domain = getattr(args, "domain", None)
    tags = getattr(args, "tags", None)
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    node = memory.remember(lesson, domain=domain, tags=tag_list)
    print(f"🧠 Architectural Memory Stored:")
    print(f"   • Rule ID: {node.id}")
    print(f"   • Domain: {domain or 'global'}")
    print(f"   • Invariant: {lesson}")
    return 0


def cmd_review_reflect(args: Any, workspace_root: Path) -> int:
    """Retrieve and display stored architectural rules and institutional memory."""
    from agtoosa.review.memory import ArchitecturalMemory

    db_path = get_default_db_path(workspace_root)
    store = GraphStore(db_path)
    memory = ArchitecturalMemory(store)

    domain = getattr(args, "domain", None)
    rules = memory.reflect(domain=domain)

    filter_str = f" for domain '{domain}'" if domain else ""
    print(f"🧠 Institutional Architectural Memory ({len(rules)} rules){filter_str}:\n")

    if not rules:
        print("   No architectural rules recorded yet. Add one with 'agtoosa review remember \"<rule>\"'.")
        return 0

    for idx, r in enumerate(rules, start=1):
        domain_tag = f"[{r['domain']}] " if r.get("domain") else ""
        print(f"   {idx}. {domain_tag}⚠️  {r['rule']}")
        if r.get("tags"):
            print(f"      Tags: {', '.join(r['tags'])}")

    return 0


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


def cmd_ci_review(args: Any, workspace_root: Path) -> int:
    """Run automated CI architecture quality gate and generate PR markdown report."""
    from agtoosa.review.ci import run_ci_gate

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    base_ref = getattr(args, "base_ref", "origin/main")
    strict = getattr(args, "strict", False)
    output_comment = getattr(args, "output_comment", None)
    post_comment = getattr(args, "post_comment", False)
    token = getattr(args, "github_token", None)
    repo = getattr(args, "repo", None)
    pr_number = getattr(args, "pr_number", None)

    exit_code, report, comment_md = run_ci_gate(
        store=store,
        workspace_root=workspace_root,
        base_ref=base_ref,
        strict=strict,
        output_comment_path=output_comment,
        post_comment=post_comment,
        token=token,
        repo=repo,
        pr_number=pr_number
    )

    verdict_icons = {"APPROVED": "✅", "WARNING": "⚠️", "BLOCKED": "🚫"}
    print(f"🏛️  Agtoosa CI Quality Gate: {verdict_icons.get(report.verdict, '❓')} [{report.verdict}]")
    print(f"   • Base Git Ref: {base_ref}")
    print(f"   • Modified Files: {len(report.modified_files)}")
    print(f"   • Invariant Findings: {len(report.findings)}")

    if output_comment:
        print(f"   • PR Comment Written: {output_comment}")

    if report.verdict == "BLOCKED":
        print("\n🚫 CI Quality Gate failed: Critical architectural invariants violated.")
    elif report.verdict == "WARNING" and strict:
        print("\n🚫 CI Quality Gate failed: Warnings detected under --strict mode.")
    elif report.verdict == "APPROVED":
        print("\n✨ CI Quality Gate passed! Clean architectural invariants.")

    return exit_code


def cmd_ci_check(args: Any, workspace_root: Path) -> int:
    """Fast CI check returning exit code 0 on clean architecture, 1 on violation."""
    from agtoosa.review.ci import run_ci_gate

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        return 1

    store = GraphStore(db_path)
    base_ref = getattr(args, "base_ref", "origin/main")
    strict = getattr(args, "strict", False)

    exit_code, _, _ = run_ci_gate(
        store=store,
        workspace_root=workspace_root,
        base_ref=base_ref,
        strict=strict
    )
    return exit_code
