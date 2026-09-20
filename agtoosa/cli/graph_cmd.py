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
    # Check if user is running in the Agtoosa project directory itself
    # Detection strategy: look for AGENTS.md and agtoosa/core/ directory
    agents_md_path = workspace_root / "AGENTS.md"
    agtoosa_dir = workspace_root / "agtoosa"
    
    is_agtoosa_project = False
    
    # Simple check: look for AGENTS.md and agtoosa/core/ directory
    if agents_md_path.exists() and agtoosa_dir.exists() and (agtoosa_dir / "core").exists():
        is_agtoosa_project = True
    
    if is_agtoosa_project:
        print("ℹ️  Self-indexing Agtoosa2 workspace (to index another project: cd /path/to/project && agtoosa graph build)\n")
    
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

    print("\n💡 Suggested Next Actions:")
    print("   • Health & Centrality:  agtoosa graph report")
    print("   • Socratic Audit:       agtoosa audit")
    print("   • Dead Code Pruning:    agtoosa refactor dead-code --dry-run")
    print("   • Interactive Studio:   agtoosa graph view --serve --open")

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
                assert out_path_obj is not None
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
        print(f"ℹ️  Knowledge graph not found at {db_path}. Automatically indexing workspace...\n")
        ret = cmd_graph_build(args, workspace_root)
        if ret != 0:
            return ret
        print()

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

    if getattr(args, "serve", False):
        from agtoosa.graph.server import run_studio_server
        port = getattr(args, "port", 8080) or 8080
        host = getattr(args, "host", "127.0.0.1") or "127.0.0.1"
        strict_port = getattr(args, "strict_port", False)

        try:
            server = run_studio_server(store, workspace_root, port=port, host=host, auto_port=not strict_port)
        except OSError as exc:
            print(f"❌ Error starting Agtoosa Studio: port {port} is unavailable ({exc}).")
            print(f"   Specify a different port using: agtoosa graph view --serve --port <port>")
            return 1

        actual_port = server.server_address[1]
        display_host = "127.0.0.1" if host in ("0.0.0.0", "") else host
        url = f"http://{display_host}:{actual_port}/"
        print(f"🚀 Agtoosa Studio Command Center live at: {url}", flush=True)
        print(f"   Two-way interactive refactoring API enabled.", flush=True)
        print(f"   Press Ctrl+C to stop.", flush=True)
        if open_browser:
            import webbrowser
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Agtoosa Studio stopped.")
            server.server_close()
        return 0

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
        print(f"   • {str(s['type']).upper()} {s['name']} ({line_str}) ➔ {s['caller_count']} callers [{s['risk']} RISK]")
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


def cmd_graph_routes(args: Any, workspace_root: Path) -> int:
    """List detected HTTP API endpoints and bound handler functions."""
    from agtoosa.graph.query import query_routes

    db_path = get_default_db_path(workspace_root)
    store = GraphStore(db_path)
    method = getattr(args, "method", None)
    routes = query_routes(store, method=method)

    if getattr(args, "json", False):
        print(json.dumps({"routes_count": len(routes), "routes": routes}, indent=2))
        return 0

    print(f"🌐 Discovered HTTP API Routes ({len(routes)} endpoint(s)):\n")
    if not routes:
        print("   No routes detected. Supported frameworks: FastAPI, Flask, Express, NestJS.")
        return 0

    for r in routes:
        m = r["http_method"]
        p = r["path"]
        fw = r["framework"]
        fpath = r["file_path"]
        lnum = f":{r['start_line']}" if r.get("start_line") else ""
        handler_name = r["handler"]["name"] if r.get("handler") else "unknown"

        m_tag = f"[{m}]"
        print(f"   • {m_tag:<8} {p:<30} ➔  {handler_name} ({fpath}{lnum}) [{fw}]")
        if r.get("injected_dependencies"):
            deps_str = ", ".join(d["provider"] or d["target_id"] for d in r["injected_dependencies"])
            print(f"       💉 Injected: {deps_str}")

    return 0


def cmd_graph_di(args: Any, workspace_root: Path) -> int:
    """Trace dependency injection providers and consumers for a target symbol."""
    from agtoosa.graph.query import query_di

    db_path = get_default_db_path(workspace_root)
    store = GraphStore(db_path)
    symbol = args.symbol
    di_info = query_di(store, symbol)

    if getattr(args, "json", False):
        print(json.dumps(di_info, indent=2))
        return 0

    target = di_info.get("target")
    if not target:
        print(f"⚠️ Symbol '{symbol}' not found in knowledge graph.")
        return 1

    print(f"💉 Dependency Injection Graph for '{target.get('name', symbol)}':\n")
    injected = di_info.get("injected_into_target", [])
    if injected:
        print("   ⬇️  Injected Dependencies (Requires):")
        for inj in injected:
            p_name = inj.get("provider") or inj.get("target_id")
            param = f" (param: {inj['param']})" if inj.get("param") else ""
            print(f"      • {p_name}{param}")
    else:
        print("   ⬇️  Injected Dependencies: None")

    consumers = di_info.get("consumers_injecting_target", [])
    if consumers:
        print("\n   ⬆️  Consumers (Injected Into):")
        for cons in consumers:
            c_name = cons["caller"]["name"] if cons.get("caller") else cons["source_id"]
            param = f" (param: {cons['param']})" if cons.get("param") else ""
            print(f"      • {c_name}{param}")
    else:
        print("\n   ⬆️  Consumers: None")

    return 0


def cmd_graph_events(args: Any, workspace_root: Path) -> int:
    """List message queue topics, pub/sub channels, task queues, and async lineage."""
    from agtoosa.graph.query import query_events

    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    topic_filter = getattr(args, "topic", None)
    events_data = query_events(store, topic=topic_filter)

    if getattr(args, "json", False):
        print(json.dumps(events_data, indent=2))
        return 0

    topics = events_data.get("topics", [])
    total = events_data.get("total_topics", 0)
    orphans = events_data.get("orphan_count", 0)

    print(f"📡 Asynchronous Event & Queue Lineage ({total} topic(s), {orphans} orphan(s)):\n")
    if not topics:
        print("   No message queue topics or task queues detected.")
        print("   Supported: Kafka, RabbitMQ, Redis Pub/Sub, Celery, BullMQ.")
        return 0

    for t in topics:
        broker_tag = f"[{t['broker'].upper()}]"
        orphan_badge = ""
        if t["is_orphan"]:
            if t["orphan_reason"] == "no_subscribers":
                orphan_badge = " ⚠️  [NO CONSUMERS - UNHANDLED]"
            elif t["orphan_reason"] == "no_publishers":
                orphan_badge = " ⚠️  [NO PRODUCERS - DORMANT]"
            else:
                orphan_badge = " ⚠️  [ISOLATED TOPIC]"

        print(f"   • {broker_tag:<10} {t['name']}{orphan_badge}")
        if t.get("path"):
            lnum = f":{t['start_line']}" if t.get("start_line") else ""
            print(f"       📍 First seen: {t['path']}{lnum}")

        pubs = t.get("publishers", [])
        if pubs:
            pub_names = []
            for p in pubs:
                node_name = p["node"]["name"] if p.get("node") else p["id"].split(":")[-1]
                path = f" ({p['node']['path']})" if p.get("node") and p["node"].get("path") else ""
                pub_names.append(f"{node_name}{path}")
            print(f"       📤 Publishers ({len(pubs)}): {', '.join(pub_names)}")
        else:
            print("       📤 Publishers: None")

        subs = t.get("subscribers", [])
        if subs:
            sub_names = []
            for s in subs:
                node_name = s["node"]["name"] if s.get("node") else s["id"].split(":")[-1]
                path = f" ({s['node']['path']})" if s.get("node") and s["node"].get("path") else ""
                sub_names.append(f"{node_name}{path}")
            print(f"       📥 Subscribers ({len(subs)}): {', '.join(sub_names)}")
        else:
            print("       📥 Subscribers: None")
        print()

    return 0


def cmd_graph_topology(args: Any, workspace_root: Path) -> int:
    """Inspect distributed runtime service topology, cross-service RPC/HTTP links, and latency bottlenecks."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print("⚠️  Knowledge graph not found. Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    from agtoosa.graph.query import query_topology

    service_filter = getattr(args, "service", None)
    topology = query_topology(store, service=service_filter)

    if getattr(args, "json", False):
        print(json.dumps(topology, indent=2))
        return 0

    services = topology["services"]
    edges = topology["network_edges"]
    bottlenecks = topology["bottlenecks"]
    error_hotspots = topology["error_hotspots"]
    circular_deps = topology["circular_dependencies"]

    print("🌐 Distributed Runtime Service Topology (DEV-030)\n")
    if not services:
        print("   No distributed services or network traces ingested yet.")
        print("   Ingest OpenTelemetry, Jaeger, or Zipkin traces with:")
        print("     agtoosa telemetry traces <trace_file.json>\n")
        return 0

    print(f"   Discovered Services: {len(services)} | Network Links: {len(edges)} | Total Calls: {topology['total_calls']:,}\n")

    print("   SERVICES & INGRESS/EGRESS:")
    for s in services:
        meta = s.get("metadata", {})
        ingress = s.get("total_ingress_calls", 0)
        egress = s.get("total_egress_calls", 0)
        print(f"   • 🌐 {s['name']:<24} (Ingress: {ingress:>6} calls | Egress: {egress:>6} calls)")

    if edges:
        print("\n   NETWORK CALL PATHS & LATENCY:")
        print(f"   {'Source':<20} -> {'Target':<28} {'Calls':<8} {'p50 (ms)':<10} {'p95 (ms)':<10} {'Errors'}")
        print("   " + "-" * 85)
        for e in edges:
            src = e["source_id"].replace("service:", "").replace("endpoint:", "")
            tgt = e["target_id"].replace("service:", "").replace("endpoint:", "")
            err_str = f"{e['error_count']} ({e['error_rate']*100:.1f}%)" if e['error_count'] > 0 else "0"
            proto = f"[{e['protocols'][0]}]" if e.get("protocols") else ""
            print(f"   {src:<20} -> {tgt:<28} {e['call_count']:<8} {e['p50_duration_ms']:<10.2f} {e['p95_duration_ms']:<10.2f} {err_str}")

    if bottlenecks:
        print("\n   ⚠️  LATENCY BOTTLENECKS (p95 >= 300ms):")
        for b in bottlenecks:
            src = b["source_id"].replace("service:", "")
            tgt = b["target_id"].replace("service:", "")
            print(f"   • ⏱️  {src} -> {tgt}: p95 = {b['p95_duration_ms']:.1f}ms (avg {b['avg_duration_ms']:.1f}ms across {b['call_count']} calls)")

    if error_hotspots:
        print("\n   ⚠️  ERROR HOTSPOTS (Errors detected):")
        for eh in error_hotspots:
            src = eh["source_id"].replace("service:", "")
            tgt = eh["target_id"].replace("service:", "")
            print(f"   • 💥 {src} -> {tgt}: {eh['error_count']} errors ({eh['error_rate']*100:.2f}% error rate)")

    if circular_deps:
        print("\n   🚨 CIRCULAR SERVICE DEPENDENCIES:")
        for cd in circular_deps:
            print(f"   • 🔄 {cd['service_a']} <-> {cd['service_b']} ({cd['description']})")

    print()
    return 0


def cmd_graph_capabilities(args: Any, workspace_root: Path) -> int:
    """Inspect installed parser coverage and language capabilities (DEV-040/043)."""
    import dataclasses
    from agtoosa.parser.capabilities import CAPABILITY_REGISTRY

    caps = CAPABILITY_REGISTRY.list_all()
    summary = CAPABILITY_REGISTRY.get_summary()
    as_json = getattr(args, "json", False)

    if as_json:
        payload = {
            "summary": summary,
            "capabilities": [dataclasses.asdict(c) for c in caps]
        }
        for c in payload["capabilities"]:
            c["active_backend"] = c["active_backend"].value if hasattr(c["active_backend"], "value") else str(c["active_backend"])
            c["coverage_tier"] = c["coverage_tier"].value if hasattr(c["coverage_tier"], "value") else str(c["coverage_tier"])
        print(json.dumps(payload, indent=2))
        return 0

    print("🛠️  Agtoosa2 Language & Parser Capabilities (EPIC-001 / DEV-040 / DEV-043)")
    print("=" * 76)
    for cap in caps:
        tier = cap.coverage_tier.value
        backend = cap.active_backend.value
        exts = ", ".join(cap.file_extensions)
        rationale = "✅ Yes" if cap.supports_rationale_markers else "❌ No"
        print(f"\n📦 {cap.display_name} ({cap.family_id})")
        print(f"   • Extensions: {exts}")
        print(f"   • Backend: {backend} | Tier: {tier}")
        print(f"   • Decision Rationale (# WHY:, # NOTE:): {rationale}")
        if cap.limitations:
            print("   • Known Limitations:")
            for lim in cap.limitations:
                print(f"     - {lim}")
    print("\n" + "=" * 76)
    return 0


def cmd_graph_verify(args: Any, workspace_root: Path) -> int:
    """Verify knowledge graph integrity and source hash freshness (DEV-043)."""
    import hashlib
    from agtoosa.core.model import ContractEnvelope, ResolutionStatus

    db_path = get_default_db_path(workspace_root)
    as_json = getattr(args, "json", False)

    if not db_path.exists():
        msg = f"Knowledge graph database not found at {db_path}."
        if as_json:
            envelope = ContractEnvelope(
                freshness="stale",
                completeness="empty",
                resolution_status=ResolutionStatus.UNRESOLVED,
                diagnostics=[msg],
            )
            print(json.dumps(envelope.to_dict(), indent=2))
        else:
            print(f"❌ {msg}")
            print("   Run 'agtoosa graph build' first.")
        return 1

    store = GraphStore(db_path)
    latest_snap = store.get_latest_snapshot()
    fingerprints = store.get_fingerprints()

    stale_files: List[str] = []
    missing_files: List[str] = []
    verified_files: int = 0

    for rel_path, stored_hash in fingerprints.items():
        file_path = workspace_root / rel_path
        if not file_path.exists():
            missing_files.append(rel_path)
            continue
        try:
            content_bytes = file_path.read_bytes()
            current_hash = hashlib.sha256(content_bytes).hexdigest()
            if current_hash != stored_hash:
                stale_files.append(rel_path)
            else:
                verified_files += 1
        except Exception:
            missing_files.append(rel_path)

    # Check for unindexed new files
    from agtoosa.parser.scanner import scan_workspace
    workspace_files = scan_workspace(workspace_root)
    unindexed_files: List[str] = []
    for f in workspace_files:
        try:
            rel = str(f.relative_to(workspace_root))
            if rel not in fingerprints:
                unindexed_files.append(rel)
        except ValueError:
            pass

    is_fresh = (len(stale_files) == 0 and len(missing_files) == 0 and len(unindexed_files) == 0)
    freshness = "fresh" if is_fresh else "stale"
    completeness = "complete" if len(missing_files) == 0 else "partial"

    diagnostics = []
    if stale_files:
        diagnostics.append(f"{len(stale_files)} file(s) modified since last index: {', '.join(stale_files[:5])}")
    if missing_files:
        diagnostics.append(f"{len(missing_files)} file(s) deleted since last index: {', '.join(missing_files[:5])}")
    if unindexed_files:
        diagnostics.append(f"{len(unindexed_files)} new file(s) unindexed: {', '.join(unindexed_files[:5])}")

    snapshot_id = latest_snap["id"] if latest_snap else None

    envelope = ContractEnvelope(
        contract_version="1.0.0",
        snapshot_id=snapshot_id,
        freshness=freshness,
        completeness=completeness,
        resolution_status=ResolutionStatus.RESOLVED if is_fresh else ResolutionStatus.AMBIGUOUS,
        data={
            "verified_files": verified_files,
            "stale_files": stale_files,
            "missing_files": missing_files,
            "unindexed_files": unindexed_files,
            "latest_snapshot": latest_snap,
        },
        diagnostics=diagnostics,
    )

    if as_json:
        print(json.dumps(envelope.to_dict(), indent=2))
        return 0 if is_fresh else 1

    print("🛡️  Agtoosa2 Graph Integrity Verification (DEV-043)")
    print(f"   • Database: {db_path}")
    print(f"   • Active Snapshot: {snapshot_id or 'None'}")
    print(f"   • Verified Matching Files: {verified_files}")
    if is_fresh:
        print("✅ Graph is completely FRESH and synchronized with disk.")
        return 0
    else:
        print("⚠️  Graph is STALE or DRIFTED:")
        for diag in diagnostics:
            print(f"   • {diag}")
        print("   Run 'agtoosa graph build' to synchronize graph state.")
        return 1


def cmd_ingest(args: Any, workspace_root: Path) -> int:
    """Ingest diagram or document into knowledge graph (DEV-033)."""
    target = args.target
    db_path = get_default_db_path(workspace_root)
    store = GraphStore(db_path)

    nodes = []
    edges = []

    if target.startswith("http://") or target.startswith("https://"):
        from agtoosa.parser.multimodal.doc_ingester import DocumentIngester
        ingester = DocumentIngester()
        nodes, edges = ingester.ingest_url(target)
    else:
        file_path = (workspace_root / target).resolve() if not Path(target).is_absolute() else Path(target)
        if not file_path.exists():
            print(f"❌ Target not found: {target}")
            return 1

        suffix = file_path.suffix.lower()
        if suffix in {".mmd", ".mermaid", ".puml", ".plantuml", ".excalidraw"} or "excalidraw" in file_path.name.lower():
            from agtoosa.parser.multimodal.diagram_parser import DiagramParser
            parser = DiagramParser()
            nodes, edges = parser.parse_file(file_path, workspace_root)
        elif suffix in {".md", ".markdown", ".txt"}:
            from agtoosa.parser.multimodal.doc_ingester import DocumentIngester
            ingester = DocumentIngester()
            nodes, edges = ingester.ingest_markdown(file_path, workspace_root)
        else:
            print(f"⚠️ Unsupported multimodal file type: {suffix}")
            return 1

    if nodes or edges:
        store.insert_batch(nodes, edges)

    as_json = getattr(args, "json", False)
    if as_json:
        print(json.dumps({
            "target": target,
            "nodes_ingested": len(nodes),
            "edges_ingested": len(edges),
            "node_names": [n.name for n in nodes]
        }, indent=2))
    else:
        print(f"📥 Successfully ingested '{target}' into knowledge graph:")
        print(f"   • Extracted Nodes: {len(nodes)}")
        print(f"   • Extracted Edges: {len(edges)}")
        for n in nodes[:5]:
            print(f"     - {n.node_type.value}: {n.name}")
        if len(nodes) > 5:
            print(f"     ... and {len(nodes) - 5} more")

    return 0


def cmd_add(args: Any, workspace_root: Path) -> int:
    """Add remote technical documentation or paper into knowledge graph (DEV-033)."""
    args.target = args.url
    return cmd_ingest(args, workspace_root)


def cmd_graph_drift_visual(args: Any, workspace_root: Path) -> int:
    """Detect architectural drift between visual diagrams and AST code (DEV-033)."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"❌ Knowledge graph database not found at {db_path}.")
        return 1

    store = GraphStore(db_path)
    from agtoosa.graph.visual_drift import VisualDriftDetector
    detector = VisualDriftDetector(store)
    report = detector.detect_drift()

    as_json = getattr(args, "json", False)
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print("\n🖼️  Visual-to-Code Architecture Drift Audit (DEV-033)")
        print("=" * 70)
        print(f"Status: {'⚠️  DRIFT DETECTED' if report['drift_detected'] else '✅ SYNCHRONIZED'}")
        print(f" • Total Visual Components: {report['total_visual_nodes']}")
        print(f" • Synchronized Components: {len(report['synchronized_components'])}")
        print(f" • Ghost Nodes:            {report['total_ghost_nodes']}")
        print(f" • Path Mismatches:         {report['total_path_mismatches']}")

        if report["ghost_nodes"]:
            print("\n👻 GHOST NODES (Diagram components without code implementation):")
            for g in report["ghost_nodes"]:
                print(f"   • '{g['name']}' in {g['path']} ({g['diagram_type']})")

        if report["path_mismatches"]:
            print("\n⚡ PATH MISMATCHES (Diagram arrows divergent from AST callgraph):")
            for p in report["path_mismatches"]:
                print(f"   • {p['visual_edge']}: {p['issue']}")

        print("=" * 70 + "\n")

    if getattr(args, "strict", False) and report["drift_detected"]:
        return 1
    return 0


def cmd_wiki_build(args: Any, workspace_root: Path) -> int:
    """Generate living C4 architecture wiki and Martin metrics (DEV-034)."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"❌ Knowledge graph database not found at {db_path}.")
        return 1

    store = GraphStore(db_path)
    from agtoosa.graph.wiki import LivingWikiGenerator
    generator = LivingWikiGenerator(store, workspace_root)

    output_dir = getattr(args, "dir", None)
    wiki_dir = Path(output_dir) if output_dir else None
    fmt = getattr(args, "format", "obsidian")

    result = generator.generate_wiki(wiki_dir=wiki_dir, format=fmt)

    as_json = getattr(args, "json", False)
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n📚 Living Architecture Wiki Built Successfully (DEV-034)")
        print("=" * 70)
        print(f"Directory: {result['output_dir']}")
        print(f"Format:    {result['format']}")
        print(f"Articles:  {len(result['articles_created'])} created:")
        for art in result["articles_created"]:
            print(f"   • {art}")
        print("=" * 70 + "\n")

    return 0


def cmd_wiki_metrics(args: Any, workspace_root: Path) -> int:
    """Output Robert C. Martin Package Coupling & Distance Metrics (DEV-034)."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"❌ Knowledge graph database not found at {db_path}.")
        return 1

    store = GraphStore(db_path)
    from agtoosa.graph.wiki import LivingWikiGenerator
    generator = LivingWikiGenerator(store, workspace_root)

    communities = generator.analyze_communities()

    as_json = getattr(args, "json", False)
    if as_json:
        data = [c.to_dict() for c in communities]
        print(json.dumps(data, indent=2))
    else:
        print("\n📐 Robert C. Martin Architecture Metrics (DEV-034)")
        print("=" * 80)
        print(f"{'Community / Subsystem':<28} {'Nodes':<7} {'Ca':<5} {'Ce':<5} {'I':<8} {'A':<8} {'D':<8}")
        print("-" * 80)
        for c in communities:
            m = c.metrics
            print(f"{c.name:<28} {len(c.nodes):<7} {m.afferent_coupling:<5} {m.efferent_coupling:<5} {m.instability:<8.2f} {m.abstractness:<8.2f} {m.distance_from_main_sequence:<8.2f}")
        print("=" * 80)
        print("Metrics: Ca (Afferent Coupling), Ce (Efferent Coupling), I (Instability), A (Abstractness), D (Distance from Main Sequence)\n")

    return 0


def cmd_extract_semantic(args: Any, workspace_root: Path) -> int:
    """Run Zero-Trust multi-agent semantic extraction and hallucination guard (DEV-035)."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"❌ Knowledge graph database not found at {db_path}.")
        return 1

    store = GraphStore(db_path)
    from agtoosa.semantic.guard import SemanticExtractionEngine

    target_dir_str = getattr(args, "dir", None)
    target_dir = Path(target_dir_str) if target_dir_str else (workspace_root / "docs")
    if not target_dir.is_absolute():
        target_dir = (workspace_root / target_dir).resolve()

    if not target_dir.exists():
        print(f"❌ Target documentation directory not found at {target_dir}.")
        return 1

    chunk_size = getattr(args, "chunk_size", 15)
    strict = getattr(args, "strict_grounding", False)

    engine = SemanticExtractionEngine(store, workspace_root)
    report = engine.batch_extract(target_dir, chunk_size=chunk_size, strict_grounding=strict)

    as_json = getattr(args, "json", False)
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print("\n🛡️  Zero-Trust Semantic Extraction & Hallucination Guard (DEV-035)")
        print("=" * 75)
        print(f"Directory:              {target_dir}")
        print(f"Total Files Processed:  {report['total_files']} (in {report['total_chunks']} chunks)")
        print(f"Grounded Edges Created: {report['edges_created']}")
        print(f"Hallucinations Blocked: {report['hallucinations_blocked']}")
        print(f"Strict Grounding Mode:  {'ENABLED' if strict else 'DISABLED (Fuzzy recovery)'}")
        print("=" * 75 + "\n")

    return 0


def cmd_audit(args: Any, workspace_root: Path) -> int:
    """Execute Socratic architecture audit and generate GRAPH_REPORT.md (DEV-036)."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"❌ Knowledge graph database not found at {db_path}.")
        return 1

    store = GraphStore(db_path)
    from agtoosa.review.socratic_audit import SocraticAuditEngine

    engine = SocraticAuditEngine(store, workspace_root)

    output_path_str = getattr(args, "output", None)
    output_path = Path(output_path_str) if output_path_str else None
    if output_path and not output_path.is_absolute():
        output_path = (workspace_root / output_path).resolve()

    as_json = getattr(args, "json", False) or getattr(args, "format", "markdown") == "json"
    fmt = "json" if as_json else "markdown"

    result = engine.write_report(output_path=output_path, format=fmt)

    if as_json and not output_path:
        print(json.dumps(result["data"], indent=2))
    else:
        print("\n🏛️  Socratic Architecture Audit Complete (DEV-036)")
        print("=" * 75)
        print(f"Report Location:        {result['output_path']}")
        print(f"Format:                 {result['format']}")
        print(f"Total Alarms Detected:  {result['total_alarms']}")
        print(f"God Nodes Flagged:      {len(result['data']['god_nodes'])}")
        print(f"Cyclic Hotspots:        {result['data']['cyclic_hotspots']['total_cycles_detected']}")
        print(f"Latent Doc Couplings:   {len(result['data']['cross_modality_couplings'])}")
        print("=" * 75 + "\n")

    return 0


def cmd_budgeted_query(args: Any, workspace_root: Path) -> int:
    """Run token-budgeted topology query with AST skeleton extraction (DEV-037)."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"❌ Knowledge graph database not found at {db_path}.")
        return 1

    store = GraphStore(db_path)
    from agtoosa.core.topology_compiler import TopologyContextCompiler

    compiler = TopologyContextCompiler(store)
    query_str = getattr(args, "query", "")
    budget = getattr(args, "budget", 1500)
    strategy = getattr(args, "strategy", "hybrid")

    pack = compiler.compile_budgeted_query(query=query_str, budget_tokens=budget, strategy=strategy)

    as_json = getattr(args, "json", False)
    if as_json:
        print(json.dumps(pack.to_dict(), indent=2))
    else:
        print(f"\n🧭 Token-Budgeted Topology Context ({pack.strategy.upper()})")
        print("=" * 75)
        print(f"Query:          {pack.query}")
        print(f"Token Budget:   {pack.budget_tokens} max ({pack.tokens_used} tokens used)")
        print(f"Nodes Included: {pack.nodes_included}")
        print("=" * 75)
        print(pack.content)

    return 0


def cmd_skill_install(args: Any, workspace_root: Path) -> int:
    """Install universal agent skill bundles (DEV-037)."""
    from agtoosa.core.topology_compiler import SkillInstaller

    target = getattr(args, "target", "all")
    custom_path_str = getattr(args, "path", None)
    custom_path = Path(custom_path_str) if custom_path_str else None

    installer = SkillInstaller(workspace_root)
    res = installer.install(target=target, custom_path=custom_path)

    as_json = getattr(args, "json", False)
    if as_json:
        print(json.dumps(res, indent=2))
    else:
        print(f"\n📦 Agtoosa2 Universal Agent Skills Installed ({res['target']})")
        print("=" * 75)
        for f in res["installed_files"]:
            print(f"   • {f}")
        print("=" * 75 + "\n")

    return 0


def cmd_graph_spectral(args: Any, workspace_root: Path) -> int:
    """Execute algebraic and spectral graph theory analysis (DEV-052)."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"❌ Knowledge graph database not found at {db_path}.")
        return 1

    store = GraphStore(db_path)
    nodes = store.get_all_nodes()
    edges = store.get_all_edges()

    from agtoosa.graph.spectral import SpectralEngine
    engine = SpectralEngine(nodes, edges)

    as_json = getattr(args, "json", False)

    if getattr(args, "cut", False):
        res = engine.compute_fiedler_cut()
        if as_json:
            print(json.dumps(res, indent=2))
        else:
            print("\n📐 Spectral Bisection & Cheeger Conductance Cut (DEV-052)")
            print("=" * 75)
            print(f"Algebraic Connectivity (λ₂): {res['algebraic_connectivity']}")
            print(f"Is Connected:                {res['is_connected']}")
            print(f"Cheeger Conductance h(G):    {res['cheeger_conductance']}")
            print(f"Cheeger Bounds:              [{res['cheeger_lower_bound']}, {res['cheeger_upper_bound']}]")
            print(f"Partition Sizes:             Set A: {len(res['cut_partition'][0])}, Set B: {len(res['cut_partition'][1])}")
            print("=" * 75 + "\n")
        return 0

    if getattr(args, "radius", False):
        res = engine.compute_spectral_radius()
        if as_json:
            print(json.dumps(res, indent=2))
        else:
            print("\n📐 Perron-Frobenius Spectral Radius & Epidemic Threshold (DEV-052)")
            print("=" * 75)
            print(f"Spectral Radius λ₁(A):       {res['spectral_radius']}")
            print(f"Epidemic Threshold τ_c:      {res['epidemic_threshold']}")
            print(f"Power Iteration Converged:   {res['is_converged']}")
            print("=" * 75 + "\n")
        return 0

    if getattr(args, "fas", False):
        res = engine.compute_minimum_feedback_arc_set()
        if as_json:
            print(json.dumps(res, indent=2))
        else:
            print("\n📐 Minimum Feedback Arc Set (FAS) (DEV-052)")
            print("=" * 75)
            print(f"Total Directed Edges:        {res['total_edges']}")
            print(f"Feedback Arcs to Decouple:   {res['feedback_arc_count']}")
            if res["feedback_arcs"]:
                print("\n   Feedback Edges Causing Cycles:")
                for e in res["feedback_arcs"][:15]:
                    print(f"   • {e['source']} -> {e['target']}")
                if len(res["feedback_arcs"]) > 15:
                    print(f"     ... and {len(res['feedback_arcs']) - 15} more")
            else:
                print("   ✅ Graph is already a strict Directed Acyclic Graph (DAG) with zero cycles.")
            print("=" * 75 + "\n")
        return 0

    if getattr(args, "transitive", False):
        res = engine.compute_transitive_reduction()
        if as_json:
            print(json.dumps(res, indent=2))
        else:
            print("\n📐 Poset Transitive Reduction / Hasse Diagram (DEV-052)")
            print("=" * 75)
            print(f"Essential Edges:             {res['essential_edge_count']}")
            print(f"Redundant Transitive Edges:  {res['redundant_edge_count']}")
            if res["redundant_edges"]:
                print("\n   Redundant Shortcut Edges (Transitive Chains Exist):")
                for e in res["redundant_edges"][:15]:
                    print(f"   • {e['source']} -> {e['target']}")
            print("=" * 75 + "\n")
        return 0

    # Default full spectral report
    fiedler = engine.compute_fiedler_cut()
    sr = engine.compute_spectral_radius()
    entropy = engine.compute_von_neumann_entropy()
    fas = engine.compute_minimum_feedback_arc_set()

    full_res = {
        "algebraic_connectivity": fiedler["algebraic_connectivity"],
        "is_connected": fiedler["is_connected"],
        "cheeger_conductance": fiedler["cheeger_conductance"],
        "cheeger_bounds": [fiedler["cheeger_lower_bound"], fiedler["cheeger_upper_bound"]],
        "spectral_radius": sr["spectral_radius"],
        "epidemic_threshold": sr["epidemic_threshold"],
        "von_neumann_entropy": entropy,
        "feedback_arc_count": fas["feedback_arc_count"]
    }

    if as_json:
        print(json.dumps(full_res, indent=2))
    else:
        print("\n📐 Agtoosa2 Algebraic & Spectral Graph Analysis (DEV-052)")
        print("=" * 75)
        print(f"Algebraic Connectivity (λ₂): {full_res['algebraic_connectivity']} ({'Connected' if full_res['is_connected'] else 'Disconnected/Fragile'})")
        print(f"Cheeger Conductance h(G):    {full_res['cheeger_conductance']} (Bounds: [{fiedler['cheeger_lower_bound']}, {fiedler['cheeger_upper_bound']}])")
        print(f"Von Neumann Graph Entropy:   {full_res['von_neumann_entropy']} bits")
        print(f"Spectral Radius λ₁(A):       {full_res['spectral_radius']} (Epidemic Threshold τ_c = {full_res['epidemic_threshold']})")
        print(f"Feedback Arc Count (Cycles): {full_res['feedback_arc_count']}")
        print("=" * 75)
        print("💡 Use flags for deeper views: --cut, --radius, --fas, --transitive, --json\n")

    return 0


def cmd_graph_curvature(args: Any, workspace_root: Path) -> int:
    """Execute Forman-Ricci discrete curvature and differential geometry audit (DEV-054)."""
    db_path = get_default_db_path(workspace_root)
    if not db_path.exists():
        print(f"❌ Knowledge graph database not found at {db_path}.")
        return 1

    store = GraphStore(db_path)
    nodes = store.get_all_nodes()
    edges = store.get_all_edges()

    from agtoosa.graph.curvature import CurvatureEngine
    engine = CurvatureEngine(nodes, edges)

    top_k = getattr(args, "top", 10)
    as_json = getattr(args, "json", False)
    check_hyperbolic = getattr(args, "hyperbolic", False)

    ric_res = engine.compute_forman_ricci_curvature()
    hyp_res = engine.compute_gromov_hyperbolicity() if check_hyperbolic else None

    result: Dict[str, Any] = {
        "total_edges": ric_res["total_edges"],
        "average_curvature": ric_res["average_curvature"],
        "bottleneck_count": ric_res["bottleneck_count"],
        "cluster_edge_count": ric_res["cluster_edge_count"],
        "top_bottlenecks": ric_res["top_bottlenecks"][:top_k]
    }
    if hyp_res:
        result["hyperbolicity"] = hyp_res

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print("\n🌐 Discrete Differential Geometry: Forman-Ricci Curvature (DEV-054)")
        print("=" * 75)
        print(f"Total Edges Analyzed:        {ric_res['total_edges']}")
        print(f"Average Curvature Ric_F:     {ric_res['average_curvature']}")
        print(f"Fragile Bridges (Ric_F < 0): {ric_res['bottleneck_count']}")
        print(f"Cluster Edges (Ric_F > 0):   {ric_res['cluster_edge_count']}")

        if hyp_res:
            print(f"Gromov δ-Hyperbolicity:      δ = {hyp_res['delta']} ({'Tree-like / Hyperbolic' if hyp_res['is_tree_like'] else 'High-density grid'})")

        print(f"\n⚠️  Top {len(result['top_bottlenecks'])} Fragile Architectural Choke Points:")
        for idx, b in enumerate(result["top_bottlenecks"], start=1):
            print(f"   [{idx}] {b['source_name']} <-> {b['target_name']}")
            print(f"       Curvature: {b['curvature']} | Degrees: ({b['deg_source']}, {b['deg_target']}) | Triangles: {b['triangles']}")

        print("=" * 75 + "\n")

    return 0
