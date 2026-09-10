"""CLI command implementations for agtoosa graph subcommands."""

import json
import sys
import time
from pathlib import Path
from typing import Any, List

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
    """Search the graph using full-text search or hybrid vector + FTS5 search."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    query_str = args.query
    limit = getattr(args, "limit", 15)
    store = GraphStore(db_path)

    if getattr(args, "hybrid", False):
        from agtoosa.graph.query import hybrid_search
        hybrid_results = hybrid_search(store, query_str, top_k=limit)
        if not hybrid_results:
            print(f"🔍 No hybrid matches found for: '{query_str}'")
            return 0
        print(f"🔮 Found {len(hybrid_results)} hybrid match(es) for '{query_str}':\n")
        for idx, item in enumerate(hybrid_results, start=1):
            r = item["node"]
            score = item["vector_score"]
            rrf = item["rrf_score"]
            source = item["match_source"]
            line_info = f":L{r['start_line']}" if r.get("start_line") else ""
            doc_snippet = f"\n     Doc: {r['docstring'][:100]}..." if r.get("docstring") else ""
            print(f" [{idx}] {r['node_type'].upper()}: {r['name']} [RRF: {rrf:.4f} | Cosine: {score:.3f} | {source}]")
            print(f"     Location: {r['path']}{line_info}{doc_snippet}")
        return 0

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
    """Export the graph to various formats (JSON, Obsidian, GraphML, Cypher, DOT)."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    from agtoosa.graph.export import MultiFormatExporter
    store = GraphStore(db_path)
    exporter = MultiFormatExporter(store)

    fmt = getattr(args, "format", "json") or "json"
    fmt = fmt.lower()
    output_path = getattr(args, "output", None)
    out_path_obj = Path(output_path) if output_path else None

    try:
        result = exporter.export(fmt, output_path=out_path_obj)
        if output_path:
            if fmt == "obsidian":
                print(f"✅ {result}")
            else:
                print(f"✅ Graph exported to {out_path_obj} ({out_path_obj.stat().st_size / 1024:.1f} KB)")
        else:
            print(result)
        return 0
    except ValueError as e:
        print(f"❌ Export error: {e}")
        return 1


def cmd_graph_view(args: Any, workspace_root: Path) -> int:
    """Generate standalone offline HTML visualizer."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    from agtoosa.graph.visualizer import VisualizerEngine
    store = GraphStore(db_path)
    visualizer = VisualizerEngine(store)

    output_path = getattr(args, "output", None)
    if output_path:
        out_file = Path(output_path)
    else:
        out_file = workspace_root / ".agtoosa" / "graph_view.html"

    filter_type = getattr(args, "filter", None)
    open_browser = getattr(args, "open", False)

    visualizer.save_html(out_file, filter_type=filter_type, open_browser=open_browser)
    print(f"🎨 Graph visualizer generated at: {out_file} ({out_file.stat().st_size / 1024:.1f} KB)")
    print(f"   Open in browser: file://{out_file.resolve()}")
    return 0


def cmd_graph_report(args: Any, workspace_root: Path) -> int:
    """Generate graph metrics, circular dependencies, and health scorecard report."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    from agtoosa.graph.metrics import MetricsEngine
    store = GraphStore(db_path)
    metrics_engine = MetricsEngine(store)
    report = metrics_engine.compute_all()

    fmt = getattr(args, "format", "text") or "text"
    fmt = fmt.lower()
    output_path = getattr(args, "output", None)

    if fmt == "json":
        content = json.dumps(report, indent=2)
    elif fmt in ("markdown", "md"):
        content = metrics_engine.format_markdown(report)
    else:
        content = metrics_engine.format_text(report)

    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(content, encoding="utf-8")
        print(f"✅ Architecture report saved to: {out_file}")
    else:
        print(content)

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

    if getattr(args, "json", False):
        import json
        print(json.dumps(res, indent=2))
        return 0

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
    """Analyze blast radius when an entity is changed across local and federated repositories."""
    from agtoosa.graph.query import compute_impact

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    depth = getattr(args, "depth", 3)
    federated = getattr(args, "federated", False)
    production = getattr(args, "production", False)
    res = compute_impact(store, args.target, max_depth=depth, federated=federated, production=production)

    if not res:
        print(f"❌ Entity not found matching: '{args.target}'")
        return 1

    if getattr(args, "json", False):
        import json
        print(json.dumps(res, indent=2))
        return 0

    target = res["target"]
    fed_badge = " (Federated Multi-Repo)" if federated else ""
    prod_badge = " [Production Telemetry Weighted]" if production else ""
    print(f"💥 Blast Radius Analysis{fed_badge}{prod_badge} for: {target['node_type'].upper()} {target['name']} ({target['path']})")
    print(f"   • Total Affected Entities: {res['impacted_count']} (up to depth {depth})")
    if res.get("federated_repos_impacted"):
        print(f"   • Cross-Service Impact:    Affected repos: {', '.join(res['federated_repos_impacted'])}")

    if res.get("production_blast_radius"):
        pbr = res["production_blast_radius"]
        tier_icons = {
            "P0_CRITICAL": "🔴 P0_CRITICAL",
            "P1_HIGH": "🟠 P1_HIGH",
            "P2_MODERATE": "🟡 P2_MODERATE",
            "P3_LOW": "🔵 P3_LOW",
            "P4_DORMANT": "⚪ P4_DORMANT",
        }
        print(f"   • Production Risk Tier:    {tier_icons.get(pbr['risk_tier'], pbr['risk_tier'])}")
        print(f"   • Total Traffic at Risk:   {pbr['total_traffic_at_risk']:,} invocations")
        print(f"   • Weighted Traffic Score:  {pbr['traffic_weighted_score']:,}")
        print(f"   • Active / Dormant Callers:{pbr['active_callers_count']} active, {pbr['dormant_callers_count']} dormant")

    if res["impacted"]:
        print("\n   ⚠️  Upstream Callers & Dependent Files:")
        for imp in res["impacted"]:
            indent = " " * (imp["depth"] * 2)
            repo_info = f" [Repo: {imp['repo']}]" if imp.get("repo") and imp["repo"] != "local" else ""
            prod_info = ""
            if production:
                calls = imp.get("call_count", 0)
                lat = imp.get("avg_duration_ms", 0.0)
                prod_info = f" ➔ Traffic: {calls:,} calls, Latency: {lat:.1f}ms"
            print(f"   {indent}└─ [Hop {imp['depth']}] {imp['node_type'].upper()}: {imp['name']} ({imp['path']}){repo_info}{prod_info} via {imp['relationship']}")

    return 0


def cmd_graph_symbols(args: Any, workspace_root: Path) -> int:
    """List functions and classes in a file with line numbers and caller impact."""
    import json

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    rel_path = getattr(args, "file", "")
    try:
        p_obj = Path(rel_path)
        if p_obj.is_absolute():
            rel_path = str(p_obj.relative_to(workspace_root))
    except ValueError:
        pass
    rel_path = rel_path.replace("\\", "/")

    with store._get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, node_type, path, start_line, end_line, docstring FROM nodes WHERE (path = ? OR path = ?) AND node_type IN ('class', 'function') ORDER BY start_line ASC;",
            (rel_path, f"./{rel_path}")
        ).fetchall()

    symbols = []
    for r in rows:
        sym_id = r["id"]
        incoming = store.get_neighbors(sym_id, direction="in")
        caller_nodes = [n for n in incoming if n.get("node_type") in ("function", "class", "file")]
        caller_count = len(caller_nodes)

        if caller_count >= 10:
            risk = "CRITICAL"
        elif caller_count >= 5:
            risk = "HIGH"
        elif caller_count >= 1:
            risk = "MODERATE"
        else:
            risk = "LOW"

        symbols.append({
            "id": sym_id,
            "name": r["name"],
            "type": r["node_type"],
            "path": r["path"],
            "start_line": r["start_line"],
            "end_line": r["end_line"],
            "caller_count": caller_count,
            "risk": risk,
            "top_callers": [c["name"] for c in caller_nodes[:5]],
            "docstring": (r["docstring"] or "").split("\n")[0] if r["docstring"] else None
        })

    if getattr(args, "json", False):
        print(json.dumps(symbols, indent=2))
        return 0

    print(f"🏛️  Symbols in '{rel_path}' ({len(symbols)} found):")
    for s in symbols:
        line_str = f"L{s['start_line']}-{s['end_line']}" if s['start_line'] else "unknown line"
        print(f"   • {s['type'].upper()} {s['name']} ({line_str}) ➔ {s['caller_count']} callers [{s['risk']} RISK]")
    return 0


def cmd_graph_watch(args: Any, workspace_root: Path) -> int:
    """Continuously monitor workspace for changes and incrementally update knowledge graph."""
    from agtoosa.watcher.watcher import WorkspaceWatcher

    db_path = get_default_db_path(workspace_root)
    store = GraphStore(db_path)
    watcher = WorkspaceWatcher(workspace_root, store)

    interval = getattr(args, "interval", 1.0)
    debounce = getattr(args, "debounce", 0.5)

    print(f"👀 Agtoosa Continuous Watcher active on: {workspace_root}")
    print(f"   • Polling Interval: {interval}s | Debounce Window: {debounce}s")
    print("   • Press Ctrl+C to stop.\n")

    def on_change_callback(changed: List[str], stats: Any):
        print(f"⚡ [{time.strftime('%H:%M:%S')}] Detected changes in {len(changed)} file(s):")
        for f in changed[:5]:
            print(f"     - {f}")
        if len(changed) > 5:
            print(f"     ... and {len(changed) - 5} more")
        print(f"   ✅ Incremental sync complete: {stats.total_nodes} nodes, {stats.total_edges} edges across {stats.files_indexed} files.\n")

    watcher.register_callback(on_change_callback)

    # Initial poll
    changed, stats = watcher.poll_once()
    if changed and stats:
        on_change_callback(changed, stats)

    try:
        watcher.watch_forever(interval=interval, debounce=debounce)
    except KeyboardInterrupt:
        print("\n🛑 Watcher stopped.")

    return 0


def cmd_graph_hooks(args: Any, workspace_root: Path) -> int:
    """Manage Agtoosa Git hooks for automated pre-commit and checkout graph sync."""
    from agtoosa.watcher.hooks import install_git_hooks, remove_git_hooks, get_git_hooks_status

    action = getattr(args, "hook_action", "status")

    if action == "install":
        res = install_git_hooks(workspace_root)
        if not res:
            print("❌ .git repository not found in workspace.")
            return 1
        print("🪝 Agtoosa Git Hooks Installed:")
        for hook, ok in res.items():
            icon = "✅" if ok else "❌"
            print(f"   {icon} {hook}")
        return 0

    elif action == "remove":
        res = remove_git_hooks(workspace_root)
        print("🪝 Agtoosa Git Hooks Removed:")
        for hook, ok in res.items():
            icon = "🗑️" if ok else "⚠️"
            print(f"   {icon} {hook}")
        return 0

    else:
        status = get_git_hooks_status(workspace_root)
        if not status:
            print("⚠️  No Git repository detected or no Agtoosa hooks installed.")
            return 0
        print("🪝 Agtoosa Git Hooks Status:")
        for hook, active in status.items():
            state = "✅ Active" if active else "⬜ Inactive"
            print(f"   • {hook}: {state}")
        return 0


def cmd_graph_embeddings_build(args: Any, workspace_root: Path) -> int:
    """Build or rebuild dense semantic vector embeddings for all graph nodes."""
    from agtoosa.graph.embeddings import SemanticEmbeddingEngine
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    clean = getattr(args, "clean", False)
    action = "Rebuilding" if clean else "Building"
    print(f"⚡ {action} dense vector embeddings at {db_path}...")

    store = GraphStore(db_path)
    engine = SemanticEmbeddingEngine()
    stats = engine.build_embeddings(store, clean=clean)

    print("✅ Embeddings indexing complete!")
    print(f"   • Nodes Embedded: {stats['indexed_count']}")
    print(f"   • Vector Dimension: {stats['dimension']}")
    print(f"   • Storage: SQLite 'node_embeddings' table (L2-normalized float BLOBs)")
    return 0


def cmd_graph_embeddings_status(args: Any, workspace_root: Path) -> int:
    """Report vector embeddings status and index statistics."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    total_nodes = len(store.get_all_nodes())
    embedding_count = store.get_embedding_count()

    print("📊 Agtoosa2 Vector Embeddings Status")
    print(f"   • Indexed Embeddings: {embedding_count} / {total_nodes} nodes")
    coverage = (embedding_count / total_nodes * 100.0) if total_nodes > 0 else 0.0
    print(f"   • Index Coverage: {coverage:.1f}%")
    print(f"   • Vector Dimension: 128-D dense subword/n-gram hashing projection")
    print(f"   • Distance Metric: Cosine Similarity (dot product)")
    print(f"   • Status: {'Ready' if embedding_count > 0 else 'Unindexed (run agtoosa graph embeddings build)'}")
    return 0


def cmd_graph_federate(args: Any, workspace_root: Path) -> int:
    """Manage cross-repository graph federation and contract syncing."""
    import json
    from agtoosa.federation.manager import FederationManager

    db_path = get_default_db_path(workspace_root)
    store = GraphStore(db_path)
    manager = FederationManager(store, workspace_root)
    action = getattr(args, "federate_action", "list")

    if action == "add":
        name = args.name
        uri = args.uri
        schema = getattr(args, "schema", None)
        res = manager.add_repository(name=name, uri=uri, schema_path=schema)
        print(f"🌐 Registered federated repository '{name}':")
        print(f"   • URI:        {res['uri']}")
        print(f"   • Local Path: {res['local_path']}")
        print(f"   • Type:       {res['repo_type']}")
        if res.get("schema_path"):
            print(f"   • Contract:   {res['schema_path']}")
        print(f"   Run 'agtoosa graph federate sync {name}' to ingest and link contracts.")
        return 0

    elif action == "list":
        repos = manager.list_repositories()
        if getattr(args, "json", False):
            print(json.dumps(repos, indent=2))
            return 0

        if not repos:
            print("🌐 No federated repositories registered.")
            print("   Use 'agtoosa graph federate add <name> <path-or-url>' to link an external service.")
            return 0

        print(f"🌐 Registered Federated Repositories ({len(repos)}):")
        for r in repos:
            synced = r.get("synced_at") or "Never"
            contract_info = f" | Contract: {r['schema_path']}" if r.get("schema_path") else ""
            print(f"   • {r['name']} ({r['repo_type']}) ➔ {r['uri']}{contract_info} [Last Sync: {synced}]")
        return 0

    elif action == "remove":
        name = args.name
        ok = manager.remove_repository(name)
        if ok:
            print(f"🗑️  Removed federated repository '{name}' and purged its nodes from knowledge graph.")
            return 0
        else:
            print(f"⚠️  Repository '{name}' not found.")
            return 1

    elif action == "sync":
        name = getattr(args, "name", None)
        clean = getattr(args, "clean", False)
        if name:
            try:
                print(f"⚡ Syncing federated repository '{name}'...")
                res = manager.sync_repository(name, clean=clean)
                print(f"✅ Federated repository '{name}' synchronized:")
                print(f"   • Nodes Indexed:       {res['nodes_indexed']}")
                print(f"   • Edges Indexed:       {res['edges_indexed']}")
                print(f"   • Cross-Repo Callers:  {res['cross_edges']}")
                return 0
            except ValueError as e:
                print(f"❌ {e}")
                return 1
        else:
            print("⚡ Syncing all federated repositories...")
            res = manager.sync_all(clean=clean)
            print(f"✅ Synchronized {res['synced_count']} federated repository(ies).")
            for item in res["repositories"]:
                print(f"   • {item['name']}: {item['nodes_indexed']} nodes, {item['cross_edges']} cross-repo links")
            return 0

    return 0
