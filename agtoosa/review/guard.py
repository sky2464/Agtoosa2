"""Architectural Guard and Drift Linter Engine (DEV-024 / Stage 24).

Enforces pre-push & pre-commit architectural invariants:
- Zero circular dependencies (Tarjan cycle detection)
- Zero architectural layer boundary violations
- Upstream blast radius threshold protection
- Monorepo package boundary & export encapsulation enforcement
- Sub-millisecond status caching (.agtoosa/guard_status.json)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Set

from agtoosa.core.model import Node, Edge
from agtoosa.graph.store import GraphStore
from agtoosa.parser import ParserEngine
from agtoosa.review.intelligence import ReviewIntelligenceEngine, DriftFinding
from agtoosa.review.monorepo import MonorepoBoundaryEngine
from agtoosa.watcher.watcher import WorkspaceWatcher


@dataclass
class GuardFinding:
    severity: str  # "ERROR", "WARNING", "INFO"
    category: str  # "CYCLE", "LAYER_VIOLATION", "BLAST_RADIUS", "BOUNDARY_LEAK"
    message: str
    symbol_or_path: str
    remediation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GuardReport:
    verdict: str  # "PASSED", "WARNING", "BLOCKED"
    findings: List[GuardFinding] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: float = 0.0
    stats: Dict[str, int] = field(default_factory=lambda: {
        "cycles": 0,
        "layer_violations": 0,
        "blast_radius_violations": 0,
        "boundary_leaks": 0
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "findings": [f.to_dict() for f in self.findings],
            "modified_files": self.modified_files,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "stats": self.stats
        }


class ArchitecturalGuard:
    """Evaluates graph invariants for pre-push git gates and continuous daemon monitoring."""

    def __init__(self, store: GraphStore, workspace_root: Path):
        self.store = store
        self.workspace_root = workspace_root.resolve()
        self.intel = ReviewIntelligenceEngine(store, workspace_root)

    @property
    def status_file_path(self) -> Path:
        return self.workspace_root / ".agtoosa" / "guard_status.json"

    def read_status_cache(self) -> Optional[Dict[str, Any]]:
        """Read existing daemon status cache if available."""
        if not self.status_file_path.exists():
            return None
        try:
            return json.loads(self.status_file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def write_status_cache(self, report: GuardReport) -> None:
        """Atomically persist guard verdict cache for sub-millisecond hook checks."""
        self.status_file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.status_file_path.with_suffix(".tmp")
        try:
            tmp_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
            tmp_path.replace(self.status_file_path)
        except OSError:
            pass

    def _get_changed_files(self, base_ref: Optional[str] = None) -> List[str]:
        """Detect modified files either from base_ref, working tree, or unpushed commits."""
        files: Set[str] = set()

        # 1. Base ref diff if specified
        if base_ref:
            try:
                res = subprocess.run(
                    ["git", "diff", "--name-only", base_ref],
                    cwd=self.workspace_root,
                    capture_output=True,
                    text=True,
                    check=False
                )
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        if line.strip():
                            files.add(line.strip())
                    return sorted(list(files))
            except (subprocess.SubprocessError, FileNotFoundError):
                pass

        # 2. Local uncommitted & untracked changes
        for f in self.intel.get_git_modified_files():
            files.add(f)

        # 3. If in git repo, check unpushed commits against upstream if no local uncommitted files
        if not files:
            for ref_expr in ("@{upstream}..HEAD", "HEAD~1..HEAD"):
                try:
                    res = subprocess.run(
                        ["git", "diff", "--name-only", ref_expr],
                        cwd=self.workspace_root,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        for line in res.stdout.splitlines():
                            if line.strip():
                                files.add(line.strip())
                        break
                except (subprocess.SubprocessError, FileNotFoundError):
                    pass

        return sorted(list(files))

    def audit(
        self,
        base_ref: Optional[str] = None,
        max_blast_radius: int = 5,
        strict: bool = False
    ) -> GuardReport:
        """Perform comprehensive architectural invariant audit."""
        start_time = time.perf_counter()
        modified_files = self._get_changed_files(base_ref)
        findings: List[GuardFinding] = []

        # 1. Tarjan Circular Dependencies (Always ERROR)
        cycle_findings = self.intel.check_cycles()
        for cf in cycle_findings:
            findings.append(GuardFinding(
                severity="ERROR",
                category="CYCLE",
                message=cf.message,
                symbol_or_path=cf.symbol_or_path,
                remediation="Decouple cyclic dependency with 'agtoosa refactor decouple' or introduce dependency injection."
            ))

        # 2. Layer Boundary Invariants (Always ERROR)
        layer_findings = self.intel.check_layer_invariants()
        for lf in layer_findings:
            findings.append(GuardFinding(
                severity="ERROR",
                category="LAYER_VIOLATION",
                message=lf.message,
                symbol_or_path=lf.symbol_or_path,
                remediation="Invert dependency: low-level domain cores must not import presentation/CLI layers."
            ))

        # 3. Blast Radius Circuit Breaker
        blast_findings = self.intel.check_blast_radius(modified_files, max_impact_threshold=max_blast_radius)
        for bf in blast_findings:
            findings.append(GuardFinding(
                severity="ERROR" if strict else "WARNING",
                category="BLAST_RADIUS",
                message=bf.message,
                symbol_or_path=bf.symbol_or_path,
                remediation=f"Ensure regression tests cover impacted callers or reduce coupling to '{bf.symbol_or_path}'."
            ))

        # 4. Monorepo Package Boundary Enforcement (if monorepo exists)
        monorepo_engine = MonorepoBoundaryEngine(self.workspace_root, self.store)
        packages = monorepo_engine.discover_packages()
        boundary_leaks = 0
        if packages:
            mono_report = monorepo_engine.audit()
            for v in mono_report.violations:
                boundary_leaks += 1
                findings.append(GuardFinding(
                    severity=v.severity,
                    category="BOUNDARY_LEAK",
                    message=v.message,
                    symbol_or_path=v.source_file,
                    remediation=v.remediation
                ))

        # Stats tabulation
        stats = {
            "cycles": len(cycle_findings),
            "layer_violations": len(layer_findings),
            "blast_radius_violations": len(blast_findings),
            "boundary_leaks": boundary_leaks
        }

        # Determine Verdict
        has_errors = any(f.severity == "ERROR" for f in findings)
        has_warnings = any(f.severity == "WARNING" for f in findings)

        if has_errors:
            verdict = "BLOCKED"
        elif has_warnings and strict:
            verdict = "BLOCKED"
        elif has_warnings:
            verdict = "WARNING"
        else:
            verdict = "PASSED"

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        report = GuardReport(
            verdict=verdict,
            findings=findings,
            modified_files=modified_files,
            duration_ms=duration_ms,
            stats=stats
        )

        # Update cache
        self.write_status_cache(report)
        return report

    def run_daemon(
        self,
        interval: float = 3.0,
        max_blast_radius: int = 5,
        strict: bool = False,
        max_ticks: Optional[int] = None,
        on_tick: Optional[Callable[[GuardReport], None]] = None
    ) -> None:
        """Run continuous background monitoring daemon updating .agtoosa/guard_status.json."""
        watcher = WorkspaceWatcher(self.workspace_root, self.store, ParserEngine())
        ticks = 0

        # Initial tick
        report = self.audit(max_blast_radius=max_blast_radius, strict=strict)
        if on_tick:
            on_tick(report)
        ticks += 1

        while max_ticks is None or ticks < max_ticks:
            time.sleep(interval)
            changed_files, stats = watcher.poll_once()
            if changed_files or ticks == 1:
                report = self.audit(max_blast_radius=max_blast_radius, strict=strict)
                if on_tick:
                    on_tick(report)
            ticks += 1
