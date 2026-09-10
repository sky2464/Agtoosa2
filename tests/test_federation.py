"""Automated verification suite for Stage 15 (DEV-015): Cross-Repo Graph Federation."""

import json
from pathlib import Path
import pytest

from agtoosa.graph.store import GraphStore
from agtoosa.federation.schema_parser import ContractSchemaParser
from agtoosa.federation.resolver import CrossRepoLinker
from agtoosa.federation.manager import FederationManager
from agtoosa.graph.query import compute_impact
from agtoosa.mcp.server import MCPServer
from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.cli.main import main


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    db_dir = ws / ".agtoosa"
    db_dir.mkdir()
    return ws


def test_federation_store_crud(temp_workspace: Path):
    """Verify GraphStore federated repository registry methods."""
    store = GraphStore(temp_workspace / ".agtoosa" / "graph.db")

    # 1. Add repo
    store.add_federated_repo(
        name="auth-service",
        uri="../auth-service",
        local_path=str(temp_workspace / "auth-service"),
        repo_type="local_dir",
        schema_path="openapi.json",
        metadata={"tier": 2}
    )

    repos = store.get_federated_repos()
    assert len(repos) == 1
    assert repos[0]["name"] == "auth-service"
    assert repos[0]["schema_path"] == "openapi.json"
    assert repos[0]["metadata"]["tier"] == 2

    # 2. Get specific repo
    r = store.get_federated_repo("auth-service")
    assert r is not None
    assert r["name"] == "auth-service"

    # 3. Update sync timestamp
    store.update_federated_repo_sync("auth-service", "2026-09-10T12:00:00Z")
    r_updated = store.get_federated_repo("auth-service")
    assert r_updated["synced_at"] == "2026-09-10T12:00:00Z"

    # 4. Remove repo
    ok = store.remove_federated_repo("auth-service")
    assert ok is True
    assert len(store.get_federated_repos()) == 0


def test_openapi_schema_parser(tmp_path: Path):
    """Verify OpenAPI 3.0 / Swagger schema contract parsing."""
    openapi_file = tmp_path / "openapi.json"
    openapi_file.write_text(json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "Auth API", "version": "1.0.0"},
        "paths": {
            "/auth/login": {
                "post": {
                    "operationId": "login_user",
                    "summary": "Authenticate user credentials",
                    "tags": ["Authentication"]
                }
            },
            "/api/v1/users": {
                "get": {
                    "operationId": "list_users",
                    "summary": "Get all active users"
                }
            }
        },
        "components": {
            "schemas": {
                "User": {"type": "object", "description": "User entity model"}
            }
        }
    }), encoding="utf-8")

    parser = ContractSchemaParser()
    nodes, edges = parser.parse_openapi(openapi_file, repo_name="auth-service")

    assert len(nodes) == 3
    node_ids = [n.id for n in nodes]
    assert "repo:auth-service:endpoint:POST:/auth/login" in node_ids
    assert "repo:auth-service:endpoint:GET:/api/v1/users" in node_ids
    assert "repo:auth-service:schema:User" in node_ids

    login_node = next(n for n in nodes if "endpoint:POST:/auth/login" in n.id)
    assert login_node.name == "login_user"
    assert login_node.metadata["method"] == "POST"
    assert login_node.metadata["route"] == "/auth/login"


def test_protobuf_schema_parser(tmp_path: Path):
    """Verify gRPC Protobuf schema contract parsing."""
    proto_file = tmp_path / "billing.proto"
    proto_file.write_text("""
    syntax = "proto3";
    package billing;

    service BillingService {
        rpc ProcessPayment (PaymentRequest) returns (PaymentResponse);
        rpc GetInvoice (InvoiceRequest) returns (InvoiceResponse);
    }

    message PaymentRequest {
        string account_id = 1;
        double amount = 2;
    }
    """, encoding="utf-8")

    parser = ContractSchemaParser()
    nodes, edges = parser.parse_protobuf(proto_file, repo_name="billing-api")

    node_ids = [n.id for n in nodes]
    assert "repo:billing-api:service:BillingService" in node_ids
    assert "repo:billing-api:rpc:BillingService.ProcessPayment" in node_ids
    assert "repo:billing-api:schema:PaymentRequest" in node_ids

    # Verify containment edges
    assert len(edges) == 2
    assert edges[0].edge_type == EdgeType.CONTAINS


def test_graphql_schema_parser(tmp_path: Path):
    """Verify GraphQL schema contract parsing."""
    gql_file = tmp_path / "schema.graphql"
    gql_file.write_text("""
    type Query {
        user(id: ID!): User
    }
    type Mutation {
        updateProfile(bio: String!): User
    }
    type User {
        id: ID!
        name: String!
    }
    """, encoding="utf-8")

    parser = ContractSchemaParser()
    nodes, edges = parser.parse_graphql(gql_file, repo_name="web-bff")

    node_ids = [n.id for n in nodes]
    assert "repo:web-bff:graphql:Query.user" in node_ids
    assert "repo:web-bff:graphql:Mutation.updateProfile" in node_ids
    assert "repo:web-bff:schema:User" in node_ids


def test_cross_repo_dependency_linking(temp_workspace: Path):
    """Verify consumer code HTTP/RPC invocations are linked to provider endpoints."""
    store = GraphStore(temp_workspace / ".agtoosa" / "graph.db")

    # 1. Insert provider endpoint node
    ep_node = Node(
        id="repo:auth-api:endpoint:POST:/api/v1/auth/token",
        name="create_token",
        node_type=NodeType.FUNCTION,
        path="auth/openapi.json",
        docstring="Issue access token",
        metadata={"route": "/api/v1/auth/token", "method": "POST", "protocol": "rest", "repo": "auth-api"}
    )
    store.insert_batch([ep_node], [])

    # 2. Create consumer client function in workspace
    consumer_file = temp_workspace / "client.py"
    consumer_file.write_text("""
def login_user(username, password):
    resp = requests.post("/api/v1/auth/token", json={"user": username})
    return resp.json()
""", encoding="utf-8")

    client_node = Node(
        id="func:login_user",
        name="login_user",
        node_type=NodeType.FUNCTION,
        path="client.py",
        start_line=2,
        end_line=4,
        docstring="Client login function"
    )
    store.insert_batch([client_node], [])

    # 3. Run cross-repo linker
    linker = CrossRepoLinker(store)
    edges = linker.link_cross_repo_dependencies(temp_workspace)

    assert len(edges) == 1
    edge = edges[0]
    assert edge.source_id == "func:login_user"
    assert edge.target_id == "repo:auth-api:endpoint:POST:/api/v1/auth/token"
    assert edge.provenance == "federated_contract"


def test_federated_blast_radius(temp_workspace: Path):
    """Verify compute_impact traces callers across local and federated repositories."""
    store = GraphStore(temp_workspace / ".agtoosa" / "graph.db")

    # Provider endpoint
    ep = Node(
        id="repo:auth-api:endpoint:POST:/login",
        name="login_endpoint",
        node_type=NodeType.FUNCTION,
        path="auth/openapi.json",
        metadata={"repo": "auth-api"}
    )
    # Consumer function in local repo
    consumer = Node(
        id="func:submit_login",
        name="submit_login",
        node_type=NodeType.FUNCTION,
        path="frontend/auth.py",
        metadata={"repo": "local"}
    )
    edge = Edge(source_id="func:submit_login", target_id="repo:auth-api:endpoint:POST:/login", edge_type=EdgeType.CALLS, provenance="federated_contract")

    store.insert_batch([ep, consumer], [edge])

    # Compute impact of modifying provider endpoint
    res = compute_impact(store, "repo:auth-api:endpoint:POST:/login", federated=True)
    assert res is not None
    assert res["impacted_count"] == 1
    assert res["impacted"][0]["id"] == "func:submit_login"


def test_federation_cli_commands(temp_workspace: Path, capsys: pytest.CaptureFixture):
    """Verify CLI commands for agtoosa graph federate add, list, sync, remove."""
    # Create sibling repo with openapi contract
    sibling_repo = temp_workspace.parent / "sibling_auth_service"
    sibling_repo.mkdir(parents=True, exist_ok=True)
    openapi_file = sibling_repo / "openapi.json"
    openapi_file.write_text(json.dumps({
        "openapi": "3.0.0",
        "paths": {
            "/api/auth": {"get": {"operationId": "check_auth"}}
        }
    }), encoding="utf-8")

    # 1. Add federated repo
    rc = main(["-C", str(temp_workspace), "graph", "federate", "add", "auth-svc", str(sibling_repo), "-s", "openapi.json"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Registered federated repository 'auth-svc'" in captured.out

    # 2. List federated repos
    rc = main(["-C", str(temp_workspace), "graph", "federate", "list"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "auth-svc" in captured.out

    # 3. Sync federated repo
    rc = main(["-C", str(temp_workspace), "graph", "federate", "sync", "auth-svc"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Federated repository 'auth-svc' synchronized" in captured.out

    # 4. Remove federated repo
    rc = main(["-C", str(temp_workspace), "graph", "federate", "remove", "auth-svc"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Removed federated repository 'auth-svc'" in captured.out


def test_mcp_federation_tools(temp_workspace: Path):
    """Verify MCP server exposes federation listing and sync tools."""
    server = MCPServer(temp_workspace)
    tool_names = [t["name"] for t in server.get_tool_definitions()]

    assert "agtoosa_list_federated_repos" in tool_names
    assert "agtoosa_sync_federation" in tool_names

    # Test list call
    res_str = server.handle_tool_call("agtoosa_list_federated_repos", {})
    res_json = json.loads(res_str)
    assert isinstance(res_json, list)
