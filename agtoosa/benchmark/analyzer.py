"""Statistical Performance Regression Analyzer (DEV-032 / Stage 32).

Evaluates active micro-benchmark outcomes against historical baselines,
calculates p50 and p95 latency shift percentages, and enforces SLA thresholds.
"""

from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agtoosa.graph.store import GraphStore
from agtoosa.benchmark.models import BenchmarkResult, RegressionComparison, BenchmarkReport
from agtoosa.benchmark.baseline import BenchmarkBaselineStore


class RegressionAnalyzer:
    """Detects latency and throughput regressions against baseline thresholds."""

    def __init__(
        self,
        store: Optional[GraphStore] = None,
        workspace_root: Optional[Path] = None,
        baseline_store: Optional[BenchmarkBaselineStore] = None
    ):
        self.store = store
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.baseline_store = baseline_store or BenchmarkBaselineStore(self.workspace_root)

    def analyze(
        self,
        current_results: List[BenchmarkResult],
        threshold_pct: float = 10.0,
        baseline_override: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> BenchmarkReport:
        """Compare current benchmark results against baseline performance.

        Args:
            current_results: Benchmark measurements for the active run.
            threshold_pct: Percentage increase in latency before flagging a regression (e.g. 10.0 = +10%).
            baseline_override: Optional explicit baseline mapping to compare against.

        Returns:
            BenchmarkReport with detailed comparisons and regression verdicts.
        """
        baseline = baseline_override if baseline_override is not None else self.baseline_store.load_baseline()

        # If baseline is empty and store has runtime telemetry, fallback to telemetry
        if not baseline and self.store:
            self.baseline_store.seed_from_telemetry(self.store)
            baseline = self.baseline_store.load_baseline()

        comparisons: List[RegressionComparison] = []
        regressions_count = 0

        for cur in current_results:
            base_info = baseline.get(cur.node_id)
            if not base_info:
                # No prior baseline: new symbol passed by default
                comparisons.append(
                    RegressionComparison(
                        node_id=cur.node_id,
                        name=cur.name,
                        path=cur.path,
                        baseline_p95_ms=cur.p95_ms,
                        current_p95_ms=cur.p95_ms,
                        baseline_p50_ms=cur.p50_ms,
                        current_p50_ms=cur.p50_ms,
                        delta_pct=0.0,
                        diff_ms=0.0,
                        verdict="PASSED",
                        severity="INFO",
                        details="New symbol: baseline established"
                    )
                )
                continue

            base_p95 = float(base_info.get("p95_ms", cur.p95_ms))
            base_p50 = float(base_info.get("p50_ms", cur.p50_ms))
            diff_ms = cur.p95_ms - base_p95

            # Compute percentage delta
            if base_p95 > 0.0001:
                delta_pct = (diff_ms / base_p95) * 100.0
            else:
                delta_pct = 0.0

            # Determine verdict and severity
            if delta_pct > threshold_pct:
                verdict = "REGRESSION"
                severity = "CRITICAL"
                regressions_count += 1
                details = f"Latency p95 regressed by +{delta_pct:.1f}% (+{diff_ms:.2f}ms)"
            elif delta_pct > (threshold_pct * 0.5):
                verdict = "WARNING"
                severity = "WARNING"
                details = f"Latency p95 increased by +{delta_pct:.1f}% (+{diff_ms:.2f}ms)"
            elif delta_pct < -threshold_pct:
                verdict = "IMPROVED"
                severity = "INFO"
                details = f"Latency p95 improved by {delta_pct:.1f}% ({diff_ms:.2f}ms)"
            else:
                verdict = "PASSED"
                severity = "INFO"
                details = f"Latency change within SLA (+{delta_pct:.1f}%)"

            comparisons.append(
                RegressionComparison(
                    node_id=cur.node_id,
                    name=cur.name,
                    path=cur.path,
                    baseline_p95_ms=base_p95,
                    current_p95_ms=cur.p95_ms,
                    baseline_p50_ms=base_p50,
                    current_p50_ms=cur.p50_ms,
                    delta_pct=delta_pct,
                    diff_ms=diff_ms,
                    verdict=verdict,
                    severity=severity,
                    details=details
                )
            )

        overall_verdict = "REGRESSION_DETECTED" if regressions_count > 0 else "PASSED"

        return BenchmarkReport(
            verdict=overall_verdict,
            total_benchmarked=len(current_results),
            regressions_count=regressions_count,
            threshold_pct=threshold_pct,
            comparisons=comparisons,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
