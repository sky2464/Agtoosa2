"""Runtime Observability & Telemetry Ingestion Engine (DEV-017 / Stage 17).

Ingests OpenTelemetry (OTLP JSON), profiler traces (Py-Spy, cProfile, flamegraphs),
and generic runtime execution metrics into the Agtoosa knowledge graph. Computes
dynamic hotspot heatmaps for the architecture visualizer and CLI diagnostics.
"""

from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.graph.store import GraphStore


@dataclass
class TelemetryRecord:
    node_id: str
    target_name: str
    call_count: int
    total_duration_ms: float
    avg_duration_ms: float
    p95_duration_ms: float
    error_count: int
    error_rate: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HeatmapNode:
    node_id: str
    name: str
    node_type: str
    path: str
    call_count: int
    avg_duration_ms: float
    error_rate: float
    composite_heat: float  # 0.0 to 1.0
    heat_level: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "COLD"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TelemetryIngester:
    """Ingests runtime spans and profiler traces, mapping them to knowledge graph nodes."""

    def __init__(self, store: GraphStore, workspace_root: Optional[Path] = None):
        self.store = store
        self.workspace_root = workspace_root or Path.cwd()

    def ingest_file(self, file_path: Path, format_hint: Optional[str] = None) -> Dict[str, Any]:
        """Ingest a telemetry or profiler file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Telemetry file not found: {file_path}")

        raw_text = file_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)

        # Detect format if not specified
        fmt = format_hint or self._detect_format(data)
        if fmt == "otel":
            records = self._parse_otel_spans(data)
        elif fmt == "pyspy":
            records = self._parse_pyspy_flamegraph(data)
        else:
            records = self._parse_generic_metrics(data)

        # Upsert into GraphStore
        records_to_save = [r.to_dict() for r in records]
        self.store.save_telemetry_batch(records_to_save)

        return {
            "format": fmt,
            "ingested_records": len(records),
            "records": [r.to_dict() for r in records[:10]],  # preview
        }

    def _detect_format(self, data: Any) -> str:
        """Infer format from JSON structure."""
        if isinstance(data, dict):
            if "resourceSpans" in data or "spans" in data:
                return "otel"
            if "flamebearer" in data or "version" in data and "frames" in data:
                return "pyspy"
            if "metrics" in data:
                return "generic"
        if isinstance(data, list):
            if data and isinstance(data[0], dict) and ("traceId" in data[0] or "spanId" in data[0]):
                return "otel"
            if data and isinstance(data[0], dict) and ("target" in data[0] or "node_id" in data[0]):
                return "generic"
        return "generic"

    def _parse_otel_spans(self, data: Any) -> List[TelemetryRecord]:
        """Extract spans from OpenTelemetry trace data."""
        raw_spans: List[Dict[str, Any]] = []

        if isinstance(data, dict):
            # OTLP ExportTraceServiceRequest structure
            resource_spans = data.get("resourceSpans", [])
            for rs in resource_spans:
                scope_spans = rs.get("scopeSpans", [])
                for ss in scope_spans:
                    raw_spans.extend(ss.get("spans", []))
            if "spans" in data:
                raw_spans.extend(data["spans"])
        elif isinstance(data, list):
            raw_spans = data

        # Aggregate spans by target
        grouped: Dict[str, Dict[str, Any]] = {}

        for span in raw_spans:
            name = span.get("name", "")
            # Check attributes for function/class or code details
            attrs = {}
            for a in span.get("attributes", []):
                if isinstance(a, dict) and "key" in a and "value" in a:
                    val = a["value"]
                    if isinstance(val, dict):
                        val = list(val.values())[0]
                    attrs[a["key"]] = val

            target_hint = attrs.get("code.function") or attrs.get("code.filepath") or name
            resolved_node = self._resolve_target_to_node(target_hint)
            node_id = resolved_node["id"] if resolved_node else f"unmapped:{target_hint}"

            # Calculate duration
            start_nano = int(span.get("startTimeUnixNano", 0))
            end_nano = int(span.get("endTimeUnixNano", 0))
            duration_ms = (end_nano - start_nano) / 1_000_000.0 if (end_nano and start_nano) else float(span.get("durationMs", 1.0))

            # Status code (2 = Error in OTel)
            status = span.get("status", {})
            is_error = status.get("code") == 2 or status.get("code") == "ERROR" or attrs.get("error", False)

            if node_id not in grouped:
                grouped[node_id] = {
                    "node_id": node_id,
                    "target_name": target_hint,
                    "calls": 0,
                    "total_ms": 0.0,
                    "durations": [],
                    "errors": 0,
                    "metadata": {"otel_names": [name]},
                }

            entry = grouped[node_id]
            entry["calls"] += 1
            entry["total_ms"] += duration_ms
            entry["durations"].append(duration_ms)
            if is_error:
                entry["errors"] += 1

        # Build TelemetryRecords
        records: List[TelemetryRecord] = []
        for g in grouped.values():
            calls = g["calls"]
            total_ms = g["total_ms"]
            avg_ms = total_ms / calls if calls > 0 else 0.0
            durations = sorted(g["durations"])
            p95_idx = int(0.95 * len(durations))
            p95_ms = durations[p95_idx] if durations else avg_ms
            errors = g["errors"]
            error_rate = errors / calls if calls > 0 else 0.0

            records.append(
                TelemetryRecord(
                    node_id=g["node_id"],
                    target_name=g["target_name"],
                    call_count=calls,
                    total_duration_ms=total_ms,
                    avg_duration_ms=avg_ms,
                    p95_duration_ms=p95_ms,
                    error_count=errors,
                    error_rate=error_rate,
                    metadata=g["metadata"],
                )
            )

        return records

    def _parse_pyspy_flamegraph(self, data: Dict[str, Any]) -> List[TelemetryRecord]:
        """Extract frame metrics from Py-Spy or speedscope flamegraph JSON."""
        records: List[TelemetryRecord] = []
        # Speedscope / Py-Spy flamebearer format
        frames = data.get("frames", data.get("shared", {}).get("frames", [])) or []
        for frame in frames:
            name = frame.get("name", "")
            file_name = frame.get("file", frame.get("filename", ""))
            line = frame.get("line", 0)

            target_hint = f"{file_name}:{name}" if file_name else name
            resolved_node = self._resolve_target_to_node(target_hint)
            node_id = resolved_node["id"] if resolved_node else f"unmapped:{target_hint}"

            hits = frame.get("hits", frame.get("count", 1))
            self_time = frame.get("selfTime", frame.get("time", 0.0))

            records.append(
                TelemetryRecord(
                    node_id=node_id,
                    target_name=name,
                    call_count=int(hits),
                    total_duration_ms=float(self_time),
                    avg_duration_ms=float(self_time) / hits if hits > 0 else 0.0,
                    p95_duration_ms=float(self_time) / hits * 1.5 if hits > 0 else 0.0,
                    error_count=0,
                    error_rate=0.0,
                    metadata={"file": file_name, "line": line},
                )
            )

        return records

    def _parse_generic_metrics(self, data: Any) -> List[TelemetryRecord]:
        """Extract metrics from generic JSON format."""
        items = data.get("metrics", []) if isinstance(data, dict) else data
        records: List[TelemetryRecord] = []

        for item in items:
            target = item.get("target") or item.get("node_id") or item.get("name", "")
            resolved_node = self._resolve_target_to_node(target)
            node_id = resolved_node["id"] if resolved_node else (item.get("node_id") or f"unmapped:{target}")

            calls = int(item.get("calls", item.get("call_count", 1)))
            total_ms = float(item.get("duration_ms", item.get("total_duration_ms", 0.0)))
            avg_ms = float(item.get("avg_duration_ms", total_ms / calls if calls > 0 else 0.0))
            p95_ms = float(item.get("p95_duration_ms", avg_ms * 1.5))
            errors = int(item.get("errors", item.get("error_count", 0)))
            error_rate = float(item.get("error_rate", errors / calls if calls > 0 else 0.0))

            records.append(
                TelemetryRecord(
                    node_id=node_id,
                    target_name=target,
                    call_count=calls,
                    total_duration_ms=total_ms,
                    avg_duration_ms=avg_ms,
                    p95_duration_ms=p95_ms,
                    error_count=errors,
                    error_rate=error_rate,
                    metadata=item.get("metadata", {}),
                )
            )

        return records

    def _resolve_target_to_node(self, target: str) -> Optional[Dict[str, Any]]:
        """Resolve a function/class name, endpoint, or file path to an existing graph node."""
        if not target:
            return None

        # 1. Exact node_id match
        exact = self.store.get_node(target)
        if exact:
            return exact

        # 2. Match by exact name
        matches = self.store.find_nodes_by_name(target, limit=5)
        if matches:
            # Prefer functions/classes over files
            for m in matches:
                if m.get("node_type") in ("function", "class", "endpoint"):
                    return m
            return matches[0]

        # 3. Clean target (e.g. strip parentheses or route methods)
        clean_target = re.sub(r'\(.*?\)', '', target).strip()
        if " " in clean_target:
            parts = clean_target.split()
            clean_target = parts[-1]  # e.g. "GET /api/users" -> "/api/users"

        matches = self.store.find_nodes_by_name(clean_target, limit=5)
        if matches:
            return matches[0]

        # 4. Search by path suffix
        if "/" in clean_target or "." in clean_target:
            leaf = clean_target.replace("\\", "/").split("/")[-1]
            if ":" in leaf:
                sym_name = leaf.split(":")[-1]
                leaf_matches = self.store.find_nodes_by_name(sym_name, limit=5)
                if leaf_matches:
                    return leaf_matches[0]

        # 5. FTS search fallback
        fts_res = self.store.query_fts(clean_target, limit=3)
        if fts_res:
            top_id = fts_res[0]["id"]
            return self.store.get_node(top_id)

        return None

    def compute_heatmaps(self, top_k: int = 50) -> List[HeatmapNode]:
        """Calculate normalized telemetry heatmaps across all nodes."""
        all_telem = self.store.get_all_telemetry()
        if not all_telem:
            return []

        # Find max calls and max latency for relative scaling
        max_calls = max((t["call_count"] for t in all_telem.values()), default=1) or 1
        max_latency = max((t["avg_duration_ms"] for t in all_telem.values()), default=1.0) or 1.0

        heatmap_nodes: List[HeatmapNode] = []

        for node_id, t in all_telem.items():
            node = self.store.get_node(node_id) or {
                "name": t.get("metadata", {}).get("target_name", node_id),
                "node_type": "unknown",
                "path": ""
            }

            calls = t["call_count"]
            avg_lat = t["avg_duration_ms"]
            err_rate = t["error_rate"]

            # Normalized component scores [0.0, 1.0]
            call_score = min(1.0, calls / max_calls)
            lat_score = min(1.0, avg_lat / max_latency)
            err_score = min(1.0, err_rate)

            # Composite Heat Calculation
            # 50% Call Frequency + 30% Latency + 20% Error Rate
            composite = (0.5 * call_score) + (0.3 * lat_score) + (0.2 * err_score)
            composite = round(composite, 4)

            # Assign Heat Level
            if composite >= 0.75 or err_rate >= 0.20:
                level = "CRITICAL"
            elif composite >= 0.45:
                level = "HIGH"
            elif composite >= 0.20:
                level = "MEDIUM"
            elif composite > 0.0:
                level = "LOW"
            else:
                level = "COLD"

            heatmap_nodes.append(
                HeatmapNode(
                    node_id=node_id,
                    name=node["name"],
                    node_type=node["node_type"],
                    path=node.get("path", ""),
                    call_count=calls,
                    avg_duration_ms=round(avg_lat, 2),
                    error_rate=round(err_rate, 4),
                    composite_heat=composite,
                    heat_level=level,
                )
            )

        # Sort descending by composite heat
        heatmap_nodes.sort(key=lambda x: x.composite_heat, reverse=True)
        return heatmap_nodes[:top_k]
