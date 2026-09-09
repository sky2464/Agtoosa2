"""CLI command implementations for agtoosa graph subcommands."""

import json
import sys
from pathlib import Path
from typing import Any

from agtoosa.graph.store import GraphStore
from agtoosa.parser import ParserEngine


def get_default_db_path(workspace_root: Path) -> Path:
    return workspace_root / ".agtoosa" / "graph.db"


def cmd_graph_build(args: Any, workspace_root: Path) -> int:
    """Build or rebuild the knowledge graph."""
    db_path = get_default_db_path(workspace_root)
    store = GraphStore(db_path)
    engine = ParserEngine()

    clean = getattr(args, "clean", False)
    action_str = "Rebuilding" if clean else "Building"
    print(f"🧠 {action_str} Agtoosa2 Knowledge Graph at {db_path}...")

    stats = engine.index_workspace(workspace_root, store, clean=clean)

    print("✅ Indexing complete!")
    print(f"   • Total Nodes: {stats.total_nodes}")
    print(f"   • Total Edges: {stats.total_edges}")
    print(f"   • Files Indexed: {stats.files_indexed}")
    if stats.node_counts_by_type:
        print("   • Breakdown by Type:")
        for ntype, count in sorted(stats.node_counts_by_type.items()):
            print(f"     - {ntype}: {count}")

    return 0


def cmd_graph_status(args: Any, workspace_root: Path) -> int:
    """Report graph status and health metrics."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"⚠️  No knowledge graph found at {db_path}.")
        print("   Run 'agtoosa graph build' to initialize and index the repository.")
        return 1

    store = GraphStore(db_path)
    stats = store.get_stats()

    print("📊 Agtoosa2 Knowledge Graph Status")
    print(f"   • Database: {db_path} ({db_path.stat().st_size / 1024:.1f} KB)")
    print(f"   • Total Nodes: {stats.total_nodes}")
    print(f"   • Total Edges: {stats.total_edges}")
    print(f"   • Source Files: {stats.files_indexed}")
    print(f"   • Last Indexed: {stats.last_indexed_at or 'Never'}")

    if stats.node_counts_by_type:
        print("   • Node Distribution:")
        for ntype, count in sorted(stats.node_counts_by_type.items()):
            print(f"     - {ntype}: {count}")

    return 0


def cmd_graph_query(args: Any, workspace_root: Path) -> int:
    """Search the graph using full-text search."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    query_str = args.query
    limit = getattr(args, "limit", 15)

    store = GraphStore(db_path)
    results = store.query_fts(query_str, limit=limit)

    if not results:
        print(f"🔍 No graph nodes found matching: '{query_str}'")
        return 0

    print(f"🔍 Found {len(results)} match(es) for '{query_str}':\n")
    for idx, r in enumerate(results, start=1):
        line_info = f":L{r['start_line']}" if r.get("start_line") else ""
        doc_snippet = f"\n     Doc: {r['docstring'][:100]}..." if r.get("docstring") else ""
        print(f" [{idx}] {r['node_type'].upper()}: {r['name']}")
        print(f"     Location: {r['path']}{line_info}{doc_snippet}")

    return 0


def cmd_graph_export(args: Any, workspace_root: Path) -> int:
    """Export the graph to standard JSON format."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    data = store.export_json()

    output_path = getattr(args, "output", None)
    if output_path:
        out_file = Path(output_path)
        out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"✅ Graph exported to {out_file} ({out_file.stat().st_size / 1024:.1f} KB)")
    else:
        print(json.dumps(data, indent=2))

    return 0
