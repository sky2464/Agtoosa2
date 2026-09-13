"""PR Blast Radius & Breaking Schema Review Bot (DEV-029).

Analyzes pull request git diffs against the Agtoosa knowledge graph to compute:
1. Upstream Caller Blast Radius (transitive depth, counts, risk tier)
2. HTTP API Route Contract Impact (FastAPI, Flask, Express, NestJS)
3. Async Message Queue & Event Bus Lineage Impact (Kafka, RabbitMQ, Redis, Celery, BullMQ)
4. Production Runtime Traffic Risk Tiering (P0_CRITICAL to P4_DORMANT)
5. Architectural Invariant Drift Alarms (layer violations, circular dependencies)

Generates polished GitHub Flavored Markdown and automates sticky PR commenting.
Zero third-party dependencies — uses standard library urllib.request and subprocess.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional, Set, Tuple
import urllib.request
import urllib.error

from agtoosa.core.model import NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.query import query_routes, query_events, compute_impact
from agtoosa.review.intelligence import ReviewIntelligenceEngine, DriftReport, DriftFinding

STICKY_PR_BOT_MARKER = "<!-- agtoosa-pr-bot-comment -->"


class PRReviewEngine:
    """Computes multi-dimensional blast radius and contract risk for a pull request."""

    def __init__(self, store: GraphStore, workspace_root: Path):
        self.store = store
        self.workspace_root = workspace_root
        self.intelligence = ReviewIntelligenceEngine(store, workspace_root)

    def get_git_diff_ranges(self, base_ref: str = "origin/main") -> Dict[str, List[Tuple[int, int]]]:
        """Extract modified files and line ranges from git diff."""
        # Try base_ref...HEAD first; fall back to base_ref or HEAD~1
        diff_output = ""
        for ref_spec in [f"{base_ref}...HEAD", base_ref, "HEAD~1"]:
            try:
                res = subprocess.run(
                    ["git", "diff", "-U0", ref_spec],
                    cwd=str(self.workspace_root),
                    capture_output=True,
                    text=True
                )
                if res.returncode == 0 and res.stdout.strip():
                    diff_output = res.stdout
                    break
            except Exception:
                continue

        if not diff_output:
            return {}

        file_ranges: Dict[str, List[Tuple[int, int]]] = {}
        current_file: Optional[str] = None
        hunk_re = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

        for line in diff_output.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                if current_file and current_file != "/dev/null":
                    file_ranges.setdefault(current_file, [])
            elif line.startswith("@@ ") and current_file:
                m = hunk_re.match(line)
                if m:
                    start_line = int(m.group(2))
                    count = int(m.group(3)) if m.group(3) else 1
                    end_line = start_line + max(1, count) - 1
                    file_ranges[current_file].append((start_line, end_line))

        return file_ranges

    def analyze(self, base_ref: str = "origin/main", diff_ranges: Optional[Dict[str, List[Tuple[int, int]]]] = None) -> Dict[str, Any]:
        """Perform comprehensive multi-dimensional PR risk and blast radius analysis."""
        if diff_ranges is None:
            diff_ranges = self.get_git_diff_ranges(base_ref)

        modified_files = sorted(list(diff_ranges.keys()))
        all_nodes = self.store.get_all_nodes()
        all_telemetry = self.store.get_all_telemetry()

        # 1. Map modified lines to graph symbols
        directly_modified_symbols: List[Dict[str, Any]] = []
        modified_symbol_ids: Set[str] = set()

        for file_path, ranges in diff_ranges.items():
            matching_nodes = [
                n for n in all_nodes
                if n.get("path") == file_path and n.get("node_type") in ("function", "class", "variable")
            ]
            for n in matching_nodes:
                s_start = n.get("start_line", 1) or 1
                s_end = n.get("end_line", s_start) or s_start
                # Check overlap with any modified hunk
                overlaps = any(not (s_end < r_start or s_start > r_end) for r_start, r_end in ranges)
                if overlaps and n["id"] not in modified_symbol_ids:
                    modified_symbol_ids.add(n["id"])
                    impact_data = compute_impact(self.store, n["id"], max_depth=3) or {}
                    impacted_list = impact_data.get("impacted", [])
                    direct_callers = [i for i in impacted_list if i.get("depth") == 1]
                    caller_count = len(direct_callers)
                    impacted_count = impact_data.get("impacted_count", len(impacted_list))
                    top_dependents = [i.get("name", i.get("id")) for i in impacted_list[:5]]

                    directly_modified_symbols.append({
                        "id": n["id"],
                        "name": n["name"],
                        "type": n["node_type"],
                        "path": n["path"],
                        "start_line": n.get("start_line"),
                        "end_line": n.get("end_line"),
                        "caller_count": caller_count,
                        "impacted_count": impacted_count,
                        "top_dependents": top_dependents,
                        "risk": "CRITICAL" if impacted_count >= 15 else (
                            "HIGH" if impacted_count >= 5 else "MODERATE"
                        )
                    })

        # 2. Check HTTP API Route Contract Impact (DEV-025)
        routes = query_routes(self.store)
        impacted_routes: List[Dict[str, Any]] = []
        for r in routes:
            handler = r.get("handler")
            handler_id = handler["id"] if handler else None
            injected_deps = [d.get("target_id") for d in r.get("injected_dependencies", [])]

            # Direct handler modified or injected dependency modified
            is_handler_touched = handler_id in modified_symbol_ids
            touched_deps = [d for d in injected_deps if d in modified_symbol_ids]

            if is_handler_touched or touched_deps:
                impacted_routes.append({
                    "id": r["id"],
                    "http_method": r["http_method"],
                    "path": r["path"],
                    "framework": r["framework"],
                    "file_path": r["file_path"],
                    "start_line": r.get("start_line"),
                    "handler_name": handler["name"] if handler else "unknown",
                    "reason": "Handler modified" if is_handler_touched else f"Dependency touched ({len(touched_deps)})"
                })

        # 3. Check Message Queue & Event Bus Lineage Impact (DEV-026)
        events_data = query_events(self.store)
        impacted_topics: List[Dict[str, Any]] = []
        for t in events_data.get("topics", []):
            pub_ids = {p["id"] for p in t.get("publishers", [])}
            sub_ids = {s["id"] for s in t.get("subscribers", [])}

            touched_pubs = pub_ids.intersection(modified_symbol_ids)
            touched_subs = sub_ids.intersection(modified_symbol_ids)

            if touched_pubs or touched_subs:
                impacted_topics.append({
                    "id": t["id"],
                    "name": t["name"],
                    "broker": t["broker"],
                    "path": t["path"],
                    "publishers_count": len(t.get("publishers", [])),
                    "subscribers_count": len(t.get("subscribers", [])),
                    "is_orphan": t.get("is_orphan", False),
                    "orphan_reason": t.get("orphan_reason"),
                    "touched_publishers": list(touched_pubs),
                    "touched_subscribers": list(touched_subs)
                })

        # 4. Production Runtime Telemetry & Risk Tiering (DEV-018)
        total_traffic_at_risk = 0
        max_error_rate = 0.0
        p0_symbols: List[str] = []

        for sym in directly_modified_symbols:
            t = all_telemetry.get(sym["id"], {})
            calls = t.get("call_count", 0)
            err_rate = t.get("error_rate", 0.0)
            total_traffic_at_risk += calls
            if err_rate > max_error_rate:
                max_error_rate = err_rate
            if calls >= 10000 or (calls >= 100 and err_rate >= 0.15):
                p0_symbols.append(sym["name"])

        if total_traffic_at_risk >= 10000 or len(p0_symbols) > 0:
            production_risk_tier = "P0_CRITICAL"
        elif total_traffic_at_risk >= 1000:
            production_risk_tier = "P1_HIGH"
        elif total_traffic_at_risk >= 100:
            production_risk_tier = "P2_MODERATE"
        elif total_traffic_at_risk > 0:
            production_risk_tier = "P3_LOW"
        else:
            production_risk_tier = "P4_DORMANT"

        # 5. Architectural Invariant Drift Alarms
        drift_report = self.intelligence.review()
        findings = drift_report.findings

        # 6. Overall Verdict
        has_blocker = any(f.severity == "ERROR" for f in findings) or (
            production_risk_tier == "P0_CRITICAL" and max_error_rate >= 0.10
        )
        has_warning = (
            any(f.severity == "WARNING" for f in findings)
            or production_risk_tier in ("P0_CRITICAL", "P1_HIGH")
            or any(sym["risk"] == "CRITICAL" for sym in directly_modified_symbols)
        )

        if has_blocker:
            verdict = "BLOCKED"
        elif has_warning:
            verdict = "WARNING"
        else:
            verdict = "APPROVED"

        return {
            "verdict": verdict,
            "production_risk_tier": production_risk_tier,
            "total_traffic_at_risk": total_traffic_at_risk,
            "max_error_rate": round(max_error_rate, 4),
            "modified_files": modified_files,
            "modified_symbols": directly_modified_symbols,
            "impacted_routes": impacted_routes,
            "impacted_topics": impacted_topics,
            "findings": [f.to_dict() for f in findings],
            "p0_symbols": p0_symbols
        }


class PRBotCommentFormatter:
    """Formats PRReviewEngine analysis results into GitHub Flavored Markdown."""

    def __init__(self, analysis: Dict[str, Any]):
        self.data = analysis

    def _badge(self) -> str:
        verdict = self.data.get("verdict", "APPROVED")
        if verdict == "APPROVED":
            return "![Verdict: APPROVED](https://img.shields.io/badge/Architecture_Gate-APPROVED-22c55e?style=for-the-badge&logo=checkmarx&logoColor=white)"
        elif verdict == "WARNING":
            return "![Verdict: WARNING](https://img.shields.io/badge/Architecture_Gate-WARNING-f59e0b?style=for-the-badge&logo=alert&logoColor=white)"
        else:
            return "![Verdict: BLOCKED](https://img.shields.io/badge/Architecture_Gate-BLOCKED-ef4444?style=for-the-badge&logo=shield&logoColor=white)"

    def _tier_badge(self) -> str:
        tier = self.data.get("production_risk_tier", "P4_DORMANT")
        colors = {
            "P0_CRITICAL": "ef4444",
            "P1_HIGH": "f97316",
            "P2_MODERATE": "eab308",
            "P3_LOW": "3b82f6",
            "P4_DORMANT": "6b7280"
        }
        color = colors.get(tier, "6b7280")
        return f"![Traffic Risk: {tier}](https://img.shields.io/badge/Production_Risk-{tier}-{color}?style=flat-square)"

    def format_markdown(self, pr_number: Optional[int] = None) -> str:
        lines: List[str] = [
            STICKY_PR_BOT_MARKER,
            "## 🏛️ Agtoosa Architecture & Blast Radius Bot",
            "",
            f"{self._badge()}  {self._tier_badge()}",
            ""
        ]

        # Executive Metrics Summary Table
        syms = self.data.get("modified_symbols", [])
        routes = self.data.get("impacted_routes", [])
        topics = self.data.get("impacted_topics", [])
        findings = self.data.get("findings", [])
        errors = [f for f in findings if f.get("severity") == "ERROR"]
        warnings = [f for f in findings if f.get("severity") == "WARNING"]
        tier = self.data.get("production_risk_tier", "P4_DORMANT")
        traffic = self.data.get("total_traffic_at_risk", 0)

        lines.append("| Metric | Value | Status |")
        lines.append("|:---|:---:|:---|")
        lines.append(f"| **Overall Gate Verdict** | `{self.data.get('verdict')}` | {'✅ Clean' if self.data.get('verdict') == 'APPROVED' else '⚠️ Attention Required'} |")
        lines.append(f"| **Production Traffic Risk** | `{tier}` | **{traffic:,}** invocations/hr at risk |")
        lines.append(f"| **Directly Modified Symbols** | `{len(syms)}` | Functions, classes, variables |")
        lines.append(f"| **HTTP API Routes Impacted** | `{len(routes)}` | Endpoints & handlers touched |")
        lines.append(f"| **Event Topics / Queues Touched** | `{len(topics)}` | Decoupled async message flows |")
        lines.append(f"| **Architectural Invariant Alarms** | `{len(errors)} errors, {len(warnings)} warnings` | Clean architecture adherence |")
        lines.append("")

        # 1. Architectural Invariant Alarms (if any)
        if findings:
            lines.append("### 🚨 Architectural Drift Alarms")
            lines.append("")
            for f in findings:
                if f.get("severity") == "ERROR":
                    lines.append(f"> [!CAUTION]")
                    lines.append(f"> **Blocker: {f.get('category')}** in `{f.get('symbol_or_path')}`")
                    lines.append(f"> {f.get('message')}")
                    lines.append("")
                else:
                    lines.append(f"> [!WARNING]")
                    lines.append(f"> **Warning: {f.get('category')}** in `{f.get('symbol_or_path')}`")
                    lines.append(f"> {f.get('message')}")
                    lines.append("")
        else:
            lines.append("> [!NOTE]")
            lines.append("> ✨ **Invariants Verified**: Zero circular dependencies, layer boundary inversions, or unhandled exceptions detected.")
            lines.append("")

        # 2. HTTP API Route Contracts (DEV-025)
        if routes:
            lines.append("<details><summary><b>🌐 Impacted HTTP API Routes (" + str(len(routes)) + ")</b></summary>")
            lines.append("")
            lines.append("| Method | Route Path | Bound Handler | Framework | Impact Reason |")
            lines.append("|:---:|:---|:---|:---:|:---|")
            for r in routes:
                m = f"`{r['http_method']}`"
                lines.append(f"| {m} | `{r['path']}` | `{r['handler_name']}` | {r['framework']} | {r['reason']} |")
            lines.append("</details>")
            lines.append("")

        # 3. Message Queue & Event Bus Lineage (DEV-026)
        if topics:
            lines.append("<details><summary><b>📡 Impacted Message Queues & Event Bus Topics (" + str(len(topics)) + ")</b></summary>")
            lines.append("")
            lines.append("| Topic / Queue | Broker | Publishers | Subscribers | Orphan Risk |")
            lines.append("|:---|:---:|:---:|:---:|:---|")
            for t in topics:
                orphan_badge = "⚠️ " + t["orphan_reason"] if t.get("is_orphan") else "✅ Connected"
                lines.append(f"| `{t['name']}` | `{t['broker'].upper()}` | {t['publishers_count']} | {t['subscribers_count']} | {orphan_badge} |")
            lines.append("</details>")
            lines.append("")

        # 4. Modified Symbols & Upstream Blast Radius
        if syms:
            lines.append("### 🔍 Modified Symbols & Upstream Blast Radius")
            lines.append("")
            lines.append("| Symbol | Type | Path | Blast Radius (Callers) | Top Upstream Callers |")
            lines.append("|:---|:---:|:---|:---:|:---|")
            for s in syms:
                callers = ", ".join(s.get("top_dependents", [])) or "*(None)*"
                cnt = s.get("impacted_count", 0)
                risk_tag = " ⚠️" if cnt >= 5 else ""
                lines.append(f"| `{s['name']}` | `{s['type']}` | `{s['path']}` | **{cnt}**{risk_tag} | {callers} |")
            lines.append("")

        # 5. Targeted Test Commands
        lines.append("### 🧪 Recommended Verification Commands")
        lines.append("```bash")
        lines.append("# Verify knowledge graph invariants and local guard status")
        lines.append("agtoosa guard --strict")
        lines.append("")
        lines.append("# Run targeted automated tests")
        lines.append("python -m pytest tests/")
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("*Generated by [Agtoosa2](https://github.com/sky2464/Agtoosa2) Architectural Quality Gate*")

        return "\n".join(lines)


def post_or_update_pr_comment(
    repo: str,
    pr_number: int,
    comment_body: str,
    token: str
) -> Dict[str, Any]:
    """Post or update a sticky PR comment on GitHub using standard library urllib."""
    api_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "agtoosa-pr-bot/0.5.0",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # 1. Fetch existing comments to search for sticky marker
    req = urllib.request.Request(api_url, headers=headers, method="GET")
    existing_comment_id = None

    try:
        with urllib.request.urlopen(req) as resp:
            comments = json.loads(resp.read().decode("utf-8"))
            for c in comments:
                body = c.get("body", "")
                if STICKY_PR_BOT_MARKER in body:
                    existing_comment_id = c.get("id")
                    break
    except urllib.error.HTTPError as e:
        # Continue to attempt POST if list failed
        pass

    # 2. Update existing or create new
    payload = json.dumps({"body": comment_body}).encode("utf-8")
    headers["Content-Type"] = "application/json"

    if existing_comment_id:
        update_url = f"https://api.github.com/repos/{repo}/issues/comments/{existing_comment_id}"
        put_req = urllib.request.Request(update_url, data=payload, headers=headers, method="PATCH")
        with urllib.request.urlopen(put_req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    else:
        post_req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(post_req) as resp:
            return json.loads(resp.read().decode("utf-8"))
