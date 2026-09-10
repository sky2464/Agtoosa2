"""Automated verification suite for Stage 14 (DEV-014): Hybrid GraphRAG v2 & Semantic Vector Search."""

import json
import math
from pathlib import Path
import pytest

from agtoosa.graph.store import GraphStore
from agtoosa.graph.embeddings import SemanticEmbeddingEngine
from agtoosa.graph.query import hybrid_search
from agtoosa.core.context_compiler import ContextCompiler
from agtoosa.mcp.server import MCPServer
from agtoosa.core.model import Node, Edge, NodeType, EdgeType


@pytest.fixture
def temp_store(tmp_path: Path) -> GraphStore:
    db_file = tmp_path / "test_graph.db"
    store = GraphStore(db_file)

    nodes = [
        Node(id="func:login", name="login_handler", node_type=NodeType.FUNCTION, path="agtoosa/auth.py", docstring="Authenticates user credentials and returns an auth session token."),
        Node(id="func:verify", name="verify_auth_token", node_type=NodeType.FUNCTION, path="agtoosa/auth.py", docstring="Validates cryptographic JWT token signature and expiration."),
        Node(id="func:render_canvas", name="render_webgl_canvas", node_type=NodeType.FUNCTION, path="agtoosa/ui/canvas.py", docstring="Draws 3D mesh triangles using GPU shader pipeline."),
        Node(id="class:AuthService", name="AuthService", node_type=NodeType.CLASS, path="agtoosa/auth.py", docstring="Enterprise user authentication and authorization service."),
        Node(id="story:DEV-001", name="Authentication System", node_type=NodeType.STORY, path="docs/specs/spec-auth.md", docstring="Implement secure login and token validation."),
        Node(id="task:DEV-001-1", name="Implement login", node_type=NodeType.TASK, path="docs/specs/spec-auth.md", docstring="Write login handler function."),
        Node(id="crit:DEV-001-AC1", name="Verify Tokens", node_type=NodeType.CRITERION, path="docs/specs/spec-auth.md", docstring="All tokens must be verified before granting access.")
    ]

    edges = [
        Edge(source_id="func:login", target_id="func:verify", edge_type=EdgeType.CALLS, provenance="ast"),
        Edge(source_id="class:AuthService", target_id="func:login", edge_type=EdgeType.CONTAINS, provenance="ast"),
        Edge(source_id="story:DEV-001", target_id="crit:DEV-001-AC1", edge_type=EdgeType.CONTAINS, provenance="doc"),
        Edge(source_id="story:DEV-001", target_id="task:DEV-001-1", edge_type=EdgeType.CONTAINS, provenance="doc")
    ]

    store.insert_batch(nodes, edges)
    return store


def test_embedding_vector_dimensions_and_norm():
    """Verify vector generation has exact 128 dimensions and unit L2 norm."""
    engine = SemanticEmbeddingEngine(dimension=128)

    vec = engine.embed_text("authentication token verification credentials")
    assert len(vec) == 128

    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-5

    empty_vec = engine.embed_text("")
    assert len(empty_vec) == 128
    assert all(x == 0.0 for x in empty_vec)


def test_cosine_similarity_semantic_separation():
    """Verify similar semantic concepts have high cosine similarity while unrelated have low similarity."""
    engine = SemanticEmbeddingEngine()

    v_auth1 = engine.embed_text("user authentication login session")
    v_auth2 = engine.embed_text("user credentials login token authorize")
    v_graphics = engine.embed_text("render 3D webgl canvas triangle shader mesh")

    sim_related = engine.cosine_similarity(v_auth1, v_auth2)
    sim_unrelated = engine.cosine_similarity(v_auth1, v_graphics)

    assert sim_related > 0.20, f"Expected strong similarity for related terms, got {sim_related}"
    assert sim_unrelated < 0.05, f"Expected near zero similarity for unrelated terms, got {sim_unrelated}"
    assert sim_related > sim_unrelated + 0.15


def test_vector_pack_unpack():
    """Verify packing and unpacking float vectors to binary BLOBs."""
    engine = SemanticEmbeddingEngine(dimension=128)
    vec = engine.embed_text("agtoosa knowledge graph test")

    blob = engine.pack_vector(vec)
    assert len(blob) == 128 * 4  # 512 bytes

    unpacked = engine.unpack_vector(blob)
    assert len(unpacked) == 128
    for original, recovered in zip(vec, unpacked):
        assert abs(original - recovered) < 1e-6


def test_store_embedding_persistence(temp_store: GraphStore):
    """Verify embedding storage, retrieval, count, and clear in GraphStore."""
    engine = SemanticEmbeddingEngine(dimension=128)
    stats = engine.build_embeddings(temp_store, clean=True)

    assert stats["indexed_count"] == 7
    assert stats["dimension"] == 128
    assert temp_store.get_embedding_count() == 7

    blob = temp_store.get_embedding("func:login")
    assert blob is not None
    vec = engine.unpack_vector(blob)
    assert len(vec) == 128

    all_emb = temp_store.get_all_embeddings()
    assert len(all_emb) == 7

    temp_store.clear_embeddings()
    assert temp_store.get_embedding_count() == 0


def test_hybrid_search_rrf_scoring(temp_store: GraphStore):
    """Verify Reciprocal Rank Fusion combines lexical and semantic search properly."""
    engine = SemanticEmbeddingEngine()
    engine.build_embeddings(temp_store)

    # Query with semantic concept
    results = hybrid_search(temp_store, "security credentials token authentication", top_k=5)
    assert len(results) > 0

    top_result = results[0]
    assert "node" in top_result
    assert "rrf_score" in top_result
    assert "vector_score" in top_result
    assert "match_source" in top_result

    # Auth-related node should be rank 1
    top_node_id = top_result["node"]["id"]
    assert top_node_id in ("story:DEV-001", "func:login", "func:verify", "class:AuthService")
    assert top_result["vector_score"] > 0.20
    assert top_result["rrf_score"] > 0.01


def test_context_compiler_hybrid_pack(temp_store: GraphStore):
    """Verify ContextCompiler outputs rich Hybrid GraphRAG v2 prompt pack."""
    engine = SemanticEmbeddingEngine()
    engine.build_embeddings(temp_store)

    compiler = ContextCompiler(temp_store)
    pack = compiler.compile_context("story:DEV-001", hybrid=True)

    assert pack is not None
    assert "# Agtoosa Context Pack (Hybrid GraphRAG v2): Authentication System" in pack
    assert "## Direct Code Context (Hybrid Vector & Graph Retrieval)" in pack
    assert "Cosine:" in pack
    assert "login_handler" in pack or "verify_auth_token" in pack

    # Test symbol pack with hybrid semantic neighbors
    sym_pack = compiler.compile_context("func:login", hybrid=True)
    assert sym_pack is not None
    assert "## Semantically Related Symbols (Hybrid GraphRAG)" in sym_pack
    assert "## Blast Radius" in sym_pack


def test_mcp_hybrid_search_tool(tmp_path: Path):
    """Verify MCP Server exposes agtoosa_hybrid_search and handles hybrid calls."""
    server = MCPServer(tmp_path)
    tool_defs = server.get_tool_definitions()
    tool_names = [t["name"] for t in tool_defs]

    assert "agtoosa_hybrid_search" in tool_names
    assert "agtoosa_search_graph" in tool_names
    assert "agtoosa_get_task_context" in tool_names

    # Test tool call
    res_str = server.handle_tool_call("agtoosa_hybrid_search", {"query": "context", "limit": 5})
    res_json = json.loads(res_str)
    assert isinstance(res_json, list)


def test_cli_embeddings_and_hybrid_commands(tmp_path: Path, capsys: pytest.CaptureFixture):
    """Verify CLI embeddings build, status, and hybrid query execution."""
    from agtoosa.cli.main import main

    db_dir = tmp_path / ".agtoosa"
    db_dir.mkdir(parents=True, exist_ok=True)
    store = GraphStore(db_dir / "graph.db")

    node = Node(
        id="func:secret_filter",
        name="filter_api_secrets",
        node_type=NodeType.FUNCTION,
        path="agtoosa/crypto.py",
        docstring="Sanitizes tokens, cryptographic keys, and password hashes."
    )
    store.insert_batch([node], [])

    # 1. Build embeddings
    rc = main(["-C", str(tmp_path), "graph", "embeddings", "build"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Embeddings indexing complete!" in captured.out
    assert "Nodes Embedded: 1" in captured.out

    # 2. Embeddings status
    rc = main(["-C", str(tmp_path), "graph", "embeddings", "status"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Indexed Embeddings: 1 / 1 nodes" in captured.out
    assert "Ready" in captured.out

    # 3. Hybrid search query
    rc = main(["-C", str(tmp_path), "graph", "query", "cryptographic keys password", "--hybrid"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "hybrid match(es)" in captured.out
    assert "filter_api_secrets" in captured.out

    # 4. Context compile with --hybrid
    rc = main(["-C", str(tmp_path), "context", "compile", "filter_api_secrets", "--hybrid"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Symbol Context Pack: filter_api_secrets" in captured.out
