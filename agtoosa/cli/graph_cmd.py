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


def cmd_graph_explain(args: Any, workspace_root: Path) -> int:
    """Explain a symbol or file."""
    from agtoosa.graph.query import explain_node

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    res = explain_node(store, args.target)

    if not res:
        print(f"❌ Entity not found matching: '{args.target}'")
        return 1

    node = res["node"]
    line_info = f":L{node['start_line']}" if node.get("start_line") else ""
    print(f"📖 {node['node_type'].upper()}: {node['name']}")
    print(f"   • Location: {node['path']}{line_info}")
    if node.get("docstring"):
        print(f"   • Description: {node['docstring']}")

    if res["incoming"]:
        print(f"\n   📥 Ingress / Callers / Importers ({len(res['incoming'])}):")
        for inc in res["incoming"][:10]:
            print(f"     - [{inc['edge_type'].upper()}] {inc['type']}: {inc['name']} ({inc['path']})")

    if res["outgoing"]:
        print(f"\n   📤 Egress / Callees / Imports ({len(res['outgoing'])}):")
        for out in res["outgoing"][:10]:
            print(f"     - [{out['edge_type'].upper()}] {out['type']}: {out['name']} ({out['path']})")

    return 0


def cmd_graph_path(args: Any, workspace_root: Path) -> int:
    """Find directed path between two entities."""
    from agtoosa.graph.query import find_path

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    chain = find_path(store, args.source, args.target)

    if not chain:
        print(f"❌ No directed path found between '{args.source}' and '{args.target}'.")
        return 1

    print(f"🧭 Directed Path ({len(chain) - 1} hops):\n")
    for idx, step in enumerate(chain):
        n = step["node"]
        edge = step.get("edge")
        if edge:
            print(f"       │  [{edge['edge_type'].upper()}]")
            print(f"       ▼")
        print(f"  [{idx + 1}] {n.get('node_type', 'node').upper()}: {n.get('name', n.get('id'))} ({n.get('path', '')})")

    return 0


def cmd_graph_impact(args: Any, workspace_root: Path) -> int:
    """Analyze blast radius when an entity is changed."""
    from agtoosa.graph.query import compute_impact

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    depth = getattr(args, "depth", 3)
    res = compute_impact(store, args.target, max_depth=depth)

    if not res:
        print(f"❌ Entity not found matching: '{args.target}'")
        return 1

    target = res["target"]
    print(f"💥 Blast Radius Analysis for: {target['node_type'].upper()} {target['name']} ({target['path']})")
    print(f"   • Total Affected Entities: {res['impacted_count']} (up to depth {depth})")

    if res["impacted"]:
        print("\n   ⚠️  Upstream Callers & Dependent Files:")
        for imp in res["impacted"]:
            indent = " " * (imp["depth"] * 2)
            print(f"   {indent}└─ [Hop {imp['depth']}] {imp['node_type'].upper()}: {imp['name']} ({imp['path']}) via {imp['relationship']}")

    return 0
