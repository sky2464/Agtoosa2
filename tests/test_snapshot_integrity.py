"""Tests for DEV-042: Atomic Snapshots & Manual Record Preservation."""
import tempfile
from pathlib import Path
import pytest

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore


def test_clear_preserves_manual_records():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_graph.db"
        store = GraphStore(db_path)

        # Insert manual records (story, adr, evidence) and code records (function, class)
        manual_story = Node(id="story:DEV-042", name="DEV-042", node_type=NodeType.STORY, path="docs/specs/spec-DEV-042.md")
        manual_adr = Node(id="adr:ADR-001", name="ADR-001", node_type=NodeType.ADR, path="docs/adrs/ADR-001.md")
        code_fn = Node(id="fn:test_func", name="test_func", node_type=NodeType.FUNCTION, path="agtoosa/test.py")

        edge_manual = Edge(source_id="story:DEV-042", target_id="adr:ADR-001", edge_type=EdgeType.IMPLEMENTS)
        edge_code = Edge(source_id="fn:test_func", target_id="story:DEV-042", edge_type=EdgeType.CALLS)

        store.insert_batch([manual_story, manual_adr, code_fn], [edge_manual, edge_code])

        # Clear with preserve_manual=True (default)
        store.clear(preserve_manual=True)

        assert store.get_node("story:DEV-042") is not None
        assert store.get_node("adr:ADR-001") is not None
        assert store.get_node("fn:test_func") is None

        edges = store.get_all_edges()
        assert len(edges) == 1
        assert edges[0]["source_id"] == "story:DEV-042"
        assert edges[0]["edge_type"] == EdgeType.IMPLEMENTS.value


def test_clear_all_removes_everything():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_graph.db"
        store = GraphStore(db_path)

        manual_story = Node(id="story:DEV-042", name="DEV-042", node_type=NodeType.STORY, path="docs/specs/spec-DEV-042.md")
        code_fn = Node(id="fn:test_func", name="test_func", node_type=NodeType.FUNCTION, path="agtoosa/test.py")

        store.insert_batch([manual_story, code_fn], [])

        store.clear(preserve_manual=False)

        assert store.get_node("story:DEV-042") is None
        assert store.get_node("fn:test_func") is None
        assert len(store.get_all_nodes()) == 0


def test_publish_atomic_snapshot():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_graph.db"
        store = GraphStore(db_path)

        # Pre-seed with manual node
        manual_story = Node(id="story:DEV-042", name="DEV-042", node_type=NodeType.STORY, path="docs/specs/spec-DEV-042.md")
        store.insert_batch([manual_story], [])

        nodes = [
            Node(id="fn:helper", name="helper", node_type=NodeType.FUNCTION, path="agtoosa/helper.py"),
            Node(id="class:Store", name="Store", node_type=NodeType.CLASS, path="agtoosa/store.py"),
        ]
        edges = [
            Edge(source_id="class:Store", target_id="fn:helper", edge_type=EdgeType.CALLS)
        ]
        fingerprints = {
            "agtoosa/helper.py": ("hash123", 1000.0),
            "agtoosa/store.py": ("hash456", 2000.0),
        }

        snap_id = store.publish_atomic_snapshot(
            snapshot_id="snap-001",
            nodes=nodes,
            edges=edges,
            fingerprints=fingerprints,
            source_hash="sha256-tree",
            preserve_manual=True
        )

        assert snap_id == "snap-001"
        latest = store.get_latest_snapshot()
        assert latest is not None
        assert latest["id"] == "snap-001"
        assert latest["status"] == "active"
        assert latest["node_count"] == 2
        assert latest["edge_count"] == 1
        assert latest["source_hash"] == "sha256-tree"

        # Manual story must still exist
        assert store.get_node("story:DEV-042") is not None
        assert store.get_node("fn:helper") is not None
        assert store.get_node("class:Store") is not None
