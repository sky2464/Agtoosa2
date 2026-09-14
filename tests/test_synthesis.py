"""Tests for DEV-039: Autonomous Cross-Language Microservice Synthesis."""

import json
from pathlib import Path
import tempfile
import unittest

from agtoosa.core.model import Node, NodeType
from agtoosa.graph.store import GraphStore
from agtoosa.federation.synthesis import MicroserviceSynthesizer
from agtoosa.mcp.server import MCPServer
from agtoosa.cli.main import main


class TestMicroserviceSynthesis(unittest.TestCase):
    """Test suite for autonomous cross-language microservice synthesis."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_root = Path(self.temp_dir.name)
        self.db_path = self.workspace_root / "test_graph.db"
        self.store = GraphStore(self.db_path)
        self.synthesizer = MicroserviceSynthesizer(self.store, self.workspace_root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _seed_endpoints_and_schemas(self):
        """Seed sample REST endpoints and data models."""
        nodes = [
            Node(
                id="endpoint:GET:/api/v1/users/{id}",
                name="get_user",
                node_type=NodeType.FUNCTION,
                path="app/routes/users.py",
                docstring="Retrieve user details by identifier.",
                metadata={
                    "kind": "rest_endpoint",
                    "protocol": "rest",
                    "method": "GET",
                    "route": "/api/v1/users/{id}",
                    "repo": "user_service"
                }
            ),
            Node(
                id="endpoint:POST:/api/v1/users",
                name="create_user",
                node_type=NodeType.FUNCTION,
                path="app/routes/users.py",
                docstring="Create a new user record.",
                metadata={
                    "kind": "rest_endpoint",
                    "protocol": "rest",
                    "method": "POST",
                    "route": "/api/v1/users",
                    "repo": "user_service"
                }
            ),
            Node(
                id="schema:User",
                name="User",
                node_type=NodeType.CLASS,
                path="app/models/user.py",
                docstring="User profile entity model.",
                metadata={
                    "kind": "schema_model",
                    "repo": "user_service"
                }
            )
        ]
        self.store.insert_batch(nodes, [])

    def test_discover_service_endpoints(self):
        """Must discover endpoints and schemas accurately."""
        self._seed_endpoints_and_schemas()
        svc_name, endpoints, schemas = self.synthesizer.discover_service_endpoints("user_service")

        self.assertEqual(svc_name, "user_service")
        self.assertEqual(len(endpoints), 2)
        self.assertEqual(len(schemas), 1)

    def test_synthesize_proto_syntax(self):
        """Synthesized .proto must conform to protobuf v3 syntax."""
        self._seed_endpoints_and_schemas()
        _, endpoints, schemas = self.synthesizer.discover_service_endpoints("user_service")
        proto = self.synthesizer.synthesize_proto("user_service", endpoints, schemas)

        self.assertIn('syntax = "proto3";', proto)
        self.assertIn("package user_service.v1;", proto)
        self.assertIn("service UserService {", proto)
        self.assertIn("rpc GetUser (GetUserRequest) returns (GetUserResponse);", proto)
        self.assertIn("rpc CreateUser (CreateUserRequest) returns (CreateUserResponse);", proto)
        self.assertIn("message GetUserRequest {", proto)
        self.assertIn("  string id = 1;", proto)
        self.assertIn("message User {", proto)

    def test_synthesize_openapi_spec(self):
        """Synthesized OpenAPI must be valid 3.0.3 specification."""
        self._seed_endpoints_and_schemas()
        _, endpoints, schemas = self.synthesizer.discover_service_endpoints("user_service")
        spec = self.synthesizer.synthesize_openapi("user_service", endpoints, schemas)

        self.assertEqual(spec["openapi"], "3.0.3")
        self.assertIn("/api/v1/users/{id}", spec["paths"])
        self.assertIn("/api/v1/users", spec["paths"])
        self.assertIn("get", spec["paths"]["/api/v1/users/{id}"])
        self.assertIn("post", spec["paths"]["/api/v1/users"])
        self.assertIn("User", spec["components"]["schemas"])

    def test_synthesize_polyglot_servers(self):
        """Server adapters must be generated for Python, TypeScript, and Go."""
        self._seed_endpoints_and_schemas()
        _, endpoints, _ = self.synthesizer.discover_service_endpoints("user_service")

        # Python (FastAPI)
        py_server = self.synthesizer.synthesize_server_adapter("python", "user_service", endpoints)
        self.assertIn("from fastapi import APIRouter", py_server)
        self.assertIn('@router.get("/api/v1/users/{id}"', py_server)
        self.assertIn('@router.post("/api/v1/users"', py_server)

        # TypeScript (Express)
        ts_server = self.synthesizer.synthesize_server_adapter("typescript", "user_service", endpoints)
        self.assertIn("import { Router", ts_server)
        self.assertIn("user_serviceRouter.get('/api/v1/users/:id'", ts_server)
        self.assertIn("user_serviceRouter.post('/api/v1/users'", ts_server)

        # Go (net/http)
        go_server = self.synthesizer.synthesize_server_adapter("go", "user_service", endpoints)
        self.assertIn("package user_service", go_server)
        self.assertIn('mux.HandleFunc("/api/v1/users/id"', go_server)

    def test_synthesize_polyglot_clients(self):
        """Client SDKs must be generated for Python, TypeScript, and Go."""
        self._seed_endpoints_and_schemas()
        _, endpoints, _ = self.synthesizer.discover_service_endpoints("user_service")

        # Python client
        py_client = self.synthesizer.synthesize_client_adapter("python", "user_service", endpoints)
        self.assertIn("class UserServiceClient:", py_client)
        self.assertIn("def getuser(self", py_client.lower())

        # TypeScript client
        ts_client = self.synthesizer.synthesize_client_adapter("typescript", "user_service", endpoints)
        self.assertIn("export class UserServiceClient {", ts_client)
        self.assertIn("async getUser(", ts_client)

        # Go client
        go_client = self.synthesizer.synthesize_client_adapter("go", "user_service", endpoints)
        self.assertIn("type UserServiceClient struct {", go_client)
        self.assertIn("func (c *UserServiceClient) GetUser()", go_client)

    def test_synthesize_bundle_filesystem(self):
        """Microservice bundle must write all requested artifacts to output directory."""
        self._seed_endpoints_and_schemas()
        out_dir = self.workspace_root / "dist" / "user_service"
        files = self.synthesizer.synthesize_microservice_bundle(
            service_name="user_service",
            output_dir=out_dir,
            target_lang="python",
            format_type="all"
        )

        self.assertIn("user_service.proto", files)
        self.assertIn("openapi.json", files)
        self.assertIn("user_service_server.py", files)
        self.assertIn("user_service_client.py", files)

        self.assertTrue((out_dir / "user_service.proto").exists())
        self.assertTrue((out_dir / "openapi.json").exists())

    def test_mcp_synthesize_microservice_tool(self):
        """MCP server must handle agtoosa_synthesize_microservice."""
        self._seed_endpoints_and_schemas()
        server = MCPServer(self.workspace_root)
        server.store = self.store

        resp = server.handle_tool_call("agtoosa_synthesize_microservice", {
            "service_name": "user_service",
            "target_lang": "typescript",
            "format": "all"
        })
        data = json.loads(resp)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["service"], "user_service")
        self.assertEqual(data["endpoints_count"], 2)

    def test_cli_synthesize_microservice(self):
        """CLI agtoosa synthesize microservice must execute end-to-end."""
        agtoosa_dir = self.workspace_root / ".agtoosa"
        agtoosa_dir.mkdir(parents=True, exist_ok=True)
        live_db = agtoosa_dir / "graph.db"
        live_store = GraphStore(live_db)

        # Seed node
        live_store.insert_batch([
            Node(
                id="endpoint:GET:/orders",
                name="get_orders",
                node_type=NodeType.FUNCTION,
                path="app/routes/orders.py",
                metadata={"method": "GET", "route": "/orders", "repo": "order_svc"}
            )
        ], [])

        out_dir = self.workspace_root / "out_orders"
        exit_code = main([
            "-C", str(self.workspace_root),
            "synthesize", "microservice",
            "--service", "order_svc",
            "--target", "go",
            "--format", "all",
            "--output", str(out_dir),
            "--json"
        ])

        self.assertEqual(exit_code, 0)
        self.assertTrue((out_dir / "order_svc.proto").exists())
        self.assertTrue((out_dir / "openapi.json").exists())
        self.assertTrue((out_dir / "order_svc_server.go").exists())
        self.assertTrue((out_dir / "order_svc_client.go").exists())


if __name__ == "__main__":
    unittest.main()
