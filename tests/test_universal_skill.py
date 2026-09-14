"""Unit tests for DEV-037: Universal Multi-Host Agent Skill & Token-Budgeted Topology Traversal."""

import json
from pathlib import Path
import pytest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.core.topology_compiler import (
    TopologyContextCompiler,
    SkillInstaller,
    BudgetedContextPack,
)
from agtoosa.mcp.server import MCPServer
from agtoosa.cli.main import main


@pytest.fixture
def skill_store(tmp_path: Path):
    db_path = tmp_path / ".agtoosa" / "graph.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = GraphStore(db_path)

    nodes = [
        Node(id="code:PaymentService", name="PaymentService", node_type=NodeType.CLASS, path="payment/service.py", docstring="Handles credit card charges and billing workflows."),
        Node(id="code:process_payment", name="process_payment", node_type=NodeType.FUNCTION, path="payment/service.py", docstring="Process transaction with gateway."),
        Node(id="code:AuthService", name="AuthService", node_type=NodeType.CLASS, path="auth/service.py", docstring="Authenticates identity and tokens."),
        Node(id="code:InvoiceGenerator", name="InvoiceGenerator", node_type=NodeType.CLASS, path="billing/invoice.py", docstring="Renders customer invoice PDFs."),
    ]

    edges = [
        Edge(source_id="code:process_payment", target_id="code:PaymentService", edge_type=EdgeType.CALLS),
        Edge(source_id="code:PaymentService", target_id="code:AuthService", edge_type=EdgeType.CALLS),
        Edge(source_id="code:PaymentService", target_id="code:InvoiceGenerator", edge_type=EdgeType.CALLS),
    ]

    store.insert_batch(nodes, edges)
    return store, tmp_path


def test_budgeted_context_compiler(skill_store):
    store, root = skill_store
    compiler = TopologyContextCompiler(store)

    # Budget of 300 tokens
    pack = compiler.compile_budgeted_query("PaymentService", budget_tokens=300, strategy="hybrid")
    assert pack.tokens_used <= 300
    assert pack.nodes_included >= 1
    assert "class PaymentService" in pack.content
    assert "Agtoosa2 Topology Context Pack" in pack.content


def test_skill_installer(skill_store):
    store, root = skill_store
    installer = SkillInstaller(root)

    res = installer.install(target="all")
    assert len(res["installed_files"]) == 3

    claude_skill = root / ".claude" / "skills" / "agtoosa" / "SKILL.md"
    agent_skill = root / ".agents" / "skills" / "agtoosa" / "SKILL.md"
    cursor_rule = root / ".cursor" / "rules" / "agtoosa.mdc"

    assert claude_skill.exists()
    assert agent_skill.exists()
    assert cursor_rule.exists()

    claude_text = claude_skill.read_text(encoding="utf-8")
    assert "name: agtoosa" in claude_text
    assert "agtoosa query" in claude_text


def test_cli_query_and_skill(skill_store, capsys):
    store, root = skill_store

    # Test agtoosa query
    exit_code = main(["-C", str(root), "query", "PaymentService", "--budget", "500", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    query_data = json.loads(captured.out)
    assert query_data["budget_tokens"] == 500
    assert query_data["tokens_used"] <= 500
    assert query_data["nodes_included"] >= 1

    # Test agtoosa skill install
    exit_code = main(["-C", str(root), "skill", "install", "--target", "cursor", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    skill_data = json.loads(captured.out)
    assert skill_data["target"] == "cursor"
    assert len(skill_data["installed_files"]) == 1


def test_mcp_budgeted_query_tool(skill_store):
    store, root = skill_store
    server = MCPServer(root)

    # Validate tool is registered in schema
    tool_names = [t["name"] for t in server.get_tool_definitions()]
    assert "agtoosa_budgeted_query" in tool_names
    assert "agtoosa_get_socratic_audit" in tool_names

    # Test handle_tool_call
    resp_str = server.handle_tool_call("agtoosa_budgeted_query", {"query": "PaymentService", "budget_tokens": 400})
    resp = json.loads(resp_str)
    assert resp["budget_tokens"] == 400
    assert resp["tokens_used"] <= 400
    assert resp["nodes_included"] >= 1
