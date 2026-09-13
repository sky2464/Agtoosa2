"""Distributed OpenTelemetry Trace Ingestion & Dynamic Topology Engine (DEV-030).

Ingests distributed traces (OTLP JSON, Jaeger, Zipkin) into the knowledge graph
to construct dynamic runtime service topologies, cross-service RPC/HTTP call paths,
latency percentiles, and network-level dependencies directly connected with static AST endpoints.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.query import query_routes


@dataclass
class TraceSpan:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    service_name: str
    name: str
    kind: str  # "SERVER", "CLIENT", "PRODUCER", "CONSUMER", "INTERNAL", "UNKNOWN"
    duration_ms: float
    is_error: bool
    http_method: Optional[str] = None
    http_route: Optional[str] = None
    http_status: Optional[int] = None
    rpc_service: Optional[str] = None
    rpc_method: Optional[str] = None
    db_system: Optional[str] = None
    db_statement: Optional[str] = None
    peer_service: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _percentile(values: List[float], p: float) -> float:
    """Calculate percentile from a sorted list of float values (0 <= p <= 1.0)."""
    if not values:
        return 0.0
    k = (len(values) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[f]
    d0 = values[f] * (c - k)
    d1 = values[c] * (k - f)
    return d0 + d1


class TraceTopologyEngine:
    """Parses distributed traces and reconstructs dynamic runtime service topologies."""

    def __init__(self, store: GraphStore, workspace_root: Optional[Path] = None):
        self.store = store
        self.workspace_root = workspace_root or Path.cwd()

    def ingest_file(
        self,
        file_path: Path,
        format_hint: Optional[str] = None,
        stitch_ast: bool = True
    ) -> Dict[str, Any]:
        """Ingest a trace file into the knowledge graph."""
        if not file_path.exists():
            raise FileNotFoundError(f"Trace file not found: {file_path}")

        raw_text = file_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)

        fmt = format_hint or self.detect_format(data)
        spans = self.parse_traces(data, format_hint=fmt)
        topology = self.build_topology(spans, stitch_ast=stitch_ast)

        return {
            "format": fmt,
            "total_spans": len(spans),
            "services_discovered": len(topology["services"]),
            "network_edges_created": len(topology["edges"]),
            "stitched_ast_endpoints": len(topology["stitched_endpoints"]),
            "topology": topology
        }

    def detect_format(self, data: Any) -> str:
        """Detect whether input is OTLP JSON, Jaeger, or Zipkin."""
        if isinstance(data, dict):
            if "resourceSpans" in data or "scopeSpans" in data:
                return "otel"
            if "data" in data and isinstance(data["data"], list):
                if data["data"] and "spans" in data["data"][0]:
                    return "jaeger"
            if "spans" in data:
                return "otel"
        elif isinstance(data, list):
            if data and isinstance(data[0], dict):
                first = data[0]
                if "localEndpoint" in first or ("parentId" in first and "traceId" in first):
                    return "zipkin"
                if "traceID" in first and "spanID" in first:
                    return "jaeger"
                if "traceId" in first and "spanId" in first:
                    return "otel"
        return "otel"

    def parse_traces(self, data: Any, format_hint: Optional[str] = None) -> List[TraceSpan]:
        """Parse raw trace payload into normalized TraceSpan objects."""
        fmt = format_hint or self.detect_format(data)
        if fmt == "jaeger":
            return self._parse_jaeger(data)
        elif fmt == "zipkin":
            return self._parse_zipkin(data)
        else:
            return self._parse_otlp(data)

    def _extract_attr_val(self, val: Any) -> Any:
        """Extract value from OTLP AnyValue structure or plain value."""
        if isinstance(val, dict):
            for k in ("stringValue", "intValue", "boolValue", "doubleValue"):
                if k in val:
                    return val[k]
            if "arrayValue" in val:
                return [self._extract_attr_val(v) for v in val["arrayValue"].get("values", [])]
            if "kvlistValue" in val:
                return {kv["key"]: self._extract_attr_val(kv.get("value")) for kv in val["kvlistValue"].get("values", [])}
            return list(val.values())[0] if val else None
        return val

    def _normalize_span_kind(self, raw_kind: Any) -> str:
        """Map OTLP/Jaeger span kinds to canonical strings."""
        if isinstance(raw_kind, int):
            mapping = {
                1: "INTERNAL",
                2: "SERVER",
                3: "CLIENT",
                4: "PRODUCER",
                5: "CONSUMER"
            }
            return mapping.get(raw_kind, "UNKNOWN")
        if isinstance(raw_kind, str):
            k = raw_kind.upper()
            if "SERVER" in k:
                return "SERVER"
            if "CLIENT" in k:
                return "CLIENT"
            if "PROD" in k:
                return "PRODUCER"
            if "CONS" in k:
                return "CONSUMER"
            if "INT" in k:
                return "INTERNAL"
        return "UNKNOWN"

    def _parse_otlp(self, data: Any) -> List[TraceSpan]:
        """Extract spans from OpenTelemetry v1 ExportTraceServiceRequest JSON."""
        spans: List[TraceSpan] = []

        raw_resource_spans = []
        if isinstance(data, dict):
            raw_resource_spans = data.get("resourceSpans", [])
            if not raw_resource_spans and "spans" in data:
                raw_resource_spans = [{"scopeSpans": [{"spans": data["spans"]}]}]
        elif isinstance(data, list):
            raw_resource_spans = [{"scopeSpans": [{"spans": data}]}]

        for rs in raw_resource_spans:
            # Extract service name from resource attributes
            service_name = "unknown-service"
            resource = rs.get("resource", {}) if isinstance(rs, dict) else {}
            resource_attrs: List[Any] = []
            if isinstance(resource, dict):
                resource_attrs = resource.get("attributes", [])
            elif isinstance(resource, list):
                resource_attrs = resource

            for attr in resource_attrs:
                if isinstance(attr, dict):
                    key = attr.get("key")
                    if key in ("service.name", "service_name"):
                        service_name = str(self._extract_attr_val(attr.get("value", "")))

            for ss in rs.get("scopeSpans", []):
                for s in ss.get("spans", []):
                    trace_id = s.get("traceId", "")
                    span_id = s.get("spanId", "")
                    parent_span_id = s.get("parentSpanId") or None
                    name = s.get("name", "unnamed-span")
                    kind = self._normalize_span_kind(s.get("kind", 0))

                    # Duration calculation
                    start_nano = int(s.get("startTimeUnixNano", 0))
                    end_nano = int(s.get("endTimeUnixNano", 0))
                    duration_ms = (end_nano - start_nano) / 1_000_000.0 if (end_nano and start_nano) else float(s.get("durationMs", 1.0))

                    # Parse attributes
                    attrs: Dict[str, Any] = {}
                    for a in s.get("attributes", []):
                        attrs[a["key"]] = self._extract_attr_val(a.get("value"))

                    # If service.name is overridden at span level
                    local_service = attrs.get("service.name") or service_name

                    # Error status
                    status = s.get("status", {})
                    is_error = status.get("code") == 2 or str(status.get("code")).upper() == "ERROR" or attrs.get("error", False)

                    spans.append(
                        TraceSpan(
                            trace_id=trace_id,
                            span_id=span_id,
                            parent_span_id=parent_span_id,
                            service_name=str(local_service),
                            name=name,
                            kind=kind,
                            duration_ms=round(duration_ms, 3),
                            is_error=bool(is_error),
                            http_method=attrs.get("http.method") or attrs.get("http.request.method"),
                            http_route=attrs.get("http.route") or attrs.get("http.target"),
                            http_status=int(attrs["http.status_code"]) if "http.status_code" in attrs else None,
                            rpc_service=attrs.get("rpc.service"),
                            rpc_method=attrs.get("rpc.method"),
                            db_system=attrs.get("db.system"),
                            db_statement=attrs.get("db.statement"),
                            peer_service=attrs.get("peer.service") or attrs.get("net.peer.name"),
                            attributes=attrs
                        )
                    )

        return spans

    def _parse_jaeger(self, data: Any) -> List[TraceSpan]:
        """Extract spans from Jaeger JSON export format."""
        spans: List[TraceSpan] = []

        traces_data = data.get("data", []) if isinstance(data, dict) else data
        for tr in traces_data:
            processes = tr.get("processes", {})
            for s in tr.get("spans", []):
                trace_id = s.get("traceID", "")
                span_id = s.get("spanID", "")

                # Parent resolution from references
                parent_span_id = None
                for ref in s.get("references", []):
                    if ref.get("refType") == "CHILD_OF":
                        parent_span_id = ref.get("spanID")
                        break

                proc_id = s.get("processID", "")
                proc = processes.get(proc_id, {})
                service_name = proc.get("serviceName", "unknown-service")

                duration_micro = s.get("duration", 1000)
                duration_ms = duration_micro / 1000.0

                tags: Dict[str, Any] = {}
                for t in s.get("tags", []):
                    tags[t["key"]] = t.get("value")

                kind = self._normalize_span_kind(tags.get("span.kind", "UNKNOWN"))
                is_error = bool(tags.get("error", False))

                spans.append(
                    TraceSpan(
                        trace_id=trace_id,
                        span_id=span_id,
                        parent_span_id=parent_span_id,
                        service_name=service_name,
                        name=s.get("operationName", "unnamed-span"),
                        kind=kind,
                        duration_ms=round(duration_ms, 3),
                        is_error=is_error,
                        http_method=tags.get("http.method"),
                        http_route=tags.get("http.route") or tags.get("http.url") or tags.get("http.target"),
                        http_status=int(tags["http.status_code"]) if "http.status_code" in tags else None,
                        rpc_service=tags.get("rpc.service"),
                        rpc_method=tags.get("rpc.method"),
                        db_system=tags.get("db.system"),
                        db_statement=tags.get("db.statement"),
                        peer_service=tags.get("peer.service") or tags.get("net.peer.name"),
                        attributes=tags
                    )
                )

        return spans

    def _parse_zipkin(self, data: Any) -> List[TraceSpan]:
        """Extract spans from Zipkin JSON array format."""
        spans: List[TraceSpan] = []
        raw_list = data if isinstance(data, list) else data.get("spans", [])

        for s in raw_list:
            trace_id = s.get("traceId", "")
            span_id = s.get("id", "")
            parent_span_id = s.get("parentId")

            local_ep = s.get("localEndpoint", {})
            service_name = local_ep.get("serviceName", "unknown-service")

            duration_micro = s.get("duration", 1000)
            duration_ms = duration_micro / 1000.0

            tags = s.get("tags", {})
            kind = self._normalize_span_kind(s.get("kind", "UNKNOWN"))
            is_error = "error" in tags or str(tags.get("error")).lower() == "true"

            remote_ep = s.get("remoteEndpoint", {})
            peer_service = remote_ep.get("serviceName") or tags.get("peer.service")

            spans.append(
                TraceSpan(
                    trace_id=trace_id,
                    span_id=span_id,
                    parent_span_id=parent_span_id,
                    service_name=service_name,
                    name=s.get("name", "unnamed-span"),
                    kind=kind,
                    duration_ms=round(duration_ms, 3),
                    is_error=is_error,
                    http_method=tags.get("http.method"),
                    http_route=tags.get("http.route") or tags.get("http.url"),
                    http_status=int(tags["http.status_code"]) if "http.status_code" in tags else None,
                    rpc_service=tags.get("rpc.service"),
                    rpc_method=tags.get("rpc.method"),
                    db_system=tags.get("db.system"),
                    db_statement=tags.get("db.statement"),
                    peer_service=peer_service,
                    attributes=tags
                )
            )

        return spans

    def build_topology(self, spans: List[TraceSpan], stitch_ast: bool = True) -> Dict[str, Any]:
        """Reconstruct cross-service network edges, latency percentiles, and link AST endpoints."""
        span_map: Dict[str, TraceSpan] = {s.span_id: s for s in spans}
        services_set: Set[str] = set()

        # Collect routes from AST for stitching if requested
        ast_routes = query_routes(self.store) if stitch_ast else []
        stitched_endpoints: Dict[str, Dict[str, Any]] = {}
        telemetry_records: Dict[str, Dict[str, Any]] = {}

        # Cross-service edge aggregator: (source_id, target_id) -> metrics
        # source_id / target_id can be "service:<name>" or "endpoint:<id>"
        network_links: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for span in spans:
            services_set.add(span.service_name)
            src_service_id = f"service:{span.service_name}"

            # 1. Parent-child linking across service boundaries
            if span.parent_span_id and span.parent_span_id in span_map:
                parent = span_map[span.parent_span_id]
                if parent.service_name != span.service_name:
                    services_set.add(parent.service_name)
                    parent_svc_id = f"service:{parent.service_name}"

                    link_key = (parent_svc_id, src_service_id)
                    if link_key not in network_links:
                        network_links[link_key] = {
                            "calls": 0,
                            "durations": [],
                            "errors": 0,
                            "protocols": set(),
                            "operations": set()
                        }
                    link = network_links[link_key]
                    link["calls"] += 1
                    link["durations"].append(span.duration_ms)
                    if span.is_error:
                        link["errors"] += 1
                    link["operations"].add(span.name)
                    if span.http_method:
                        link["protocols"].add("http")
                    elif span.rpc_service:
                        link["protocols"].add("grpc")
                    else:
                        link["protocols"].add("rpc")

            # 2. Peer service calls (e.g. client span calling downstream external/uninstrumented service)
            if span.peer_service and span.peer_service != span.service_name:
                peer_svc_id = f"service:{span.peer_service}"
                services_set.add(span.peer_service)

                link_key = (src_service_id, peer_svc_id)
                if link_key not in network_links:
                    network_links[link_key] = {
                        "calls": 0,
                        "durations": [],
                        "errors": 0,
                        "protocols": set(),
                        "operations": set()
                    }
                link = network_links[link_key]
                link["calls"] += 1
                link["durations"].append(span.duration_ms)
                if span.is_error:
                    link["errors"] += 1
                link["operations"].add(span.name)
                if span.db_system:
                    link["protocols"].add(f"db:{span.db_system}")
                elif span.http_method:
                    link["protocols"].add("http")
                else:
                    link["protocols"].add("network")

            # 3. Stitch server spans to local codebase AST Endpoint nodes
            if stitch_ast and (span.kind == "SERVER" or span.http_route or span.http_method):
                matching_endpoint = self._find_matching_ast_route(span, ast_routes)
                if matching_endpoint:
                    ep_id = matching_endpoint["id"]
                    stitched_endpoints[ep_id] = matching_endpoint

                    # If this server span had a caller parent in another service, link directly
                    caller_service_id = src_service_id
                    if span.parent_span_id and span.parent_span_id in span_map:
                        p = span_map[span.parent_span_id]
                        if p.service_name != span.service_name:
                            caller_service_id = f"service:{p.service_name}"

                    ep_link_key = (caller_service_id, ep_id)
                    if ep_link_key not in network_links:
                        network_links[ep_link_key] = {
                            "calls": 0,
                            "durations": [],
                            "errors": 0,
                            "protocols": {"http"},
                            "operations": set()
                        }
                    ep_link = network_links[ep_link_key]
                    ep_link["calls"] += 1
                    ep_link["durations"].append(span.duration_ms)
                    if span.is_error:
                        ep_link["errors"] += 1
                    ep_link["operations"].add(f"{span.http_method or 'GET'} {matching_endpoint['path']}")

                    # Collect runtime telemetry for the endpoint node
                    if ep_id not in telemetry_records:
                        telemetry_records[ep_id] = {
                            "node_id": ep_id,
                            "target_name": matching_endpoint["path"],
                            "call_count": 0,
                            "total_duration_ms": 0.0,
                            "durations": [],
                            "error_count": 0
                        }
                    tr = telemetry_records[ep_id]
                    tr["call_count"] += 1
                    tr["total_duration_ms"] += span.duration_ms
                    tr["durations"].append(span.duration_ms)
                    if span.is_error:
                        tr["error_count"] += 1

        # Create Service Nodes
        service_nodes: List[Node] = []
        for svc in sorted(services_set):
            svc_id = f"service:{svc}"
            # Compute ingress and egress counts
            ingress = sum(1 for (s, t) in network_links.keys() if t == svc_id)
            egress = sum(1 for (s, t) in network_links.keys() if s == svc_id)
            meta = {
                "service_name": svc,
                "ingress_connections": ingress,
                "egress_connections": egress,
                "provenance": "otel_trace"
            }
            service_nodes.append(
                Node(
                    id=svc_id,
                    name=svc,
                    node_type=NodeType.SERVICE,
                    path=f"runtime://services/{svc}",
                    docstring=f"Runtime service: {svc}",
                    metadata=meta
                )
            )

        # Create Network Call Edges
        network_edges: List[Edge] = []
        for (src_id, tgt_id), link_data in network_links.items():
            calls = link_data["calls"]
            durations = sorted(link_data["durations"])
            total_ms = sum(durations)
            avg_ms = total_ms / calls if calls > 0 else 0.0
            p50_ms = _percentile(durations, 0.50)
            p95_ms = _percentile(durations, 0.95)
            p99_ms = _percentile(durations, 0.99)
            errors = link_data["errors"]
            error_rate = errors / calls if calls > 0 else 0.0

            edge_meta = {
                "call_count": calls,
                "total_duration_ms": round(total_ms, 2),
                "avg_duration_ms": round(avg_ms, 2),
                "p50_duration_ms": round(p50_ms, 2),
                "p95_duration_ms": round(p95_ms, 2),
                "p99_duration_ms": round(p99_ms, 2),
                "error_count": errors,
                "error_rate": round(error_rate, 4),
                "protocols": sorted(list(link_data["protocols"])),
                "operations": sorted(list(link_data["operations"]))[:10]
            }

            network_edges.append(
                Edge(
                    source_id=src_id,
                    target_id=tgt_id,
                    edge_type=EdgeType.NETWORK_CALLS,
                    provenance="otel_trace",
                    metadata=edge_meta
                )
            )

        # Insert Service Nodes and Network Edges into SQLite
        self.store.insert_batch(service_nodes, network_edges)

        # Update runtime telemetry for stitched endpoints
        if telemetry_records:
            batch_telemetry = []
            for tr in telemetry_records.values():
                c = tr["call_count"]
                d = sorted(tr["durations"])
                avg_dur = tr["total_duration_ms"] / c if c > 0 else 0.0
                p95_dur = _percentile(d, 0.95)
                errs = tr["error_count"]
                batch_telemetry.append({
                    "node_id": tr["node_id"],
                    "target_name": tr["target_name"],
                    "call_count": c,
                    "total_duration_ms": tr["total_duration_ms"],
                    "avg_duration_ms": round(avg_dur, 2),
                    "p95_duration_ms": round(p95_dur, 2),
                    "error_count": errs,
                    "error_rate": round(errs / c if c > 0 else 0.0, 4),
                    "metadata": {"source": "otel_traces"}
                })
            self.store.save_telemetry_batch(batch_telemetry)

        return {
            "services": [asdict(n) for n in service_nodes],
            "edges": [asdict(e) for e in network_edges],
            "stitched_endpoints": list(stitched_endpoints.values()),
            "total_calls": sum(link["calls"] for link in network_links.values())
        }

    def _find_matching_ast_route(
        self,
        span: TraceSpan,
        ast_routes: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Match an incoming HTTP server span to an existing AST route node."""
        if not ast_routes:
            return None

        span_route = span.http_route or ""
        span_method = (span.http_method or "").upper()

        # If span name is "POST /users"
        if not span_route and " " in span.name:
            parts = span.name.split()
            if parts[0].upper() in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
                span_method = parts[0].upper()
                span_route = parts[1]

        clean_span_route = re.sub(r'\{.*?\}|:\w+', '*', span_route).rstrip('/') or '/'

        for r in ast_routes:
            r_method = (r.get("http_method") or "").upper()
            r_path = (r.get("path") or "").rstrip('/') or '/'
            clean_r_path = re.sub(r'\{.*?\}|:\w+', '*', r_path)

            if span_method and r_method and span_method != r_method:
                continue

            if clean_span_route == clean_r_path or span_route.rstrip('/') == r_path:
                return r

        return None
