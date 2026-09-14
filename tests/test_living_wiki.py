"""Unit tests for Living C4 Architecture Wiki & Robert C. Martin Metrics (DEV-034)."""

import json
from pathlib import Path
import tempfile
import pytest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.wiki import LivingWikiGenerator, MartinMetrics, CommunitySummary
from agtoosa.cli.main import main


@pytest.fixture
def wiki_store(tmp_path: Path):
    db_path = tmp_path / ".agtoosa" / "graph.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = GraphStore(db_path)

    nodes = [
        # Subsystem A: core package
        Node(id="core:BaseModel", name="BaseModel", node_type=NodeType.CLASS, path="core/base.py", metadata={"is_abstract": True}),
        Node(id="core:Entity", name="Entity", node_type=NodeType.CLASS, path="core/entity.py"),
        Node(id="core:init", name="init", node_type=NodeType.FUNCTION, path="core/base.py"),
        # Subsystem B: service package
        Node(id="service:UserService", name="UserService", node_type=NodeType.CLASS, path="service/user.py"),
        Node(id="service:AuthService", name="AuthService", node_type=NodeType.CLASS, path="service/auth.py"),
    ]

    edges = [
        # Internal edges within core
        Edge(source_id="core:Entity", target_id="core:BaseModel", edge_type=EdgeType.INHERITS),
        Edge(source_id="core:init", target_id="core:BaseModel", edge_type=EdgeType.CALLS),
        # Internal edges within service
        Edge(source_id="service:AuthService", target_id="service:UserService", edge_type=EdgeType.CALLS),
        # Cross-subsystem edges: service -> core
        Edge(source_id="service:UserService", target_id="service:AuthService", edge_type=EdgeType.CALLS),
        Edge(source_id="service:UserService", target_id="core:Entity", edge_type=EdgeType.CALLS),
        Edge(source_id="service:AuthService", target_id="core:BaseModel", edge_type=EdgeType.CALLS),
    ]

    store.insert_batch(nodes, edges)

    return store, tmp_path


def test_martin_metrics_calculation(wiki_store):
    store, root = wiki_store
    generator = LivingWikiGenerator(store, root)

    communities = generator.analyze_communities()
    assert len(communities) >= 1

    for c in communities:
        m = c.metrics
        assert m.afferent_coupling >= 0
        assert m.efferent_coupling >= 0
        assert 0.0 <= m.instability <= 1.0
        assert 0.0 <= m.abstractness <= 1.0
        assert 0.0 <= m.distance_from_main_sequence <= 1.0


def test_wiki_generation_obsidian_and_standard(wiki_store):
    store, root = wiki_store
    generator = LivingWikiGenerator(store, root)

    wiki_dir = root / ".agtoosa" / "wiki"
    res = generator.generate_wiki(wiki_dir=wiki_dir, format="obsidian")

    assert Path(res["output_dir"]).exists()
    assert "index.md" in res["articles_created"]
    assert len(res["articles_created"]) > 1

    index_content = (wiki_dir / "index.md").read_text()
    assert "Architecture Wiki" in index_content
    assert "[[Subsystem-" in index_content  # Obsidian wikilink style

    # Test standard format
    wiki_std = root / "docs" / "wiki"
    res_std = generator.generate_wiki(wiki_dir=wiki_std, format="standard")
    std_index = (wiki_std / "index.md").read_text()
    assert ".md)" in std_index


def test_c4_diagram_embedding(wiki_store):
    store, root = wiki_store
    generator = LivingWikiGenerator(store, root)

    communities = generator.analyze_communities()
    c = communities[0]
    diagram = generator.generate_c4_diagram(c)

    assert "```mermaid" in diagram
    assert ("flowchart TD" in diagram or "graph TD" in diagram)
    assert "```" in diagram


def test_cli_wiki_commands(wiki_store, capsys):
    store, root = wiki_store

    # Test agtoosa wiki build with -C as top-level flag
    exit_code = main(["-C", str(root), "wiki", "build", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_communities"] >= 1
    assert "index.md" in data["articles_created"]

    # Test agtoosa wiki metrics
    exit_code = main(["-C", str(root), "wiki", "metrics", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    metrics_data = json.loads(captured.out)
    assert len(metrics_data) >= 1
    assert "metrics" in metrics_data[0]
    assert "afferent_coupling" in metrics_data[0]["metrics"]
