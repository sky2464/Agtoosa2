"""Review Intelligence: Architecture drift alarms, layer boundary enforcement, and PR diff analysis."""

from dataclasses import dataclass, field, asdict
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.core.model import Node, Edge, NodeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.metrics import MetricsEngine
from agtoosa.graph.query import compute_impact, resolve_node


@dataclass
class DriftFinding:
    severity: str  # "ERROR", "WARNING", "INFO"
    category: str  # "CYCLE", "LAYER_VIOLATION", "BLAST_RADIUS", "UNLINKED_CODE", "MISSING_DOC"
    message: str
    symbol_or_path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DriftReport:
    verdict: str  # "APPROVED", "WARNING", "BLOCKED"
    findings: List[DriftFinding] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    affected_stories: List[str] = field(default_factory=list)
    pr_diff_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "findings": [f.to_dict() for f in self.findings],
            "modified_files": self.modified_files,
            "affected_stories": self.affected_stories,
            "pr_diff_summary": self.pr_diff_summary
        }


class ReviewIntelligenceEngine:
    """Detects architectural drift, circular dependencies, layer violations, and PR risks."""

    # Explicit Architectural Tier Hierarchy (Higher numbers = deeper/foundational layers)
    # Tier 1: Entrypoints & Presentation (cli, mcp)
    # Tier 2: Application, Engine & Infrastructure (parser, graph, watcher, review)
    # Tier 3: Domain Core & Foundational Entities (core)
    DOMAIN_TIERS = {
        "cli": 1,
        "mcp": 1,
        "review": 2,
        "watcher": 2,
        "parser": 2,
        "graph": 2,
        "core": 3,
    }

    def __init__(self, store: GraphStore, workspace_root: Path):
        self.store = store
        self.workspace_root = workspace_root.resolve()
        self.metrics_engine = MetricsEngine(store)

    def _get_path_tier(self, path: str) -> Optional[int]:
        """Determine architectural tier from file or module path."""
        normalized = path.replace("\\", "/").lower()
        if "core/model" in normalized or "core/security" in normalized:
            return 3  # Tier 3: Foundational Domain Entities & Security Primitives
        if "core/context_compiler" in normalized or "core/lifecycle" in normalized or "core/topology_compiler" in normalized:
            return 2  # Tier 2: Application Services

        parts = normalized.split("/")
        for part in parts:
            if part in self.DOMAIN_TIERS:
                return self.DOMAIN_TIERS[part]
        return None

    def check_layer_invariants(self) -> List[DriftFinding]:
        """Verify architectural tiers (e.g. low-level Graph Store must never import high-level CLI/MCP)."""
        findings: List[DriftFinding] = []
        edges = self.store.get_all_edges()

        for edge in edges:
            if edge.get("edge_type") not in ("imports", "calls"):
                continue

            src_id = edge["source_id"]
            tgt_id = edge["target_id"]

            src_node = self.store.get_node(src_id)
            tgt_node = self.store.get_node(tgt_id)

            if not src_node or not tgt_node:
                continue

            src_tier = self._get_path_tier(src_node.get("path", ""))
            tgt_tier = self._get_path_tier(tgt_node.get("path", ""))

            # Layer violation: Lower tier component (higher tier number) importing higher tier component (lower tier number)
            # Example: src_tier=3 (graph) importing tgt_tier=1 (cli)
            if src_tier and tgt_tier and src_tier > tgt_tier:
                findings.append(DriftFinding(
                    severity="ERROR",
                    category="LAYER_VIOLATION",
                    message=f"Layer Boundary Violation: Tier {src_tier} component '{src_node['name']}' ({src_node['path']}) imports Tier {tgt_tier} component '{tgt_node['name']}' ({tgt_node['path']}). Lower tiers must never depend on higher tiers.",
                    symbol_or_path=src_node["path"]
                ))

        return findings

    def check_cycles(self) -> List[DriftFinding]:
        """Check for cyclic dependencies introduced into the graph."""
        findings: List[DriftFinding] = []
        cycles = self.metrics_engine.detect_cycles()

        for cycle in cycles:
            cycle_str = " ➔ ".join(cycle["cycle_nodes"][:5])
            if len(cycle["cycle_nodes"]) > 5:
                cycle_str += f" ... ({len(cycle['cycle_nodes'])} nodes)"

            findings.append(DriftFinding(
                severity="ERROR",
                category="CYCLE",
                message=f"Cyclic Dependency Detected ({cycle['length']} hops): {cycle_str}",
                symbol_or_path=cycle["cycle_nodes"][0] if cycle["cycle_nodes"] else ""
            ))

        return findings

    def check_blast_radius(self, modified_files: List[str], max_impact_threshold: int = 5) -> List[DriftFinding]:
        """Evaluate upstream blast radius for modified files."""
        findings: List[DriftFinding] = []

        for fpath in modified_files:
            file_node = self.store.get_node(f"file:{fpath}")
            if not file_node:
                continue

            impact_res = compute_impact(self.store, file_node["id"], max_depth=3)
            if impact_res and impact_res["impacted_count"] >= max_impact_threshold:
                top_callers = [f"{c['node_type'].upper()} {c['name']} ({c['path']})" for c in impact_res["impacted"][:3]]
                callers_summary = ", ".join(top_callers)
                findings.append(DriftFinding(
                    severity="WARNING",
                    category="BLAST_RADIUS",
                    message=f"High Blast Radius: Modifying '{fpath}' impacts {impact_res['impacted_count']} upstream dependents (e.g. {callers_summary}). Ensure regression tests verify these callers.",
                    symbol_or_path=fpath
                ))

        return findings

    def check_unlinked_debt(self, modified_files: List[str]) -> List[DriftFinding]:
        """Detect unindexed files or public symbols lacking documentation."""
        findings: List[DriftFinding] = []

        for fpath in modified_files:
            # Skip hidden files or configuration files in hidden directories (e.g. .github, .gitignore)
            if fpath.startswith(".") or "/." in fpath:
                continue

            file_node = self.store.get_node(f"file:{fpath}")
            if not file_node:
                findings.append(DriftFinding(
                    severity="WARNING",
                    category="UNLINKED_CODE",
                    message=f"File '{fpath}' is modified in Git but not indexed in the knowledge graph. Run 'agtoosa graph build'.",
                    symbol_or_path=fpath
                ))

        return findings

    def get_git_modified_files(self) -> List[str]:
        """Query Git status for modified, added, or untracked files."""
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain", "-uall"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=True
            )
            files = []
            for line in res.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    p_str = parts[-1]
                    target_p = self.workspace_root / p_str
                    if target_p.is_file():
                        files.append(p_str)
            return sorted(list(set(files)))
        except (subprocess.SubprocessError, FileNotFoundError):
            return []

    def diff_against_git(self, base_ref: str = "HEAD") -> Dict[str, Any]:
        """Map Git line diffs directly to graph symbols and blast radius."""
        modified_files: List[str] = []
        symbol_impacts: List[Dict[str, Any]] = []

        try:
            # 1. Get changed files
            res = subprocess.run(
                ["git", "diff", "--name-only", base_ref],
                cwd=self.workspace_root,
                capture_output=True,
                text=True
            )
            if res.returncode == 0:
                modified_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]

            # 2. Get line diffs per file and intersect with symbol locations
            diff_res = subprocess.run(
                ["git", "diff", "-U0", base_ref],
                cwd=self.workspace_root,
                capture_output=True,
                text=True
            )
            current_file: Optional[str] = None
            hunk_regex = re.compile(r"^@@ -[0-9]+(?:,[0-9]+)? \+([0-9]+)(?:,([0-9]+))? @@")

            changed_lines_by_file: Dict[str, Set[int]] = {}

            for line in diff_res.stdout.splitlines():
                if line.startswith("+++ b/"):
                    current_file = line[6:].strip()
                    changed_lines_by_file.setdefault(current_file, set())
                elif line.startswith("@@ ") and current_file:
                    m = hunk_regex.match(line)
                    if m:
                        start = int(m.group(1))
                        count = int(m.group(2)) if m.group(2) else 1
                        for lnum in range(start, start + count):
                            changed_lines_by_file[current_file].add(lnum)

            # 3. Intersect lines with symbols in knowledge graph
            for fpath, lines in changed_lines_by_file.items():
                with self.store._get_connection() as conn:
                    rows = conn.execute(
                        "SELECT id, name, node_type, start_line, end_line FROM nodes WHERE path = ? AND node_type IN ('class', 'function');",
                        (fpath,)
                    ).fetchall()
                    for r in rows:
                        s_start = r["start_line"]
                        s_end = r["end_line"] or s_start
                        if s_start and any(s_start <= lnum <= s_end for lnum in lines):
                            # Symbol was directly modified
                            sym_id = r["id"]
                            impact = compute_impact(self.store, sym_id, max_depth=3)
                            impacted_cnt: int = int(impact["impacted_count"]) if (impact and "impacted_count" in impact) else 0
                            symbol_impacts.append({
                                "id": sym_id,
                                "name": r["name"],
                                "type": r["node_type"],
                                "path": fpath,
                                "impacted_count": impacted_cnt,
                                "top_dependents": [imp["name"] for imp in (impact["impacted"][:3] if impact else [])]
                            })

        except Exception:
            pass

        return {
            "base_ref": base_ref,
            "modified_file_count": len(modified_files),
            "modified_files": modified_files,
            "directly_modified_symbols": symbol_impacts,
            "high_risk_symbols": [s for s in symbol_impacts if int(s.get("impacted_count", 0)) >= 5]
        }

    def review(self, modified_files: Optional[List[str]] = None, diff_base: Optional[str] = None) -> DriftReport:
        """Execute full review pipeline: layers, cycles, blast radius, unlinked debt, and PR diff."""
        if modified_files is None:
            modified_files = self.get_git_modified_files()

        findings: List[DriftFinding] = []

        # 1. Layer boundary checks
        findings.extend(self.check_layer_invariants())

        # 2. Cycle detection
        findings.extend(self.check_cycles())

        # 3. Blast radius warnings
        findings.extend(self.check_blast_radius(modified_files))

        # 4. Unlinked code & debt
        findings.extend(self.check_unlinked_debt(modified_files))

        # 5. Monorepo package boundary checks (if monorepo detected)
        try:
            from agtoosa.review.monorepo import MonorepoBoundaryEngine
            mono_engine = MonorepoBoundaryEngine(self.workspace_root, store=self.store)
            mono_report = mono_engine.check_boundaries()
            if mono_report.is_monorepo:
                for v in mono_report.violations:
                    findings.append(DriftFinding(
                        severity=v.severity,
                        category=f"MONOREPO_{v.rule}",
                        message=f"[{v.rule}] {v.message}",
                        symbol_or_path=v.source_file or v.source_package
                    ))
        except Exception:
            pass

        # 5. Affected stories
        affected_stories = set()
        for fpath in modified_files:
            file_node = self.store.get_node(f"file:{fpath}")
            if file_node:
                neighbors = self.store.get_neighbors(file_node["id"], direction="in")
                for n in neighbors:
                    if n.get("node_type") == "story":
                        affected_stories.add(n["name"])

        # 6. Optional Git PR Diff
        pr_diff_summary = None
        if diff_base:
            pr_diff_summary = self.diff_against_git(diff_base)

        # Verdict calculation
        has_errors = any(f.severity == "ERROR" for f in findings)
        has_warnings = any(f.severity == "WARNING" for f in findings)

        if has_errors:
            verdict = "BLOCKED"
        elif has_warnings:
            verdict = "WARNING"
        else:
            verdict = "APPROVED"

        return DriftReport(
            verdict=verdict,
            findings=findings,
            modified_files=modified_files,
            affected_stories=sorted(list(affected_stories)),
            pr_diff_summary=pr_diff_summary
        )
