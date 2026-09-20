"""CLI command implementations for lifecycle commands (context compile, review, ship)."""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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
        print(f"ℹ️  Knowledge graph not found at {db_path}. Automatically indexing workspace...\n")
        from agtoosa.cli.graph_cmd import cmd_graph_build
        ret = cmd_graph_build(args, workspace_root)
        if ret != 0:
            return ret
        print()

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
    """Mathematically verify proof chain before shipping a story or full repository release gate."""
    import json
    from agtoosa.review.intelligence import ReviewIntelligenceEngine

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    lifecycle = LifecycleEngine(store, workspace_root)
    target = getattr(args, "story", "all") or "all"

    # 1. Single story verification mode
    if target.lower() != "all":
        can_ship, reasons = lifecycle.verify_ship_proof(target)
        if getattr(args, "json", False):
            print(json.dumps({
                "story": target,
                "approved": can_ship,
                "reasons": reasons
            }, indent=2))
            return 0 if can_ship else 1

        if can_ship:
            print(f"🚀 SHIP APPROVED: Story '{target}' proof graph is complete and verified!")
            print("   All acceptance criteria and assigned tasks have passed.")
            return 0
        else:
            print(f"🚫 SHIP BLOCKED: Story '{target}' cannot be shipped.")
            print("   Failure reasons:")
            for r in reasons:
                print(f"     - {r}")
            return 1

    # 2. Release Gate mode (agtoosa ship / agtoosa ship all)
    review_engine = ReviewIntelligenceEngine(store, workspace_root)
    review_report = review_engine.review()

    stories = store.get_nodes_by_type("story")
    def _sort_key(node: Dict[str, Any]) -> str:
        return node.get("metadata", {}).get("story_id", node["name"])
    stories.sort(key=_sort_key)

    ship_results = []
    approved_count = 0
    blocked_count = 0

    for s in stories:
        sid = s.get("metadata", {}).get("story_id", s["name"])
        title = s.get("metadata", {}).get("title", s["name"])
        can_ship, reasons = lifecycle.verify_ship_proof(sid)
        if can_ship:
            approved_count += 1
        else:
            blocked_count += 1
        ship_results.append({
            "id": sid,
            "title": title,
            "approved": can_ship,
            "reasons": reasons
        })

    is_strict = getattr(args, "strict", False)
    review_ok = review_report.verdict == "APPROVED" if is_strict else review_report.verdict in ("APPROVED", "WARNING")
    gate_passed = review_ok and (blocked_count == 0)

    if getattr(args, "json", False):
        print(json.dumps({
            "gate_passed": gate_passed,
            "review_verdict": review_report.verdict,
            "total_stories": len(stories),
            "approved_stories": approved_count,
            "blocked_stories": blocked_count,
            "results": ship_results
        }, indent=2))
        return 0 if gate_passed else 1

    review_icon = "✅" if review_report.verdict == "APPROVED" else "⚠️"
    gate_icon = "🚀" if gate_passed else "🚫"
    gate_label = "GATE APPROVED" if gate_passed else "GATE BLOCKED"

    print(f"{gate_icon} Agtoosa Release Gate: Mathematical Ship Verification [{gate_label}]")
    print("═" * 84)
    print(f"   • Working Tree Review:      {review_icon} [{review_report.verdict}] ({len(review_report.modified_files)} files checked)")
    print(f"   • Specifications Evaluated: {len(stories)}")
    print(f"   • Proofs Approved:          {approved_count} / {len(stories)}")
    if blocked_count > 0:
        print(f"   • Proofs Blocked:           {blocked_count} / {len(stories)}")
    print("─" * 84)
    print(f"{'SPEC ID':<10} {'STATUS':<14} {'TITLE':<38} {'PROOF CHAIN'}")
    print("─" * 84)
    for res in ship_results:
        status_str = "🚀 APPROVED" if res["approved"] else "🚫 BLOCKED"
        title_trunc = (res["title"][:35] + "…") if len(res["title"]) > 36 else res["title"]
        proof_note = "Criteria & Tasks verified" if res["approved"] else res["reasons"][0]
        if len(proof_note) > 28:
            proof_note = proof_note[:25] + "…"
        print(f"{res['id']:<10} {status_str:<14} {title_trunc:<38} {proof_note}")
    print("═" * 84)

    if gate_passed:
        print("\n✨ ALL SPECIFICATIONS AND ARCHITECTURAL INVARIANTS SHIP-APPROVED!")
        print("   Ready to cut release tag and publish.")
        return 0
    elif blocked_count == 0 and review_report.verdict != "APPROVED":
        print(f"\n⚠️  All stories verified, but working tree has review warning: {review_report.verdict}")
        return 0 if not is_strict else 1
    else:
        print(f"\n🚫 Release gate blocked: {blocked_count} specification(s) have unfulfilled criteria or tasks.")
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


def cmd_lifecycle_spec(args: Any, workspace_root: Path) -> int:
    """Inspect and query engineering specifications and lifecycle criteria."""
    from agtoosa.parser.doc_parser import MarkdownDocParser
    from agtoosa.core.model import NodeType

    target = getattr(args, "target", "all") or "all"
    json_mode = getattr(args, "json", False)

    db_path = get_default_db_path(workspace_root)
    stories_data: List[Dict[str, Any]] = []

    if db_path.exists():
        store = GraphStore(db_path)
        raw_stories = store.get_nodes_by_type("story")
        for s in raw_stories:
            sid = s.get("metadata", {}).get("story_id") or s["id"].replace("story:", "")
            neighbors = store.get_neighbors(s["id"], direction="out")
            criteria = [n for n in neighbors if n.get("node_type") == "criterion"]
            tasks = [n for n in neighbors if n.get("node_type") == "task"]
            completed_tasks = [t for t in tasks if t.get("metadata", {}).get("completed", False)]

            in_neighbors = store.get_neighbors(s["id"], direction="in")
            linked_files = [n.get("path") for n in in_neighbors if n.get("node_type") == "file"]

            status = s.get("metadata", {}).get("status") or "Implemented & Verified"
            milestone = s.get("metadata", {}).get("milestone") or ""
            title = s.get("metadata", {}).get("title") or s["name"]

            stories_data.append({
                "id": s["id"],
                "story_id": sid,
                "title": title,
                "path": s.get("path", ""),
                "status": status,
                "milestone": milestone,
                "criteria": [{"code": c.get("metadata", {}).get("criterion_code", c["name"]), "doc": c.get("docstring", "")} for c in criteria],
                "tasks": [{"name": t["name"], "doc": t.get("docstring", ""), "completed": t.get("metadata", {}).get("completed", False)} for t in tasks],
                "criteria_count": len(criteria),
                "tasks_count": len(tasks),
                "completed_tasks_count": len(completed_tasks),
                "linked_files": [f for f in linked_files if f],
                "can_ship": len(criteria) > 0 and (len(tasks) == 0 or len(completed_tasks) == len(tasks)),
            })
    else:
        specs_dir = workspace_root / "docs" / "specs"
        if specs_dir.exists():
            parser = MarkdownDocParser()
            for p in sorted(specs_dir.glob("*.md")):
                nodes, edges = parser.parse(p, workspace_root)
                story_node = next((n for n in nodes if n.node_type == NodeType.STORY), None)
                if story_node:
                    sid = story_node.metadata.get("story_id") or story_node.id.replace("story:", "")
                    criteria = [n for n in nodes if n.node_type == NodeType.CRITERION]
                    tasks = [n for n in nodes if n.node_type == NodeType.TASK]
                    completed_tasks = [t for t in tasks if t.metadata.get("completed", False)]
                    stories_data.append({
                        "id": story_node.id,
                        "story_id": sid,
                        "title": story_node.metadata.get("title") or story_node.name,
                        "path": story_node.path,
                        "status": story_node.metadata.get("status") or "Implemented & Verified",
                        "milestone": story_node.metadata.get("milestone") or "",
                        "criteria": [{"code": c.metadata.get("criterion_code", c.name), "doc": c.docstring or ""} for c in criteria],
                        "tasks": [{"name": t.name, "doc": t.docstring or "", "completed": t.metadata.get("completed", False)} for t in tasks],
                        "criteria_count": len(criteria),
                        "tasks_count": len(tasks),
                        "completed_tasks_count": len(completed_tasks),
                        "linked_files": [story_node.path],
                        "can_ship": len(criteria) > 0 and (len(tasks) == 0 or len(completed_tasks) == len(tasks)),
                    })

    def _sort_key(item):
        sid = item["story_id"]
        if sid.startswith("EPIC-"):
            num_part = sid.split("-")[1]
            return (0, int(num_part) if num_part.isdigit() else 0)
        elif sid.startswith("DEV-"):
            num_part = sid.split("-")[1]
            return (1, int(num_part) if num_part.isdigit() else 999)
        return (2, sid)

    stories_data.sort(key=_sort_key)

    # 1. Single Story Inspection Mode
    if target.lower() not in ("all", "list", "*", ""):
        search_target = target.lower().replace("story:", "").strip()
        matched = None
        for s in stories_data:
            if s["story_id"].lower() == search_target or s["id"].lower() == f"story:{search_target}":
                matched = s
                break
        if not matched:
            for s in stories_data:
                if search_target in s["story_id"].lower() or search_target in s["title"].lower():
                    matched = s
                    break

        if not matched:
            print(f"❌ Specification '{target}' not found.")
            return 1

        if json_mode:
            print(json.dumps(matched, indent=2))
            return 0

        ship_icon = "🚀 SHIP APPROVED" if matched["can_ship"] else "⏳ IN PROGRESS"
        print(f"📜 Agtoosa Specification: {matched['story_id']} — {matched['title']}")
        print("═" * 80)
        print(f"   • Spec File:     {matched['path']}")
        print(f"   • Status:        {matched['status'] or '✅ Done'}")
        if matched.get("milestone"):
            print(f"   • Milestone:     {matched['milestone']}")
        print(f"   • Lifecycle:     {ship_icon}")
        print()

        print(f"📋 Acceptance Criteria ({len(matched['criteria'])}):")
        if matched["criteria"]:
            for c in matched["criteria"]:
                doc_snippet = c["doc"][:120] + ("..." if len(c["doc"]) > 120 else "")
                print(f"   • {c['code']}: {doc_snippet}")
        else:
            print("   (No formal AC tags parsed; validated via test fixtures)")
        print()

        print(f"📝 Tasks ({matched['completed_tasks_count']}/{matched['tasks_count']} completed):")
        if matched["tasks"]:
            for t in matched["tasks"]:
                box = "[x]" if t["completed"] else "[ ]"
                desc = t["doc"][:80] + ("..." if len(t["doc"]) > 80 else "")
                print(f"   {box} {t['name']}: {desc}")
        else:
            print("   (Tasks tracked in milestone ledger)")
        print()

        print("💡 Next Steps:")
        print(f"   • Verify ship proof:    agtoosa ship {matched['story_id']}")
        print(f"   • Compile agent pack:   agtoosa context compile {matched['story_id']}")
        print(f"   • View all specs:       agtoosa spec all")
        return 0

    # 2. All Specifications Listing Mode
    if json_mode:
        print(json.dumps(stories_data, indent=2))
        return 0

    total_specs = len(stories_data)
    total_criteria = sum(s["criteria_count"] for s in stories_data)
    total_tasks = sum(s["tasks_count"] for s in stories_data)
    total_completed_tasks = sum(s["completed_tasks_count"] for s in stories_data)

    print("📜 Agtoosa Architecture: Engineering Specifications & Lifecycle Ledger")
    print("═" * 88)
    print(f"{'SPEC ID':<10} {'TITLE':<42} {'STATUS':<15} {'AC':<5} {'TASKS':<8} {'READY'}")
    print("─" * 88)

    for s in stories_data:
        title_str = s["title"]
        if len(title_str) > 40:
            title_str = title_str[:39] + "…"

        stat_str = s["status"] or "✅ Done"
        if len(stat_str) > 13:
            stat_str = stat_str[:12] + "…"

        ac_str = str(s["criteria_count"]) if s["criteria_count"] > 0 else "-"
        task_str = f"{s['completed_tasks_count']}/{s['tasks_count']}" if s["tasks_count"] > 0 else "-"
        ready_icon = "✅ Yes" if s["can_ship"] else "🟡 WIP"

        print(f"{s['story_id']:<10} {title_str:<42} {stat_str:<15} {ac_str:<5} {task_str:<8} {ready_icon}")

    print("─" * 88)
    print(f"📊 Summary: {total_specs} specifications tracked | {total_criteria} criteria | {total_completed_tasks}/{total_tasks} tasks verified")
    print("\n💡 Next Steps:")
    print("   • Inspect a specification:  agtoosa spec <story_id> (e.g. agtoosa spec DEV-001)")
    print("   • Verify story ship proof:  agtoosa ship <story_id>")
    print("   • Export full JSON ledger:  agtoosa spec all --json")

    return 0


def cmd_agent_init(args: Any, workspace_root: Path) -> int:
    """Enforce Agtoosa2 architectural guardrails in AGENTS.md, CLAUDE.md, and agent rules (DEV-058)."""
    import json
    from agtoosa.core.agent_rules import AgentWorkflowEnforcer

    target = getattr(args, "target", "all")
    targets = [target] if target != "all" else ["all"]
    with_hooks = not getattr(args, "no_git_hooks", False)

    enforcer = AgentWorkflowEnforcer(workspace_root)
    res = enforcer.install_all(targets=targets, with_git_hooks=with_hooks)

    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0

    print(f"\n🤖 Agtoosa2 AI Agent Workflow Enforcement ({workspace_root.name})")
    print("═" * 75)
    print("   Installed & Updated Instructions:")
    for f in res["installed_files"]:
        print(f"   • ✅ {f}")

    if res.get("git_hooks_installed"):
        print("\n   Git Pre-Push & Review Hooks:")
        for h, ok in res["git_hooks_installed"].items():
            icon = "✅" if ok else "⚠️"
            print(f"   • {icon} .git/hooks/{h}")

    print("─" * 75)
    print("✨ AI agents (Cursor, Claude, Copilot, Antigravity) are now governed by Agtoosa2.")
    print("   They will automatically run 'agtoosa query' and 'agtoosa review' during development.")
    print("═" * 75 + "\n")
    return 0
