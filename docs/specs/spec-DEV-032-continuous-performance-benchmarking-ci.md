# Specification: DEV-032 Continuous Performance Regression Benchmarking CI

## 1. Problem Statement
Architectural quality gates (DEV-024, DEV-029) guard static invariants such as circular dependencies, layer boundary leaks, and production blast radius. However, silent runtime latency and memory throughput regressions often slip through code reviews:
- Inefficient $O(N^2)$ algorithm changes in utility functions or data parsing loops.
- Accidental synchronous I/O or redundant serialization in high-throughput endpoints.
- Unmonitored memory footprint expansion in AST compilers and graph queries.

Existing benchmark tools (e.g. pytest-benchmark) are disconnected from the architectural knowledge graph, lack integration with runtime telemetry, and require manual benchmark harness authoring for every function.

## 2. Architecture & Design

### 2.1 AST-Targeted Benchmark Discovery (`BenchmarkHarness`)
The benchmark harness cross-references PR git diffs (`base_ref` vs `HEAD`) with the Agtoosa SQLite knowledge graph:
1. Discovers modified files in the working tree or PR diff.
2. Identifies all contained callable nodes (`NodeType.FUNCTION`, `NodeType.METHOD`, `NodeType.ENDPOINT`).
3. Executes calibrated micro-benchmarks across $N$ iterations (default: 50–100) with preceding warmup passes to avoid JIT/cold-start distortion.
4. Uses standard library `time.perf_counter_ns()` for nanosecond precision and `tracemalloc` for peak heap memory allocation.

### 2.2 Dual-Baseline Strategy (`BenchmarkBaselineStore`)
Performance comparisons are drawn from two complementary baseline sources:
1. **Persistent Baseline Snapshot** (`.agtoosa/benchmarks/baseline.json`):
   - Tagged release baselines (e.g. `main`, `v0.4.0`) capturing golden SLA metrics.
2. **Runtime Telemetry Fallback** (`GraphStore.runtime_telemetry`):
   - When no explicit baseline snapshot exists, automatically seeds baseline entries from ingested OpenTelemetry / profiler traces (DEV-017 / DEV-030).

### 2.3 Statistical Regression Analyzer (`RegressionAnalyzer`)
- Calculates p50, p95, and p99 percentiles, average latency, and throughput (ops/sec).
- Computes percentage shift:
  $$\Delta\% = \frac{\text{Current } p95 - \text{Baseline } p95}{\text{Baseline } p95} \times 100\%$$
- Applies SLA circuit breaker thresholds:
  - $\Delta\% > \text{threshold}$ (default: $+10.0\%$): Flags `REGRESSION` (`CRITICAL`).
  - $\Delta\% > 0.5 \times \text{threshold}$: Flags `WARNING`.
  - $\Delta\% < -\text{threshold}$: Flags `IMPROVED`.
  - Otherwise: `PASSED`.
- Generates GitHub PR markdown tables and structured JSON outputs.

### 2.4 Developer, CLI & MCP Surfaces
- **CLI Commands**:
  - `agtoosa ci benchmark [--base <ref>] [--threshold <pct>] [--strict] [--save-baseline] [--output <path>] [--json]`
  - `agtoosa benchmark run [--target <path_or_symbol>] [--iterations <N>] [--threshold <pct>] [--save-baseline] [--json]`
  - `agtoosa benchmark snapshot [--name <label>] [--json]`
- **MCP Tool**:
  - `agtoosa_run_performance_benchmark`: Allows AI coding agents (Cursor, Claude, Copilot) to evaluate performance before approving PRs or suggesting refactoring fixes.
- **CI Workflow**:
  - `.github/workflows/agtoosa-benchmark.yml`: Runs on PRs to `main`/`master`, evaluating performance regressions against `origin/main` with sticky GitHub comment updates.
