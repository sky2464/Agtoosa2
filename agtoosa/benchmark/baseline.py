"""Baseline Snapshot Store for Performance Benchmarking (DEV-032 / Stage 32).

Persists and manages historical performance baselines in `.agtoosa/benchmarks/baseline.json`,
with support for tagging, schema versioning, and seeding from live runtime telemetry.
"""

from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from agtoosa.graph.store import GraphStore
from agtoosa.benchmark.models import BenchmarkResult


class BenchmarkBaselineStore:
    """Manages persistent performance baselines and snapshot history."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.benchmarks_dir = self.workspace_root / ".agtoosa" / "benchmarks"
        self.baseline_file = self.benchmarks_dir / "baseline.json"

    def load_baseline(self) -> Dict[str, Dict[str, Any]]:
        """Load the active baseline performance benchmarks."""
        if not self.baseline_file.exists():
            return {}
        try:
            data = json.loads(self.baseline_file.read_text(encoding="utf-8"))
            return data.get("symbols", {})
        except (OSError, json.JSONDecodeError):
            return {}

    def save_baseline(
        self,
        results: List[BenchmarkResult],
        tag: Optional[str] = None
    ) -> Path:
        """Persist benchmark results as the new baseline snapshot."""
        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)

        existing = self.load_baseline()

        now_iso = datetime.now(timezone.utc).isoformat()
        for r in results:
            existing[r.node_id] = {
                "node_id": r.node_id,
                "name": r.name,
                "path": r.path,
                "iterations": r.iterations,
                "p50_ms": r.p50_ms,
                "p95_ms": r.p95_ms,
                "p99_ms": r.p99_ms,
                "avg_ms": r.avg_ms,
                "throughput_ops_sec": r.throughput_ops_sec,
                "peak_memory_bytes": r.peak_memory_bytes,
                "updated_at": now_iso,
                "tag": tag or "latest"
            }

        payload = {
            "version": "1.0.0",
            "tag": tag or "latest",
            "updated_at": now_iso,
            "total_symbols": len(existing),
            "symbols": existing
        }

        # Atomically write baseline.json
        tmp_file = self.baseline_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_file.replace(self.baseline_file)

        # If a custom tag was supplied, also write snapshot file
        if tag and tag != "latest":
            tagged_file = self.benchmarks_dir / f"baseline_{tag}.json"
            tagged_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return self.baseline_file

    def seed_from_telemetry(self, store: GraphStore) -> int:
        """Seed benchmark baseline from existing runtime telemetry in GraphStore."""
        telemetry = store.get_all_telemetry()
        if not telemetry:
            return 0

        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)
        existing = self.load_baseline()
        seeded_count = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        for node_id, tel in telemetry.items():
            node = store.get_node(node_id) or {}
            p95 = float(tel.get("p95_duration_ms") or tel.get("avg_duration_ms", 0.0) * 1.5)
            avg = float(tel.get("avg_duration_ms", 0.0))
            calls = int(tel.get("call_count", 1))

            existing[node_id] = {
                "node_id": node_id,
                "name": node.get("name", node_id.split(":")[-1]),
                "path": node.get("path", ""),
                "iterations": calls,
                "p50_ms": avg,
                "p95_ms": p95,
                "p99_ms": p95 * 1.2,
                "avg_ms": avg,
                "throughput_ops_sec": float(calls / max(1.0, tel.get("total_duration_ms", 1000.0) / 1000.0)),
                "peak_memory_bytes": 0,
                "updated_at": now_iso,
                "tag": "telemetry_seed"
            }
            seeded_count += 1

        payload = {
            "version": "1.0.0",
            "tag": "telemetry_seed",
            "updated_at": now_iso,
            "total_symbols": len(existing),
            "symbols": existing
        }

        tmp_file = self.baseline_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_file.replace(self.baseline_file)

        return seeded_count
