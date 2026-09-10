"""CI/CD Quality Gate: Automated GitHub PR comment generation and architectural invariant enforcement."""

import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import urllib.error

from agtoosa.review.intelligence import DriftReport, DriftFinding, ReviewIntelligenceEngine
from agtoosa.graph.store import GraphStore

STICKY_COMMENT_MARKER = "<!-- agtoosa-architecture-gate-comment -->"


class PRCommentFormatter:
    """Formats a DriftReport into a polished, high-signal GitHub Flavored Markdown PR comment."""

    def __init__(self, report: DriftReport, workspace_root: Optional[Path] = None):
        self.report = report
        self.workspace_root = workspace_root

    def _get_verdict_badge(self) -> str:
        verdict = self.report.verdict
        if verdict == "APPROVED":
            return "![Verdict: APPROVED](https://img.shields.io/badge/Architecture_Gate-APPROVED-22c55e?style=for-the-badge&logo=checkmarx&logoColor=white)"
        elif verdict == "WARNING":
            return "![Verdict: WARNING](https://img.shields.io/badge/Architecture_Gate-WARNING-f59e0b?style=for-the-badge&logo=alert&logoColor=white)"
        else:
            return "![Verdict: BLOCKED](https://img.shields.io/badge/Architecture_Gate-BLOCKED-ef4444?style=for-the-badge&logo=shield&logoColor=white)"

    def _determine_recommended_tests(self) -> List[str]:
        """Infer targeted test suites based on modified files and impacted callers."""
        tests = set()
        paths = list(self.report.modified_files)

        if self.report.pr_diff_summary:
            for sym in self.report.pr_diff_summary.get("directly_modified_symbols", []):
                paths.append(sym.get("path", ""))

        for p in paths:
            norm = p.replace("\\", "/").lower()
            if "watcher" in norm:
                tests.add("pytest tests/test_watcher.py")
            if "review" in norm:
                tests.add("pytest tests/test_intelligence.py tests/test_ci_gate.py")
            if "cli" in norm:
                tests.add("pytest tests/test_cli.py")
            if "graph" in norm or "store" in norm or "metrics" in norm:
                tests.add("pytest tests/test_metrics.py tests/test_store.py tests/test_query.py")
            if "parser" in norm:
                tests.add("pytest tests/test_parser.py tests/test_polyglot.py")
            if "security" in norm:
                tests.add("pytest tests/test_security.py")
            if "visualizer" in norm:
                tests.add("pytest tests/test_visualizer.py")
            if "lifecycle" in norm or "context" in norm:
                tests.add("pytest tests/test_lifecycle.py")

        if not tests:
            tests.add("uv run pytest")
        return sorted(list(tests))

    def format_markdown(self, pr_number: Optional[int] = None) -> str:
        """Render complete GitHub Flavored Markdown comment body."""
        lines: List[str] = []

        # 1. Header & Verdict Badge
        lines.append("## 🏛️ Agtoosa Architecture Quality Gate")
        lines.append("")
        lines.append(self._get_verdict_badge())
        lines.append("")

        # 2. Executive Summary Metrics Table
        diff_info = self.report.pr_diff_summary or {}
        modified_syms = diff_info.get("directly_modified_symbols", [])
        high_risk_syms = diff_info.get("high_risk_symbols", [])
        error_findings = [f for f in self.report.findings if f.severity == "ERROR"]
        warning_findings = [f for f in self.report.findings if f.severity == "WARNING"]

        status_emoji = "✅ Passed" if self.report.verdict == "APPROVED" else ("⚠️ In Review" if self.report.verdict == "WARNING" else "🚫 Blocked")

        lines.append("| Metric | Result | CI Impact |")
        lines.append("|:---|:---:|:---|")
        lines.append(f"| **Gate Verdict** | `{self.report.verdict}` | {status_emoji} |")
        lines.append(f"| **Modified Files** | `{len(self.report.modified_files)}` | Scope of change |")
        lines.append(f"| **Directly Changed Symbols** | `{len(modified_syms)}` | Functions & classes touched |")
        lines.append(f"| **High-Risk Symbols (Callers ≥ 5)** | `{len(high_risk_syms)}` | Potential blast radius |")
        lines.append(f"| **Targeted Stories** | `{len(self.report.affected_stories)}` | Linked functional stories |")
        lines.append(f"| **Invariant Violations** | `{len(error_findings)} errors, {len(warning_findings)} warnings` | Clean architecture compliance |")
        lines.append("")

        # 3. Architectural Drift Alarms
        if self.report.findings:
            lines.append("### 🚨 Architectural Drift Alarms")
            lines.append("")
            for f in self.report.findings:
                if f.severity == "ERROR":
                    lines.append(f"> [!CAUTION]")
                    lines.append(f"> **Blocker: {f.category}** in `{f.symbol_or_path}`")
                    lines.append(f"> {f.message}")
                    lines.append("")
                else:
                    lines.append(f"> [!WARNING]")
                    lines.append(f"> **Warning: {f.category}** in `{f.symbol_or_path}`")
                    lines.append(f"> {f.message}")
                    lines.append("")
        else:
            lines.append("> [!NOTE]")
            lines.append("> ✨ **Clean Architectural Verification**: No circular dependencies, layer inversions, or unbounded blast radius detected.")
            lines.append("")

        # 4. Directly Modified Symbols & Upstream Blast Radius
        if modified_syms:
            lines.append("### 🔍 Modified Symbols & Upstream Blast Radius")
            lines.append("")
            lines.append("| Symbol | Type | Path | Blast Radius (Callers) | Top Upstream Callers |")
            lines.append("|:---|:---:|:---|:---:|:---|")
            for sym in modified_syms:
                callers = ", ".join(sym.get("top_dependents", [])) or "*(None)*"
                impact_count = sym.get("impacted_count", 0)
                risk_flag = " ⚠️" if impact_count >= 5 else ""
                lines.append(f"| `{sym['name']}` | `{sym['type']}` | `{sym['path']}` | **{impact_count}**{risk_flag} | {callers} |")
            lines.append("")

        # 5. Affected Stories
        if self.report.affected_stories:
            lines.append("### 🎯 Impacted User Stories")
            lines.append("")
            for story in self.report.affected_stories:
                lines.append(f"- 📌 **{story}**")
            lines.append("")

        # 6. Recommended Automated Verification Suites
        rec_tests = self._determine_recommended_tests()
        if rec_tests:
            lines.append("### 🧪 Recommended Test Suites")
            lines.append("")
            lines.append("Run the following verification suites before merging to prevent regressions:")
            lines.append("```bash")
            for t in rec_tests:
                lines.append(t)
            lines.append("```")
            lines.append("")

        # 7. Sticky Anchor & Footer
        lines.append(STICKY_COMMENT_MARKER)
        lines.append("---")
        lines.append("*Automated by [Agtoosa2 Architecture Gatekeeper](https://github.com/sky2464/Agtoosa2) v0.2.1-dev • Zero-dependency Graph Intelligence*")

        return "\n".join(lines)


def parse_pr_number_from_env() -> Optional[int]:
    """Detect PR number from GitHub Actions environment variables."""
    # Direct PR number
    pr_env = os.environ.get("PR_NUMBER")
    if pr_env and pr_env.isdigit():
        return int(pr_env)

    # From GITHUB_REF: refs/pull/123/merge or refs/pull/123/head
    gh_ref = os.environ.get("GITHUB_REF", "")
    m = re.match(r"^refs/pull/(\d+)/", gh_ref)
    if m:
        return int(m.group(1))

    # From GITHUB_EVENT_PATH (GitHub event JSON)
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and os.path.isfile(event_path):
        try:
            with open(event_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "pull_request" in data and "number" in data["pull_request"]:
                    return int(data["pull_request"]["number"])
                if "issue" in data and "number" in data["issue"]:
                    return int(data["issue"]["number"])
        except Exception:
            pass

    return None


def post_or_update_pr_comment(
    comment_md: str,
    repo: Optional[str] = None,
    pr_number: Optional[int] = None,
    token: Optional[str] = None,
    api_url: str = "https://api.github.com"
) -> bool:
    """Post or update sticky PR comment via GitHub REST API without third-party libraries."""
    token = token or os.environ.get("GITHUB_TOKEN")
    repo = repo or os.environ.get("GITHUB_REPOSITORY")
    pr_number = pr_number or parse_pr_number_from_env()

    # Step Summary output (native to GitHub Actions)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        try:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(f"\n{comment_md}\n")
        except Exception as e:
            print(f"⚠️  Failed to append to GITHUB_STEP_SUMMARY: {e}")

    if not token or not repo or not pr_number:
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Agtoosa-CI-Gate/0.2.1",
        "Content-Type": "application/json"
    }

    try:
        # 1. Search existing comments to find sticky marker
        list_url = f"{api_url}/repos/{repo}/issues/{pr_number}/comments"
        req = urllib.request.Request(list_url, headers=headers, method="GET")
        existing_comment_id = None

        with urllib.request.urlopen(req, timeout=15) as resp:
            comments = json.loads(resp.read().decode("utf-8"))
            for c in comments:
                if STICKY_COMMENT_MARKER in c.get("body", ""):
                    existing_comment_id = c.get("id")
                    break

        # 2. Update existing sticky comment or create new one
        payload = json.dumps({"body": comment_md}).encode("utf-8")

        if existing_comment_id:
            update_url = f"{api_url}/repos/{repo}/issues/comments/{existing_comment_id}"
            req = urllib.request.Request(update_url, data=payload, headers=headers, method="PATCH")
        else:
            create_url = f"{api_url}/repos/{repo}/issues/{pr_number}/comments"
            req = urllib.request.Request(create_url, data=payload, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 201)

    except urllib.error.HTTPError as e:
        print(f"⚠️  GitHub API returned HTTP {e.code}: {e.read().decode('utf-8')}")
        return False
    except Exception as e:
        print(f"⚠️  Error posting PR comment: {e}")
        return False


def run_ci_gate(
    store: GraphStore,
    workspace_root: Path,
    base_ref: str = "origin/main",
    strict: bool = False,
    output_comment_path: Optional[str] = None,
    post_comment: bool = False,
    token: Optional[str] = None,
    repo: Optional[str] = None,
    pr_number: Optional[int] = None
) -> Tuple[int, DriftReport, str]:
    """Orchestrates CI review, diff analysis, report formatting, and gate verdict."""
    engine = ReviewIntelligenceEngine(store, workspace_root)
    report = engine.review(diff_base=base_ref)

    formatter = PRCommentFormatter(report, workspace_root=workspace_root)
    comment_md = formatter.format_markdown(pr_number=pr_number)

    if output_comment_path:
        out_p = Path(output_comment_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(comment_md, encoding="utf-8")

    if post_comment:
        post_or_update_pr_comment(
            comment_md=comment_md,
            repo=repo,
            pr_number=pr_number,
            token=token
        )

    # Determine exit code
    if report.verdict == "BLOCKED":
        exit_code = 1
    elif report.verdict == "WARNING" and strict:
        exit_code = 1
    else:
        exit_code = 0

    return exit_code, report, comment_md
