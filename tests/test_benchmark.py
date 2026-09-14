"""Automated test suite for DEV-032: Continuous Performance Regression Benchmarking CI."""

import argparse
import json
from pathlib import Path
import tempfile
import time
import unittest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.benchmark.models import BenchmarkResult, RegressionComparison, BenchmarkReport
from agtoosa.benchmark.baseline import BenchmarkBaselineStore
from agtoosa.benchmark.harness import BenchmarkHarness
from agtoosa.benchmark.analyzer import RegressionAnalyzer
from agtoosa.cli.lifecycle_cmd import cmd_ci_benchmark, cmd_benchmark_run, cmd_benchmark_snapshot
from agtoosa.mcp.server import MCPServer


class TestContinuousBenchmarking(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.db_path = self.workspace / ".agtoosa" / "graph.db"
        self.store = GraphStore(self.db_path)

        # Write real Python source for genuine benchmark execution (DEV-045 / R-09)
        app_dir = self.workspace / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "compute.py").write_text(
            "def fast_calc():\n    return sum(i for i in range(10))\n\n"
            "def slow_query():\n    return sum(i for i in range(100))\n",
            encoding="utf-8"
        )

        # Seed sample nodes into store
        self.node_fast = Node(
            id="function:app/compute.py:fast_calc",
            name="fast_calc",
            node_type=NodeType.FUNCTION,
            path="app/compute.py",
            start_line=1,
            end_line=2
        )
        self.node_slow = Node(
            id="function:app/compute.py:slow_query",
            name="slow_query",
            node_type=NodeType.FUNCTION,
            path="app/compute.py",
            start_line=4,
            end_line=5
        )
        self.store.insert_batch([self.node_fast, self.node_slow], [])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_benchmark_models_and_markdown(self):
        """Verify models convert to dict and format GitHub PR markdown correctly."""
        comp = RegressionComparison(
            node_id="function:app/compute.py:slow_query",
            name="slow_query",
            path="app/compute.py",
            baseline_p95_ms=10.0,
            current_p95_ms=15.0,
            baseline_p50_ms=8.0,
            current_p50_ms=12.0,
            delta_pct=50.0,
            diff_ms=5.0,
            verdict="REGRESSION",
            severity="CRITICAL",
            details="Latency p95 regressed by +50.0%"
        )
        report = BenchmarkReport(
            verdict="REGRESSION_DETECTED",
            total_benchmarked=1,
            regressions_count=1,
            threshold_pct=10.0,
            comparisons=[comp]
        )

        md = report.to_markdown()
        self.assertIn("Agtoosa Performance Regression Benchmark", md)
        self.assertIn("REGRESSION DETECTED", md)
        self.assertIn("+50.0%", md)
        self.assertIn("`slow_query`", md)
        self.assertIn("1 performance regression(s) exceed", md)

    def test_harness_run_benchmark(self):
        """Verify BenchmarkHarness measures execution times and calculates percentiles."""
        harness = BenchmarkHarness(self.store, self.workspace)

        def mock_workload():
            # simulate 1ms workload
            time.sleep(0.001)

        result = harness.run_benchmark(
            {"id": "test:func", "name": "mock_func", "path": "test.py"},
            iterations=20,
            warmup=2,
            callable_override=mock_workload
        )

        self.assertEqual(result.name, "mock_func")
        self.assertEqual(result.iterations, 20)
        self.assertGreater(result.p50_ms, 0.5)
        self.assertGreaterEqual(result.p95_ms, result.p50_ms)
        self.assertGreaterEqual(result.p99_ms, result.p95_ms)
        self.assertGreater(result.throughput_ops_sec, 0)
        self.assertEqual(result.status, "completed")

    def test_harness_unresolvable_target_returns_unsupported_not_synthetic(self):
        """Verify unresolvable targets return unsupported/skipped without synthetic fallback (DEV-045 / R-09 / AC-17)."""
        harness = BenchmarkHarness(self.store, self.workspace)
        node = {
            "id": "function:app/compute.py:nonexistent_func",
            "name": "nonexistent_func",
            "path": "app/compute.py"
        }
        res = harness.run_benchmark(node)
        self.assertEqual(res.status, "unsupported")
        self.assertIsNotNone(res.skip_reason)
        self.assertEqual(res.iterations, 0)
        self.assertEqual(res.p50_ms, 0.0)

    def test_baseline_store_persistence(self):
        """Verify BenchmarkBaselineStore saves, loads, and tags snapshots."""
        b_store = BenchmarkBaselineStore(self.workspace)
        self.assertEqual(b_store.load_baseline(), {})

        res = BenchmarkResult(
            node_id="function:app/compute.py:fast_calc",
            name="fast_calc",
            path="app/compute.py",
            iterations=50,
            p50_ms=2.0,
            p95_ms=3.0,
            p99_ms=3.5,
            avg_ms=2.1,
            min_ms=1.8,
            max_ms=4.0,
            throughput_ops_sec=500.0,
            peak_memory_bytes=1024
        )

        saved_path = b_store.save_baseline([res], tag="v1.0")
        self.assertTrue(saved_path.exists())

        loaded = b_store.load_baseline()
        self.assertIn(res.node_id, loaded)
        self.assertEqual(loaded[res.node_id]["p95_ms"], 3.0)
        self.assertEqual(loaded[res.node_id]["tag"], "v1.0")

    def test_baseline_store_seed_from_telemetry(self):
        """Verify seeding baseline from GraphStore runtime telemetry."""
        self.store.save_telemetry_batch([{
            "node_id": "function:app/compute.py:fast_calc",
            "call_count": 100,
            "total_duration_ms": 250.0,
            "avg_duration_ms": 2.5,
            "p95_duration_ms": 4.0,
            "error_count": 0
        }])

        b_store = BenchmarkBaselineStore(self.workspace)
        seeded = b_store.seed_from_telemetry(self.store)
        self.assertEqual(seeded, 1)

        loaded = b_store.load_baseline()
        self.assertIn("function:app/compute.py:fast_calc", loaded)
        self.assertEqual(loaded["function:app/compute.py:fast_calc"]["p95_ms"], 4.0)

    def test_regression_analyzer(self):
        """Verify RegressionAnalyzer detects regressions and improvements against baseline."""
        analyzer = RegressionAnalyzer(self.store, self.workspace)

        baseline_data = {
            "function:app/compute.py:fast_calc": {
                "node_id": "function:app/compute.py:fast_calc",
                "name": "fast_calc",
                "p95_ms": 10.0,
                "p50_ms": 8.0
            },
            "function:app/compute.py:slow_query": {
                "node_id": "function:app/compute.py:slow_query",
                "name": "slow_query",
                "p95_ms": 20.0,
                "p50_ms": 15.0
            }
        }

        # fast_calc regresses: 10.0 -> 15.0 (+50%)
        res_regressed = BenchmarkResult(
            node_id="function:app/compute.py:fast_calc",
            name="fast_calc",
            path="app/compute.py",
            iterations=50,
            p50_ms=12.0,
            p95_ms=15.0,
            p99_ms=16.0,
            avg_ms=12.5,
            min_ms=10.0,
            max_ms=18.0,
            throughput_ops_sec=100.0
        )

        # slow_query improves: 20.0 -> 12.0 (-40%)
        res_improved = BenchmarkResult(
            node_id="function:app/compute.py:slow_query",
            name="slow_query",
            path="app/compute.py",
            iterations=50,
            p50_ms=10.0,
            p95_ms=12.0,
            p99_ms=13.0,
            avg_ms=10.5,
            min_ms=8.0,
            max_ms=14.0,
            throughput_ops_sec=150.0
        )

        report = analyzer.analyze(
            [res_regressed, res_improved],
            threshold_pct=10.0,
            baseline_override=baseline_data
        )

        self.assertEqual(report.verdict, "REGRESSION_DETECTED")
        self.assertEqual(report.regressions_count, 1)

        comp_reg = next(c for c in report.comparisons if c.name == "fast_calc")
        self.assertEqual(comp_reg.verdict, "REGRESSION")
        self.assertEqual(comp_reg.severity, "CRITICAL")
        self.assertAlmostEqual(comp_reg.delta_pct, 50.0, places=1)

        comp_imp = next(c for c in report.comparisons if c.name == "slow_query")
        self.assertEqual(comp_imp.verdict, "IMPROVED")
        self.assertEqual(comp_imp.severity, "INFO")
        self.assertAlmostEqual(comp_imp.delta_pct, -40.0, places=1)

    def test_cli_ci_benchmark_and_run(self):
        """Verify 'agtoosa ci benchmark' and 'agtoosa benchmark run' CLI entrypoints."""
        args_ci = argparse.Namespace(
            command="ci",
            ci_action="benchmark",
            base=None,
            threshold=10.0,
            strict=False,
            save_baseline=True,
            output=None,
            json=True
        )
        rc_ci = cmd_ci_benchmark(args_ci, self.workspace)
        self.assertEqual(rc_ci, 0)

        # Verify snapshot command
        args_snap = argparse.Namespace(
            command="benchmark",
            benchmark_action="snapshot",
            name="baseline_test",
            json=True
        )
        rc_snap = cmd_benchmark_snapshot(args_snap, self.workspace)
        self.assertEqual(rc_snap, 0)

        # Verify run command
        args_run = argparse.Namespace(
            command="benchmark",
            benchmark_action="run",
            target="fast_calc",
            iterations=10,
            threshold=10.0,
            save_baseline=False,
            json=True
        )
        rc_run = cmd_benchmark_run(args_run, self.workspace)
        self.assertEqual(rc_run, 0)

    def test_mcp_performance_benchmark_tool(self):
        """Verify 'agtoosa_run_performance_benchmark' MCP tool call."""
        server = MCPServer(self.workspace)
        tool_defs = server.get_tool_definitions()
        bench_tool = next((t for t in tool_defs if t["name"] == "agtoosa_run_performance_benchmark"), None)
        self.assertIsNotNone(bench_tool)

        res_json = server.handle_tool_call(
            "agtoosa_run_performance_benchmark",
            {"target": "fast_calc", "iterations": 10, "threshold_pct": 15.0}
        )
        data = json.loads(res_json)
        self.assertIn("verdict", data)
        self.assertIn("total_benchmarked", data)
        self.assertIn("markdown", data)
        self.assertGreaterEqual(data["total_benchmarked"], 1)


if __name__ == "__main__":
    unittest.main()
