# Specification: DEV-030 Distributed OpenTelemetry Trace Ingestion & Dynamic Topology

## Status
Implemented / Ready for Verification

## Priority Score
**87 / 100** (Milestone 12 — Ingests OTLP, Jaeger, and Zipkin spans to map true runtime HTTP/gRPC/RPC call topologies directly alongside static AST callgraphs).

## Problem Statement
Static AST analysis provides deep insight into intra-repository function calls, class inheritances, and syntactic dependencies. However, in modern microservices, distributed backends, and multi-service systems:
1. **Network Blindspots**: Service $A$ calling Service $B$ over HTTP or gRPC is completely invisible to static AST parsers because the connection occurs across processes and network interfaces.
2. **Missing Dynamic Telemetry**: Developers cannot determine which remote clients call their endpoints, what the latency distribution ($p50, p95, p99$) looks like across service links, or where cascading network failures originate.
3. **Decoupled Architecture Drift**: As distributed microservices evolve, unexpected cyclic service dependencies (e.g. Service $A \rightarrow B \rightarrow A$) and uninstrumented external dependencies (Stripe, AWS S3) emerge without notice.

## Objectives
1. **Multi-Format Distributed Trace Ingestion Engine (`TraceTopologyEngine`)**:
   - Parse OpenTelemetry v1 `ExportTraceServiceRequest` JSON payloads (`resourceSpans` $\rightarrow$ `scopeSpans` $\rightarrow$ `spans`).
   - Parse Jaeger JSON export format (`data[].spans` with references and processes).
   - Parse Zipkin JSON array format (`[ { id, traceId, parentId, localEndpoint, remoteEndpoint } ]`).
   - Auto-detect format and extract spans, kinds (SERVER, CLIENT, PRODUCER, CONSUMER, INTERNAL), durations, statuses, and RPC/HTTP/DB attributes.
2. **Dynamic Runtime Service Topology Reconstruction**:
   - Reconstruct parent-child span hierarchies across service boundaries.
   - Extract `NodeType.SERVICE` nodes (`service:<service_name>`) and directed `EdgeType.NETWORK_CALLS` edges.
   - Calculate link-level statistics: `call_count`, `avg_duration_ms`, `p50_duration_ms`, `p95_duration_ms`, `p99_duration_ms`, `error_count`, `error_rate`, and `protocols`.
3. **AST & Endpoint Stitching**:
   - Cross-reference server spans with local AST `Endpoint` (DEV-025) and `Function` nodes.
   - Create direct `network_calls` edges from caller services to codebase endpoint nodes.
   - Update `runtime_telemetry` for stitched AST nodes.
4. **Topology Query & Diagnostics (`query_topology`)**:
   - Retrieve service dependency graph, incoming callers, and outgoing dependencies.
   - Identify performance bottlenecks ($p95 \ge 300\text{ms}$).
   - Detect network error hotspots (error rate $\ge 5\%$ or errors present).
   - Detect circular service dependencies ($A \leftrightarrow B$).
5. **Developer & Agent Surfaces**:
   - CLI: `agtoosa telemetry traces <file> [--format otel|jaeger|zipkin] [--no-stitch] [--json]`.
   - CLI: `agtoosa graph topology [--service <name>] [--json]`.
   - MCP Tool: `agtoosa_get_service_topology` providing LLM agents with live distributed service architecture.

## Architecture

```
[ Distributed Trace Payload ] (OTLP JSON / Jaeger / Zipkin)
              │
              ▼
    [ TraceTopologyEngine ]
    ┌─────────┴────────────────────────────┐
    │ 1. Multi-format Span Parser          │
    │ 2. Cross-Service Hierarchy Resolver   │
    │ 3. AST Endpoint Stitching (DEV-025)  │
    │ 4. Latency Percentile Calculator     │
    └─────────┬────────────────────────────┘
              │
              ▼
   [ SQLite Knowledge Graph ]
   ├── Nodes: NodeType.SERVICE (service:<name>)
   ├── Edges: EdgeType.NETWORK_CALLS (p50, p95, error_rate)
   └── Stitched AST Endpoints + runtime_telemetry
              │
              ├─► CLI: agtoosa graph topology / agtoosa telemetry traces
              ├─► MCP: agtoosa_get_service_topology
              └─► Studio: Visualizer Service Domain & Network Edges
```
