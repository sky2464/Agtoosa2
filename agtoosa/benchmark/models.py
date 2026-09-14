"""Domain models for Continuous Performance Benchmarking (DEV-032 / Stage 32).

Defines telemetry data structures, benchmark measurement results,
regression comparisons, and comprehensive CI benchmark reports.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkResult:
    """Measurement outcome of an individual benchmarked code symbol."""
    node_id: str
    name: str
    path: str
    iterations: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    avg_ms: float
    min_ms: float
    max_ms: float
    throughput_ops_sec: float
    peak_memory_bytes: int = 0
    status: str = "completed"  # "completed", "skipped", "unsupported", "failed"
    skip_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BenchmarkResult:
        return cls(**data)


@dataclass
class RegressionComparison:
    """Evaluation of current benchmark performance against historical baseline."""
    node_id: str
    name: str
    path: str
    baseline_p95_ms: float
    current_p95_ms: float
    baseline_p50_ms: float
    current_p50_ms: float
    delta_pct: float
    diff_ms: float
    verdict: str  # "PASSED", "WARNING", "REGRESSION", "IMPROVED"
    severity: str  # "INFO", "WARNING", "CRITICAL"
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RegressionComparison:
        return cls(**data)


@dataclass
class BenchmarkReport:
    """Aggregate report evaluating performance across all benchmarked symbols."""
    verdict: str  # "PASSED", "WARNING", "REGRESSION_DETECTED"
    total_benchmarked: int
    regressions_count: int
    threshold_pct: float
    comparisons: List[RegressionComparison] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "total_benchmarked": self.total_benchmarked,
            "regressions_count": self.regressions_count,
            "threshold_pct": self.threshold_pct,
            "timestamp": self.timestamp,
            "duration_sec": self.duration_sec,
            "comparisons": [c.to_dict() for c in self.comparisons]
        }

    def to_markdown(self) -> str:
        """Generate a GitHub-compatible markdown summary for CI PR comments."""
        verdict_badge = {
            "PASSED": "✅ **PASSED**",
            "WARNING": "⚠️ **WARNING**",
            "REGRESSION_DETECTED": "🚨 **REGRESSION DETECTED**"
        }.get(self.verdict, self.verdict)

        lines = [
            "## ⚡ Agtoosa Performance Regression Benchmark",
            f"**Verdict**: {verdict_badge} | **Threshold**: +{self.threshold_pct:.1f}% | **Symbols Tested**: {self.total_benchmarked}",
            "",
            "| Symbol | Path | Baseline p95 | Current p95 | $\\Delta\\%$ | Status |",
            "|---|---|---|---|---|---|"
        ]

        if not self.comparisons:
            lines.append("| _No symbols benchmarked_ | - | - | - | - | - |")
        else:
            for c in self.comparisons:
                status_icon = {
                    "PASSED": "🟢 Normal",
                    "IMPROVED": "🚀 Faster",
                    "WARNING": "🟡 Warning",
                    "REGRESSION": "🔴 Regressed"
                }.get(c.verdict, c.verdict)

                delta_str = f"+{c.delta_pct:.1f}%" if c.delta_pct >= 0 else f"{c.delta_pct:.1f}%"
                lines.append(
                    f"| `{c.name}` | `{c.path}` | {c.baseline_p95_ms:.2f}ms | {c.current_p95_ms:.2f}ms | **{delta_str}** | {status_icon} |"
                )

        lines.append("")
        if self.regressions_count > 0:
            lines.append(f"> ⚠️ **{self.regressions_count} performance regression(s) exceed the +{self.threshold_pct:.1f}% threshold.**")
        else:
            lines.append("> ✨ **All symbols meet architectural runtime latency SLAs.**")

        return "\n".join(lines)
