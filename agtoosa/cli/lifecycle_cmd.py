"""CLI command implementations for lifecycle commands (context compile, review, ship)."""

import json
import os
import re
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
    hybrid = getattr(args, "hybrid", False)
    pack = compiler.compile_context(args.target, radius=radius, hybrid=hybrid)

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


def cmd_review_boundaries(args: Any, workspace_root: Path) -> int:
    """Validate monorepo package boundaries, encapsulation, and dependency rules."""
    from agtoosa.review.monorepo import MonorepoBoundaryEngine

    target_path = Path(getattr(args, "path", "."))
    if not target_path.is_absolute():
        target_path = (workspace_root / target_path).resolve()

    db_path = get_default_db_path(target_path)
    store = GraphStore(db_path) if db_path.exists() else None

    engine = MonorepoBoundaryEngine(target_path, store=store)
    report = engine.check_boundaries(strict=getattr(args, "strict", False))

    if getattr(args, "json", False):
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.passed else 1

    print(f"📦 Monorepo Package Boundary Review:")
    print(f"   • Workspace Root: {target_path}")
    print(f"   • Monorepo Detected: {'Yes' if report.is_monorepo else 'No'}")
    print(f"   • Packages Discovered: {len(report.packages)}")

    for pkg in report.packages:
        manifest_str = f" ({pkg['manifest_type']})" if pkg.get("manifest_type") else ""
        print(f"     - 📦 {pkg['name']}{manifest_str} ➔ {pkg['path']}")

    if report.package_dependencies:
        print(f"\n   🔗 Inter-Package Dependencies ({len(report.package_dependencies)}):")
        for dep in report.package_dependencies:
            print(f"     • {dep['from']} ➔ {dep['to']}")

    if report.cycles:
        print(f"\n   🚨 Package Cycles Detected ({len(report.cycles)}):")
        for c in report.cycles:
            print(f"     ❌ {' ➔ '.join(c)}")

    if report.violations:
        print(f"\n   🚨 Boundary Violations ({len(report.violations)}):")
        for v in report.violations:
            sev_icon = "❌" if v.severity == "ERROR" else "⚠️"
            print(f"     {sev_icon} [{v.rule}] {v.message}")
            print(f"        Remediation: {v.remediation}")
    else:
        print("\n   ✨ All package encapsulation boundaries and dependency rules respected!")

    verdict_icon = "✅ PASSED" if report.passed else "🚫 FAILED"
    print(f"\nVerdict: {verdict_icon}")
    return 0 if report.passed else 1


def cmd_ci_pr_bot(args: Any, workspace_root: Path) -> int:
    """Run PR Blast Radius & Breaking Schema Review Bot."""
    from agtoosa.review.pr_bot import PRReviewEngine, PRBotCommentFormatter, post_or_update_pr_comment

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    base_ref = getattr(args, "base", "origin/main") or "origin/main"
    engine = PRReviewEngine(store, workspace_root)
    analysis = engine.analyze(base_ref=base_ref)

    formatter = PRBotCommentFormatter(analysis)
    markdown_comment = formatter.format_markdown(pr_number=getattr(args, "pr", None))

    output_path = getattr(args, "output", None)
    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(markdown_comment, encoding="utf-8")

    if getattr(args, "json", False):
        print(json.dumps(analysis, indent=2))
    elif not output_path:
        print(markdown_comment)

    # Post comment if requested
    if getattr(args, "post_comment", False):
        token = os.environ.get("GITHUB_TOKEN")
        repo = os.environ.get("GITHUB_REPOSITORY")
        pr_number = getattr(args, "pr", None)

        if not pr_number and os.environ.get("GITHUB_REF"):
            m = re.match(r"refs/pull/(\d+)/", os.environ["GITHUB_REF"])
            if m:
                pr_number = int(m.group(1))

        if token and repo and pr_number:
            try:
                post_or_update_pr_comment(repo, int(pr_number), markdown_comment, token)
                print(f"✅ Sticky PR comment posted/updated on {repo}#{pr_number}")
            except Exception as e:
                print(f"⚠️ Failed to post PR comment: {e}")
        else:
            print("⚠️ Skipping comment posting: Missing GITHUB_TOKEN, GITHUB_REPOSITORY, or PR number.")

    verdict = analysis.get("verdict", "APPROVED")
    tier = analysis.get("production_risk_tier", "P4_DORMANT")

    if getattr(args, "fail_on_p0", False) and tier == "P0_CRITICAL":
        print(f"\n🚫 CI Gate Failed: P0_CRITICAL production traffic impacted under --fail-on-p0.")
        return 1

    if getattr(args, "strict", False) and verdict in ("BLOCKED", "WARNING"):
        print(f"\n🚫 CI Gate Failed: {verdict} status under --strict mode.")
        return 1

    return 1 if verdict == "BLOCKED" else 0


def cmd_ci_repair(args: Any, workspace_root: Path) -> int:
    """Autonomous AI repair agent diagnosing and healing architectural violations in CI."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️ Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    from agtoosa.repair.agent import PRAgentRepairEngine

    engine = PRAgentRepairEngine(store, workspace_root)
    base_ref = getattr(args, "base", None)
    apply_mode = getattr(args, "apply", False)
    dry_run = getattr(args, "dry_run", not apply_mode)
    branch_name = getattr(args, "branch", None)

    issues = engine.diagnose(base_ref=base_ref)

    if not issues:
        if getattr(args, "json", False):
            print(json.dumps({"status": "clean", "issues_count": 0, "repairs": []}, indent=2))
            return 0
        print("✅ No architectural violations or drift detected. Workspace is clean.")
        return 0

    results = []
    print(f"🩺 Diagnosed {len(issues)} Architectural Violation(s):\n")

    for idx, issue in enumerate(issues, 1):
        print(f"   [{idx}/{len(issues)}] {issue.severity}: {issue.description}")
        print(f"       Suggested Strategy: {issue.suggested_action}")

        plan = engine.synthesize_repair(issue)
        if not plan:
            print("       ⚠️ Autonomous patch synthesis not supported for this issue type.\n")
            results.append({"issue": issue.to_dict(), "synthesized": False})
            continue

        print(f"       Plan ID: {plan.plan_id}")
        print(f"       Files to modify: {', '.join(plan.files_modified)}")

        if dry_run:
            print("       Mode: DRY-RUN (Preview Diff):\n")
            for line in plan.diff.splitlines()[:15]:
                print(f"         {line}")
            if len(plan.diff.splitlines()) > 15:
                print(f"         ... ({len(plan.diff.splitlines()) - 15} more diff lines)")
            print()
            results.append({
                "issue": issue.to_dict(),
                "plan": plan.to_dict(),
                "applied": False,
                "dry_run": True
            })
        else:
            print("       Applying patch and verifying architectural invariants...")
            apply_res = engine.apply_and_verify(plan, dry_run=False)
            if apply_res["success"]:
                print(f"       ✅ Patch applied & verified! (Backup ID: {apply_res['backup_id']})")
                if branch_name:
                    commit_res = engine.create_git_commit(plan, branch_name=branch_name)
                    if commit_res["success"]:
                        print(f"       🌿 Committed to branch '{commit_res['branch']}': {commit_res['commit_hash']}")
                    else:
                        print(f"       ⚠️ Git commit failed: {commit_res.get('error')}")
                print()
            else:
                print(f"       ❌ Verification failed! Atomic rollback executed: {apply_res.get('reason')}\n")

            results.append({
                "issue": issue.to_dict(),
                "plan": plan.to_dict(),
                "result": apply_res
            })

    if getattr(args, "json", False):
        print(json.dumps({
            "status": "repaired" if apply_mode else "dry_run",
            "total_issues": len(issues),
            "results": results
        }, indent=2))

    return 0


def cmd_ci_benchmark(args: Any, workspace_root: Path) -> int:
    """Run automated CI continuous performance regression benchmark against baseline."""
    from agtoosa.benchmark.harness import BenchmarkHarness
    from agtoosa.benchmark.analyzer import RegressionAnalyzer
    from agtoosa.benchmark.baseline import BenchmarkBaselineStore

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️ Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    base_ref = getattr(args, "base", None)
    threshold_pct = float(getattr(args, "threshold", 10.0))
    strict = getattr(args, "strict", False)
    save_baseline = getattr(args, "save_baseline", False)
    output_path = getattr(args, "output", None)
    json_mode = getattr(args, "json", False)

    harness = BenchmarkHarness(store, workspace_root)
    baseline_store = BenchmarkBaselineStore(workspace_root)
    analyzer = RegressionAnalyzer(store, workspace_root, baseline_store)

    targets = harness.discover_targets(base_ref=base_ref)
    if not json_mode:
        print(f"⚡ Discovered {len(targets)} benchmarkable symbol(s)")

    results = []
    for t in targets:
        res = harness.run_benchmark(t, iterations=50, warmup=5)
        results.append(res)

    report = analyzer.analyze(results, threshold_pct=threshold_pct)

    if save_baseline and results:
        baseline_store.save_baseline(results, tag="ci")
        if not json_mode:
            print("💾 Performance baseline saved to .agtoosa/benchmarks/baseline.json")

    if output_path:
        Path(output_path).write_text(report.to_markdown(), encoding="utf-8")
        if not json_mode:
            print(f"📝 Benchmark report written to {output_path}")

    if json_mode:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print("\n" + report.to_markdown())

    if report.verdict == "REGRESSION_DETECTED" and strict:
        return 1
    return 0


def cmd_benchmark_run(args: Any, workspace_root: Path) -> int:
    """Run micro-benchmarks on specified target symbol or path."""
    from agtoosa.benchmark.harness import BenchmarkHarness
    from agtoosa.benchmark.analyzer import RegressionAnalyzer
    from agtoosa.benchmark.baseline import BenchmarkBaselineStore

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️ Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    target = getattr(args, "target", None)
    iterations = int(getattr(args, "iterations", 100))
    threshold_pct = float(getattr(args, "threshold", 10.0))
    save_baseline = getattr(args, "save_baseline", False)
    json_mode = getattr(args, "json", False)

    harness = BenchmarkHarness(store, workspace_root)
    baseline_store = BenchmarkBaselineStore(workspace_root)
    analyzer = RegressionAnalyzer(store, workspace_root, baseline_store)

    targets = harness.discover_targets(target_path_or_symbol=target)
    if not targets:
        print(f"⚠️ No benchmark targets matching '{target or 'all'}' found.")
        return 1

    results = []
    for t in targets:
        res = harness.run_benchmark(t, iterations=iterations, warmup=10)
        results.append(res)

    report = analyzer.analyze(results, threshold_pct=threshold_pct)

    if save_baseline and results:
        baseline_store.save_baseline(results)
        if not json_mode:
            print("💾 Performance baseline snapshot updated.")

    if json_mode:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print("\n" + report.to_markdown())

    return 0


def cmd_benchmark_snapshot(args: Any, workspace_root: Path) -> int:
    """Capture and persist current performance baseline snapshot."""
    from agtoosa.benchmark.harness import BenchmarkHarness
    from agtoosa.benchmark.baseline import BenchmarkBaselineStore

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️ Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    name = getattr(args, "name", "latest")
    json_mode = getattr(args, "json", False)

    harness = BenchmarkHarness(store, workspace_root)
    baseline_store = BenchmarkBaselineStore(workspace_root)

    targets = harness.discover_targets()
    results = []
    for t in targets:
        res = harness.run_benchmark(t, iterations=50, warmup=5)
        results.append(res)

    path = baseline_store.save_baseline(results, tag=name)

    if json_mode:
        print(json.dumps({
            "status": "snapshot_created",
            "tag": name,
            "symbols_count": len(results),
            "file": str(path)
        }, indent=2))
    else:
        print(f"📸 Baseline snapshot '{name}' created with {len(results)} symbols at {path}")

    return 0




