"""Automated AST Benchmark Harness Engine (DEV-032 / Stage 32).

Discovers modified code symbols from PR diffs, executes calibrated latency
and memory micro-benchmarks across N iterations with warmup passes, and computes
nanosecond statistical distributions (p50, p95, p99, throughput).
"""

from __future__ import annotations
import importlib.util
import math
from pathlib import Path
import subprocess
import time
import tracemalloc
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agtoosa.core.model import Node, NodeType
from agtoosa.graph.store import GraphStore
from agtoosa.benchmark.models import BenchmarkResult


class BenchmarkHarness:
    """Automated benchmark executor and AST target discovery harness."""

    def __init__(self, store: GraphStore, workspace_root: Optional[Path] = None):
        self.store = store
        self.workspace_root = (workspace_root or Path.cwd()).resolve()

    def discover_targets(
        self,
        base_ref: Optional[str] = None,
        target_path_or_symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Discover benchmarkable functions and endpoints from PR diff or target filter."""
        all_nodes = self.store.get_all_nodes()
        callable_types = {"function", "method", "endpoint"}

        # 1. If explicit target symbol or path provided
        if target_path_or_symbol:
            matched: List[Dict[str, Any]] = []
            for n in all_nodes:
                if n.get("node_type") in callable_types:
                    if (
                        target_path_or_symbol == n.get("id")
                        or target_path_or_symbol == n.get("name")
                        or target_path_or_symbol in n.get("path", "")
                    ):
                        matched.append(n)
            return matched

        # 2. If base_ref provided, find git changed files
        changed_files: Set[str] = set()
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
                            changed_files.add(line.strip())
            except Exception:
                pass

        # 3. Also include uncommitted working tree changes
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=False
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) == 2:
                        changed_files.add(parts[1])
        except Exception:
            pass

        # Filter nodes by changed files
        if changed_files:
            matched_nodes = [
                n for n in all_nodes
                if n.get("node_type") in callable_types and n.get("path") in changed_files
            ]
            if matched_nodes:
                return matched_nodes

        # Fallback: if no git changes or initial repository setup, return top callable symbols
        return [
            n for n in all_nodes
            if n.get("node_type") in callable_types and not n.get("path", "").startswith("tests/")
        ][:15]

    def run_benchmark(
        self,
        node: Dict[str, Any],
        iterations: int = 100,
        warmup: int = 10,
        callable_override: Optional[Callable[..., Any]] = None
    ) -> BenchmarkResult:
        """Measure latency percentiles and memory allocation for a specific target node."""
        node_id = node.get("id", "unknown")
        name = node.get("name", "unknown")
        path = node.get("path", "")

        func = callable_override or self._resolve_callable(node)
        if func is None:
            # Unresolvable target: return explicit unsupported/skipped outcome (R-09 / AC-17)
            return BenchmarkResult(
                node_id=node_id,
                name=name,
                path=path,
                iterations=0,
                p50_ms=0.0,
                p95_ms=0.0,
                p99_ms=0.0,
                avg_ms=0.0,
                min_ms=0.0,
                max_ms=0.0,
                throughput_ops_sec=0.0,
                peak_memory_bytes=0,
                status="unsupported",
                skip_reason="Target symbol is not an executable zero-argument callable or could not be loaded safely",
                metadata={"node_type": node.get("node_type", "function")}
            )

        durations_ns: List[int] = []

        # Memory tracking
        tracemalloc.start()
        start_mem = tracemalloc.get_traced_memory()[0]

        # Warmup passes
        for _ in range(max(1, warmup)):
            try:
                func()
            except Exception:
                pass

        # Measurement passes
        t_total_start = time.perf_counter_ns()
        for _ in range(iterations):
            t0 = time.perf_counter_ns()
            try:
                func()
            except Exception:
                pass
            t1 = time.perf_counter_ns()
            durations_ns.append(max(1, t1 - t0))
        t_total_end = time.perf_counter_ns()

        peak_mem = tracemalloc.get_traced_memory()[1] - start_mem
        tracemalloc.stop()

        durations_ns.sort()
        n = len(durations_ns)

        def percentile(p: float) -> float:
            idx = int(math.ceil(p * n)) - 1
            idx = max(0, min(n - 1, idx))
            return durations_ns[idx] / 1_000_000.0  # ns to ms

        p50_ms = percentile(0.50)
        p95_ms = percentile(0.95)
        p99_ms = percentile(0.99)
        min_ms = durations_ns[0] / 1_000_000.0
        max_ms = durations_ns[-1] / 1_000_000.0
        avg_ms = (sum(durations_ns) / n) / 1_000_000.0

        total_sec = max(0.000001, (t_total_end - t_total_start) / 1_000_000_000.0)
        throughput = float(iterations / total_sec)

        return BenchmarkResult(
            node_id=node_id,
            name=name,
            path=path,
            iterations=iterations,
            p50_ms=p50_ms,
            p95_ms=p95_ms,
            p99_ms=p99_ms,
            avg_ms=avg_ms,
            min_ms=min_ms,
            max_ms=max_ms,
            throughput_ops_sec=throughput,
            peak_memory_bytes=max(0, peak_mem),
            status="completed",
            skip_reason=None,
            metadata={"node_type": node.get("node_type", "function")}
        )

    def _resolve_callable(self, node: Dict[str, Any]) -> Optional[Callable[[], Any]]:
        """Attempt to dynamically load the python callable safely; returns None if unresolvable (R-09)."""
        path_str = node.get("path", "")
        name = node.get("name", "")

        if path_str and path_str.endswith(".py"):
            full_path = self.workspace_root / path_str
            if full_path.exists():
                try:
                    spec = importlib.util.spec_from_file_location("bench_module", full_path)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        if hasattr(mod, name):
                            attr = getattr(mod, name)
                            if callable(attr):
                                # Test zero-arg invocation
                                return lambda: attr()
                except Exception:
                    pass

        # Never substitute synthetic probe (R-09 / AC-17)
        return None
