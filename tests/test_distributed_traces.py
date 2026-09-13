"""Automated test suite for DEV-030: Distributed OpenTelemetry Trace Ingestion & Dynamic Topology."""

import argparse
import json
from pathlib import Path
import tempfile
import unittest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.query import query_topology
from agtoosa.observability.traces import TraceTopologyEngine, TraceSpan
from agtoosa.cli.observability_cmd import cmd_telemetry
from agtoosa.cli.graph_cmd import cmd_graph_topology
from agtoosa.mcp.server import MCPServer


class TestDistributedTraceTopology(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.db_path = self.workspace / ".agtoosa" / "graph.db"
        self.store = GraphStore(self.db_path)
        self.engine = TraceTopologyEngine(self.store, self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_otlp_traces(self):
        """Test parsing standard OTLP JSON and reconstructing service topology with percentiles."""
        otlp_payload = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "api-gateway"}}
                        ]
                    },
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "trace1",
                                    "spanId": "span-gw-1",
                                    "name": "GET /checkout",
                                    "kind": 2,  # SERVER
                                    "startTimeUnixNano": 1000000000,
                                    "endTimeUnixNano": 1050000000,  # 50ms
                                    "attributes": [
                                        {"key": "http.method", "value": {"stringValue": "GET"}},
                                        {"key": "http.route", "value": {"stringValue": "/checkout"}}
                                    ]
                                },
                                {
                                    "traceId": "trace1",
                                    "spanId": "span-gw-call-order",
                                    "parentSpanId": "span-gw-1",
                                    "name": "OrderService.CreateOrder",
                                    "kind": 3,  # CLIENT
                                    "startTimeUnixNano": 1010000000,
                                    "endTimeUnixNano": 1045000000,  # 35ms
                                    "attributes": [
                                        {"key": "rpc.service", "value": {"stringValue": "OrderService"}}
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "order-service"}}
                        ]
                    },
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "trace1",
                                    "spanId": "span-order-srv",
                                    "parentSpanId": "span-gw-call-order",
                                    "name": "OrderService.CreateOrder",
                                    "kind": 2,  # SERVER
                                    "startTimeUnixNano": 1012000000,
                                    "endTimeUnixNano": 1043000000,  # 31ms
                                    "attributes": [
                                        {"key": "rpc.service", "value": {"stringValue": "OrderService"}}
                                    ]
                                },
                                {
                                    "traceId": "trace1",
                                    "spanId": "span-order-call-pay",
                                    "parentSpanId": "span-order-srv",
                                    "name": "POST /pay",
                                    "kind": 3,  # CLIENT
                                    "startTimeUnixNano": 1015000000,
                                    "endTimeUnixNano": 1040000000,  # 25ms
                                    "attributes": [
                                        {"key": "peer.service", "value": {"stringValue": "payment-service"}},
                                        {"key": "http.method", "value": {"stringValue": "POST"}}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        trace_file = self.workspace / "otlp.json"
        trace_file.write_text(json.dumps(otlp_payload), encoding="utf-8")

        res = self.engine.ingest_file(trace_file)
        self.assertEqual(res["format"], "otel")
        self.assertEqual(res["total_spans"], 4)
        self.assertGreaterEqual(res["services_discovered"], 3)

        # Check in SQLite
        svc_gw = self.store.get_node("service:api-gateway")
        self.assertNotNull = self.assertIsNotNone
        self.assertIsNotNone(svc_gw)
        self.assertEqual(svc_gw["node_type"], "service")

        svc_order = self.store.get_node("service:order-service")
        self.assertIsNotNone(svc_order)

        svc_pay = self.store.get_node("service:payment-service")
        self.assertIsNotNone(svc_pay)

        # Check topology query
        topo = query_topology(self.store)
        self.assertGreaterEqual(topo["total_services"], 3)
        self.assertGreaterEqual(topo["total_network_edges"], 2)

    def test_parse_jaeger_traces(self):
        """Test parsing Jaeger JSON export with process references."""
        jaeger_payload = {
            "data": [
                {
                    "traceID": "jaeger-trace-101",
                    "processes": {
                        "p1": {"serviceName": "frontend-ui"},
                        "p2": {"serviceName": "inventory-api"}
                    },
                    "spans": [
                        {
                            "traceID": "jaeger-trace-101",
                            "spanID": "sp-front",
                            "processID": "p1",
                            "operationName": "RenderCatalog",
                            "duration": 50000,  # 50ms
                            "tags": [
                                {"key": "span.kind", "value": "client"}
                            ],
                            "references": []
                        },
                        {
                            "traceID": "jaeger-trace-101",
                            "spanID": "sp-inv",
                            "processID": "p2",
                            "operationName": "GetStock",
                            "duration": 35000,  # 35ms
                            "tags": [
                                {"key": "span.kind", "value": "server"},
                                {"key": "http.route", "value": "/items"}
                            ],
                            "references": [
                                {"refType": "CHILD_OF", "spanID": "sp-front"}
                            ]
                        }
                    ]
                }
            ]
        }

        trace_file = self.workspace / "jaeger.json"
        trace_file.write_text(json.dumps(jaeger_payload), encoding="utf-8")

        res = self.engine.ingest_file(trace_file)
        self.assertEqual(res["format"], "jaeger")
        self.assertEqual(res["total_spans"], 2)

        topo = query_topology(self.store)
        svc_names = {s["name"] for s in topo["services"]}
        self.assertIn("frontend-ui", svc_names)
        self.assertIn("inventory-api", svc_names)

    def test_parse_zipkin_traces(self):
        """Test parsing Zipkin JSON array payload."""
        zipkin_payload = [
            {
                "traceId": "zipkin-trace-99",
                "id": "zk-root",
                "name": "search",
                "duration": 80000,  # 80ms
                "localEndpoint": {"serviceName": "search-service"}
            },
            {
                "traceId": "zipkin-trace-99",
                "id": "zk-child",
                "parentId": "zk-root",
                "name": "lookup_es",
                "duration": 40000,  # 40ms
                "localEndpoint": {"serviceName": "elasticsearch-proxy"},
                "remoteEndpoint": {"serviceName": "es-cluster"}
            }
        ]

        trace_file = self.workspace / "zipkin.json"
        trace_file.write_text(json.dumps(zipkin_payload), encoding="utf-8")

        res = self.engine.ingest_file(trace_file)
        self.assertEqual(res["format"], "zipkin")
        self.assertEqual(res["total_spans"], 2)

        topo = query_topology(self.store)
        svc_names = {s["name"] for s in topo["services"]}
        self.assertIn("search-service", svc_names)
        self.assertIn("elasticsearch-proxy", svc_names)

    def test_ast_endpoint_stitching_and_telemetry(self):
        """Test stitching runtime server spans to static AST Endpoint nodes."""
        # 1. Pre-populate an AST Endpoint node into knowledge graph (from DEV-025)
        ep = Node(
            id="endpoint:app/routes.py:post_checkout",
            name="checkout",
            node_type=NodeType.ENDPOINT,
            path="app/routes.py",
            start_line=25,
            end_line=45,
            metadata={
                "http_method": "POST",
                "path": "/api/v1/checkout",
                "framework": "fastapi"
            }
        )
        self.store.insert_batch([ep], [])

        # 2. Ingest trace containing client calling /api/v1/checkout
        trace_payload = {
            "resourceSpans": [
                {
                    "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "mobile-app"}}]},
                    "scopeSpans": [{"spans": [
                        {
                            "traceId": "tr-stitch",
                            "spanId": "sp-mobile-req",
                            "name": "POST /api/v1/checkout",
                            "kind": 3,  # CLIENT
                            "startTimeUnixNano": 1000000000,
                            "endTimeUnixNano": 1120000000
                        }
                    ]}]
                },
                {
                    "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "backend-api"}}]},
                    "scopeSpans": [{"spans": [
                        {
                            "traceId": "tr-stitch",
                            "spanId": "sp-backend-srv",
                            "parentSpanId": "sp-mobile-req",
                            "name": "POST /api/v1/checkout",
                            "kind": 2,  # SERVER
                            "startTimeUnixNano": 1005000000,
                            "endTimeUnixNano": 1115000000,  # 110ms
                            "attributes": [
                                {"key": "http.method", "value": {"stringValue": "POST"}},
                                {"key": "http.route", "value": {"stringValue": "/api/v1/checkout"}}
                            ]
                        }
                    ]}]
                }
            ]
        }

        trace_file = self.workspace / "stitch_trace.json"
        trace_file.write_text(json.dumps(trace_payload), encoding="utf-8")

        res = self.engine.ingest_file(trace_file, stitch_ast=True)
        self.assertEqual(res["stitched_ast_endpoints"], 1)
        self.assertEqual(res["topology"]["stitched_endpoints"][0]["id"], ep.id)

        # Verify edge exists from service:mobile-app directly to endpoint:app/routes.py:post_checkout
        neighbors = self.store.get_neighbors(ep.id, direction="in")
        caller_ids = [n["id"] for n in neighbors]
        self.assertIn("service:mobile-app", caller_ids)

        # Verify runtime_telemetry was recorded for the endpoint
        telem = self.store.get_telemetry_for_node(ep.id)
        self.assertIsNotNone(telem)
        self.assertEqual(telem["call_count"], 1)
        self.assertEqual(telem["avg_duration_ms"], 110.0)

    def test_query_topology_bottlenecks_and_cycles(self):
        """Test diagnostics for latency bottlenecks, errors, and circular network dependencies."""
        s_a = Node(id="service:auth-svc", name="auth-svc", node_type=NodeType.SERVICE, path="runtime://services/auth-svc")
        s_b = Node(id="service:billing-svc", name="billing-svc", node_type=NodeType.SERVICE, path="runtime://services/billing-svc")

        # Edge A -> B (slow bottleneck with p95 = 450ms)
        e_ab = Edge(
            source_id=s_a.id,
            target_id=s_b.id,
            edge_type=EdgeType.NETWORK_CALLS,
            provenance="otel_trace",
            metadata={
                "call_count": 500,
                "avg_duration_ms": 320.0,
                "p95_duration_ms": 450.0,
                "error_count": 25,
                "error_rate": 0.05,
                "protocols": ["http"]
            }
        )

        # Edge B -> A (creates circular network dependency!)
        e_ba = Edge(
            source_id=s_b.id,
            target_id=s_a.id,
            edge_type=EdgeType.NETWORK_CALLS,
            provenance="otel_trace",
            metadata={
                "call_count": 120,
                "avg_duration_ms": 40.0,
                "p95_duration_ms": 65.0,
                "error_count": 0,
                "error_rate": 0.0,
                "protocols": ["grpc"]
            }
        )

        self.store.insert_batch([s_a, s_b], [e_ab, e_ba])

        topo = query_topology(self.store)
        self.assertEqual(len(topo["bottlenecks"]), 1)
        self.assertEqual(topo["bottlenecks"][0]["source_id"], "service:auth-svc")

        self.assertEqual(len(topo["error_hotspots"]), 1)
        self.assertEqual(topo["error_hotspots"][0]["error_count"], 25)

        self.assertEqual(len(topo["circular_dependencies"]), 1)
        self.assertIn("auth-svc", topo["circular_dependencies"][0]["service_a"])

    def test_cli_traces_and_topology(self):
        """Test CLI subcommands 'agtoosa telemetry traces' and 'agtoosa graph topology'."""
        trace_file = self.workspace / "cli_traces.json"
        trace_file.write_text(json.dumps([
            {
                "traceId": "cli-trace-1",
                "id": "c1",
                "name": "login",
                "duration": 25000,
                "localEndpoint": {"serviceName": "web-client"}
            },
            {
                "traceId": "cli-trace-1",
                "id": "c2",
                "parentId": "c1",
                "name": "verify",
                "duration": 15000,
                "localEndpoint": {"serviceName": "auth-backend"}
            }
        ]), encoding="utf-8")

        # 1. Ingest via CLI
        args_ingest = argparse.Namespace(
            command="telemetry",
            telem_action="traces",
            file=str(trace_file),
            format="zipkin",
            no_stitch=True,
            json=True
        )
        rc_ingest = cmd_telemetry(args_ingest, self.workspace)
        self.assertEqual(rc_ingest, 0)

        # 2. Query via CLI
        args_topo = argparse.Namespace(
            command="graph",
            graph_action="topology",
            service=None,
            json=True
        )
        rc_topo = cmd_graph_topology(args_topo, self.workspace)
        self.assertEqual(rc_topo, 0)

    def test_mcp_service_topology_tool(self):
        """Test MCPServer tool 'agtoosa_get_service_topology'."""
        server = MCPServer(self.workspace)
        tool_defs = server.get_tool_definitions()
        topo_tool = next((t for t in tool_defs if t["name"] == "agtoosa_get_service_topology"), None)
        self.assertIsNotNone(topo_tool)

        # Seed service
        s = Node(id="service:catalog-svc", name="catalog-svc", node_type=NodeType.SERVICE, path="runtime://services/catalog-svc")
        self.store.insert_batch([s], [])

        res_json = server.handle_tool_call("agtoosa_get_service_topology", {"service": "catalog-svc"})
        data = json.loads(res_json)
        self.assertIn("services", data)
        self.assertEqual(len(data["services"]), 1)
        self.assertEqual(data["services"][0]["name"], "catalog-svc")


if __name__ == "__main__":
    unittest.main()
