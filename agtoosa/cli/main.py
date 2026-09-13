"""Main command-line entrypoint for Agtoosa2."""

import argparse
import sys
from pathlib import Path

# Python version guard
if sys.version_info < (3, 11):
    sys.exit(f"Error: Agtoosa2 requires Python 3.11 or newer (currently running on Python {sys.version.split()[0]}).")

# Ensure repository root is on sys.path if run directly as a script
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agtoosa import __version__
from agtoosa.cli.graph_cmd import (
    cmd_graph_build,
    cmd_graph_status,
    cmd_graph_query,
    cmd_graph_export,
)


def cmd_version(args, workspace_root: Path) -> int:
    """Display comprehensive system diagnostics and packaging version."""
    import json
    import platform
    import sqlite3
    from agtoosa.cli.graph_cmd import get_default_db_path

    is_frozen = getattr(sys, "frozen", False)
    mode = "Standalone Binary (PyInstaller)" if is_frozen else "Python Environment (Source/Package)"

    # Test SQLite FTS5 capability
    fts5_enabled = False
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content);")
        conn.close()
        fts5_enabled = True
    except Exception:
        pass

    db_path = get_default_db_path(workspace_root)
    graph_info = {"db_exists": False}
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            node_count = conn.execute("SELECT COUNT(*) FROM nodes;").fetchone()[0]
            edge_count = conn.execute("SELECT COUNT(*) FROM edges;").fetchone()[0]
            conn.close()
            graph_info = {
                "db_exists": True,
                "path": str(db_path),
                "size_bytes": db_path.stat().st_size,
                "node_count": node_count,
                "edge_count": edge_count,
            }
        except Exception:
            pass

    diag_data = {
        "version": __version__,
        "execution_mode": mode,
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python_version": sys.version.split()[0],
        "sqlite_version": sqlite3.sqlite_version,
        "fts5_enabled": fts5_enabled,
        "workspace_root": str(workspace_root),
        "graph": graph_info,
    }

    if getattr(args, "json", False):
        print(json.dumps(diag_data, indent=2))
        return 0

    print(f"🏛️  Agtoosa2 v{__version__} — Unified Graph-Native Engineering Operating System")
    print("System & Runtime Diagnostics:")
    print(f"   • Execution Mode:    {mode}")
    print(f"   • Platform:          {diag_data['platform']}")
    print(f"   • Python Runtime:    {diag_data['python_version']}")
    print(f"   • SQLite Engine:     v{diag_data['sqlite_version']} (FTS5: {'✅ Supported' if fts5_enabled else '❌ Missing'})")
    print(f"   • Active Workspace:  {workspace_root}")

    if graph_info.get("db_exists"):
        kb_size = int(graph_info["size_bytes"]) / 1024
        print(f"   • Knowledge Graph:   {db_path.name} ({kb_size:.1f} KB, {graph_info['node_count']} nodes, {graph_info['edge_count']} edges)")
    else:
        print(f"   • Knowledge Graph:   Not initialized (run 'agtoosa graph build')")

    return 0


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="agtoosa",
        description="Agtoosa2: Unified Graph-Native Engineering Operating System"
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"agtoosa {__version__}"
    )
    parser.add_argument(
        "-C", "--workspace", type=str, default=".", help="Target workspace root (default: current directory)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available command families")

    # agtoosa graph ...
    graph_parser = subparsers.add_parser("graph", help="Graph-native knowledge engine operations")
    graph_sub = graph_parser.add_subparsers(dest="graph_action", required=True)

    # agtoosa graph build
    build_p = graph_sub.add_parser("build", help="Index workspace into local knowledge graph")
    build_p.add_argument("--clean", action="store_true", help="Clean rebuild of all graph tables")

    # agtoosa graph status
    graph_sub.add_parser("status", help="Display graph status and health metrics")

    # agtoosa graph query <query>
    query_p = graph_sub.add_parser("query", help="Full-text search across indexed nodes")
    query_p.add_argument("query", type=str, help="Search query string")
    query_p.add_argument("-n", "--limit", type=int, default=15, help="Maximum results to return")
    query_p.add_argument("--hybrid", action="store_true", help="Perform hybrid search combining FTS5 lexical ranking and dense vector similarity")

    # agtoosa graph explain <target>
    explain_p = graph_sub.add_parser("explain", help="Inspect an entity's definition, callers, and callees")
    explain_p.add_argument("target", type=str, help="Target symbol or file name")
    explain_p.add_argument("--json", action="store_true", help="Output as JSON")

    # agtoosa graph path <source> <target>
    path_p = graph_sub.add_parser("path", help="Find directed path between two entities")
    path_p.add_argument("source", type=str, help="Starting node name")
    path_p.add_argument("target", type=str, help="Destination node name")

    # agtoosa graph impact <target>
    impact_p = graph_sub.add_parser("impact", help="Calculate upstream blast radius when an entity changes")
    impact_p.add_argument("target", type=str, help="Modified symbol or file name")
    impact_p.add_argument("-d", "--depth", type=int, default=3, help="Max traversal depth (default: 3)")
    impact_p.add_argument("--federated", action="store_true", help="Analyze blast radius across local and federated repositories")
    impact_p.add_argument("--production", action="store_true", help="Weight blast radius with runtime telemetry traffic and error rates")
    impact_p.add_argument("--json", action="store_true", help="Output as JSON")

    # agtoosa graph symbols <file>
    symbols_p = graph_sub.add_parser("symbols", help="List all symbols in a file with line ranges, caller counts, and blast radius")
    symbols_p.add_argument("file", type=str, help="Target file path")
    symbols_p.add_argument("--json", action="store_true", help="Output as JSON")

    # agtoosa graph export
    export_p = graph_sub.add_parser("export", help="Export graph to JSON, Obsidian, GraphML, Cypher, or DOT")
    export_p.add_argument("-o", "--output", type=str, help="Path to write export output")
    export_p.add_argument("-f", "--format", type=str, default="json", choices=["json", "obsidian", "graphml", "cypher", "dot"], help="Export format (default: json)")

    # agtoosa graph view
    view_p = graph_sub.add_parser("view", help="Generate standalone offline HTML graph visualizer")
    view_p.add_argument("-o", "--output", type=str, help="Path to write HTML file (default: .agtoosa/graph_view.html)")
    view_p.add_argument("--filter", type=str, help="Filter by node type (e.g. class, function, story)")
    view_p.add_argument("--open", action="store_true", help="Automatically open generated visualizer in web browser")
    view_p.add_argument("--serve", action="store_true", help="Start interactive Agtoosa Studio HTTP server with 2-way refactoring actions")
    view_p.add_argument("--port", type=int, default=8080, help="Port for Agtoosa Studio server (default: 8080)")

    # agtoosa graph report
    report_p = graph_sub.add_parser("report", help="Generate architecture health, cycle detection, and centrality report")
    report_p.add_argument("-o", "--output", type=str, help="Path to write report output")
    report_p.add_argument("-f", "--format", type=str, default="text", choices=["text", "markdown", "json"], help="Report format (default: text)")

    # agtoosa graph watch
    watch_p = graph_sub.add_parser("watch", help="Continuously monitor workspace and incrementally sync graph")
    watch_p.add_argument("--interval", type=float, default=1.0, help="Poll interval in seconds (default: 1.0)")
    watch_p.add_argument("--debounce", type=float, default=0.5, help="Debounce window in seconds (default: 0.5)")

    # agtoosa graph hooks
    hooks_p = graph_sub.add_parser("hooks", help="Manage automated Agtoosa Git hooks")
    hooks_p.add_argument("hook_action", type=str, nargs="?", default="status", choices=["install", "remove", "status"], help="Action: install, remove, or status")

    # agtoosa graph embeddings
    emb_p = graph_sub.add_parser("embeddings", help="Manage dense semantic vector embeddings")
    emb_sub = emb_p.add_subparsers(dest="embeddings_action", required=True)
    emb_build = emb_sub.add_parser("build", help="Build or rebuild vector embeddings for all graph nodes")
    emb_build.add_argument("--clean", action="store_true", help="Clean rebuild of all stored embeddings")
    emb_sub.add_parser("status", help="Report vector embeddings index status")

    # agtoosa graph federate
    fed_p = graph_sub.add_parser("federate", help="Cross-repository graph federation and contract management")
    fed_sub = fed_p.add_subparsers(dest="federate_action", required=True)

    fed_add = fed_sub.add_parser("add", help="Register a federated repository (local path or git URL)")
    fed_add.add_argument("name", type=str, help="Repository unique alias")
    fed_add.add_argument("uri", type=str, help="Local directory path or Git clone URL")
    fed_add.add_argument("-s", "--schema", type=str, help="Path to API schema contract (OpenAPI, Proto, GraphQL)")

    fed_list = fed_sub.add_parser("list", help="List registered federated repositories")
    fed_list.add_argument("--json", action="store_true", help="Output list as JSON")

    fed_sync = fed_sub.add_parser("sync", help="Synchronize and ingest federated repositories and contracts")
    fed_sync.add_argument("name", type=str, nargs="?", help="Specific repository alias to sync (or all if omitted)")
    fed_sync.add_argument("--clean", action="store_true", help="Clean rebuild of federated repo nodes")

    fed_rm = fed_sub.add_parser("remove", help="Remove a federated repository and purge its nodes")
    fed_rm.add_argument("name", type=str, help="Repository unique alias to remove")

    # agtoosa graph routes
    routes_p = graph_sub.add_parser("routes", help="List discovered HTTP API endpoints and bound handler functions")
    routes_p.add_argument("-m", "--method", type=str, choices=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"], help="Filter by HTTP method")
    routes_p.add_argument("--json", action="store_true", help="Output routes as JSON")

    # agtoosa graph di <symbol>
    di_p = graph_sub.add_parser("di", help="Trace dependency injection providers and consumers for a symbol")
    di_p.add_argument("symbol", type=str, help="Target function, class, or service symbol")
    di_p.add_argument("--json", action="store_true", help="Output DI graph as JSON")

    # agtoosa graph events
    events_p = graph_sub.add_parser("events", help="List message queue topics, pub/sub channels, task queues, and async lineage")
    events_p.add_argument("-t", "--topic", type=str, help="Filter by topic or queue name")
    events_p.add_argument("--json", action="store_true", help="Output event lineage as JSON")


    # agtoosa context compile <target>
    context_parser = subparsers.add_parser("context", help="Context Compilation v2 (Graph RAG for AI Agents)")
    context_sub = context_parser.add_subparsers(dest="context_action", required=True)
    compile_p = context_sub.add_parser("compile", help="Compile bounded context pack for task/story")
    compile_p.add_argument("target", type=str, help="Target Story, Task, or Symbol name")
    compile_p.add_argument("-r", "--radius", type=int, default=2, help="Context extraction radius (default: 2)")
    compile_p.add_argument("-o", "--output", type=str, help="Write context pack to file")
    compile_p.add_argument("--hybrid", action="store_true", help="Enable Hybrid GraphRAG v2 combining lexical FTS5, vector similarity, and structural graph traversal")

    # agtoosa review ...
    review_parser = subparsers.add_parser("review", help="Review working tree changes against graph invariants")
    review_parser.add_argument("--diff", type=str, help="Diff against Git base ref (e.g. main, HEAD~1)")
    review_parser.add_argument("--strict", action="store_true", help="Fail with non-zero exit code on any drift warning")
    review_parser.add_argument("--json", action="store_true", help="Output review report as JSON")
    review_sub = review_parser.add_subparsers(dest="review_action")

    remember_p = review_sub.add_parser("remember", help="Record architectural decision into project memory")
    remember_p.add_argument("rule", type=str, help="Architectural rule or invariant to remember")
    remember_p.add_argument("-d", "--domain", type=str, help="Associated domain or subsystem")
    remember_p.add_argument("-t", "--tags", type=str, help="Comma-separated tags")

    reflect_p = review_sub.add_parser("reflect", help="View stored architectural rules and memory")
    reflect_p.add_argument("-d", "--domain", type=str, help="Filter by domain")

    boundaries_p = review_sub.add_parser("boundaries", help="Enforce monorepo package encapsulation and import boundaries")
    boundaries_p.add_argument("--path", type=str, default=".", help="Workspace root path (default: current dir)")
    boundaries_p.add_argument("--strict", action="store_true", help="Fail if any warnings are detected")
    boundaries_p.add_argument("--json", action="store_true", help="Output boundaries report as JSON")

    # agtoosa ci ...
    ci_parser = subparsers.add_parser("ci", help="CI/CD Quality Gate & automated PR verification")
    ci_sub = ci_parser.add_subparsers(dest="ci_action", required=True)

    ci_review_p = ci_sub.add_parser("review", help="Run CI architectural drift review and generate PR comment")
    ci_review_p.add_argument("--base-ref", type=str, default="origin/main", help="Base git ref for PR diff (default: origin/main)")
    ci_review_p.add_argument("--strict", action="store_true", help="Fail with non-zero exit code if warnings or alarms are present")
    ci_review_p.add_argument("--output-comment", type=str, help="Path to write GitHub PR Markdown comment (e.g. pr-comment.md)")
    ci_review_p.add_argument("--post-comment", action="store_true", help="Post or update sticky PR comment via GitHub REST API")
    ci_review_p.add_argument("--github-token", type=str, help="GitHub token for PR comment posting (defaults to $GITHUB_TOKEN)")
    ci_review_p.add_argument("--pr-number", type=int, help="Pull Request number (defaults to $PR_NUMBER or CI detection)")
    ci_review_p.add_argument("--repo", type=str, help="GitHub repository owner/repo (defaults to $GITHUB_REPOSITORY)")

    ci_check_p = ci_sub.add_parser("check", help="Fast CI gate check returning 0 on clean architecture, 1 on violation")
    ci_check_p.add_argument("--base-ref", type=str, default="origin/main", help="Base git ref for diff")
    ci_check_p.add_argument("--strict", action="store_true", help="Treat warnings as failures")

    ci_pr_bot_p = ci_sub.add_parser("pr-bot", help="Run PR Blast Radius & Breaking Schema Review Bot")
    ci_pr_bot_p.add_argument("--base", type=str, default="origin/main", help="Base git ref for PR diff (default: origin/main)")
    ci_pr_bot_p.add_argument("--pr", type=int, help="Pull Request number (defaults to $PR_NUMBER or CI detection)")
    ci_pr_bot_p.add_argument("--post-comment", action="store_true", help="Post or update sticky PR comment via GitHub REST API")
    ci_pr_bot_p.add_argument("-o", "--output", type=str, help="Path to write GitHub PR Markdown comment")
    ci_pr_bot_p.add_argument("--json", action="store_true", help="Output analysis data as JSON")
    ci_pr_bot_p.add_argument("--fail-on-p0", action="store_true", help="Fail if P0_CRITICAL production traffic is impacted")
    ci_pr_bot_p.add_argument("--strict", action="store_true", help="Fail if any warnings or errors are present")

    # agtoosa version
    version_parser = subparsers.add_parser("version", help="Display version and runtime diagnostic information")
    version_parser.add_argument("--json", action="store_true", help="Output diagnostic information as JSON")

    # agtoosa ship <story>
    ship_parser = subparsers.add_parser("ship", help="Verify proof graph and ship story")
    ship_parser.add_argument("story", type=str, help="Target Story ID to verify and ship")

    # agtoosa telemetry ...
    telem_parser = subparsers.add_parser("telemetry", help="Runtime observability, OpenTelemetry ingestion, and heatmaps")
    telem_sub = telem_parser.add_subparsers(dest="telem_action", required=True)

    ingest_p = telem_sub.add_parser("ingest", help="Ingest OpenTelemetry trace spans or profiler data")
    ingest_p.add_argument("file", type=str, help="Path to OpenTelemetry JSON, Py-Spy, or metrics JSON")
    ingest_p.add_argument("--format", type=str, choices=["otel", "pyspy", "generic"], help="Format hint")

    status_p = telem_sub.add_parser("status", help="Display runtime telemetry tracking stats")
    status_p.add_argument("--json", action="store_true", help="Output status as JSON")

    heatmap_p = telem_sub.add_parser("heatmap", help="Compute execution hotspot heatmaps across symbols")
    heatmap_p.add_argument("--top", type=int, default=20, help="Top N hotspots to display (default: 20)")
    heatmap_p.add_argument("--json", action="store_true", help="Output heatmap data as JSON")

    clear_p = telem_sub.add_parser("clear", help="Clear all stored runtime telemetry")

    # agtoosa refactor ...
    refactor_parser = subparsers.add_parser("refactor", help="Autonomous architectural refactoring and cycle decoupling")
    refactor_sub = refactor_parser.add_subparsers(dest="refactor_action", required=True)

    decouple_p = refactor_sub.add_parser("decouple", help="Generate dependency injection and decoupling blueprints for cyclic dependencies")
    decouple_p.add_argument("--json", action="store_true", help="Output blueprints as JSON")
    decouple_p.add_argument("--apply", action="store_true", help="Apply decoupling interface generation to workspace")
    decouple_p.add_argument("--dry-run", action="store_true", help="Preview unified diff without modifying files")

    dead_code_p = refactor_sub.add_parser("dead-code", help="Identify dead code / zombie symbols and generate safe deletion blueprints")
    dead_code_p.add_argument("--json", action="store_true", help="Output dead code report as JSON")
    dead_code_p.add_argument("--min-confidence", type=str, default="low", choices=["low", "medium", "high"], help="Minimum confidence threshold (default: low)")
    dead_code_p.add_argument("--apply", action="store_true", help="Apply safe dead-code pruning to workspace")
    dead_code_p.add_argument("--dry-run", action="store_true", help="Preview unified diff without modifying files")

    rollback_p = refactor_sub.add_parser("rollback", help="Roll back an applied refactoring using backup snapshot ID")
    rollback_p.add_argument("backup_id", type=str, help="Backup snapshot ID to restore")

    refactor_sub.add_parser("backups", help="List available refactoring rollback backups")

    # agtoosa guard ...
    guard_parser = subparsers.add_parser("guard", help="Pre-push architectural guard, drift linter & background daemon")
    guard_parser.add_argument("--strict", action="store_true", help="Fail with exit code 1 on any warning or threshold breach")
    guard_parser.add_argument("--max-blast-radius", type=int, default=5, help="Maximum allowed upstream dependents before alert (default: 5)")
    guard_parser.add_argument("--base-ref", type=str, help="Base Git ref for diff evaluation (e.g. origin/main)")
    guard_parser.add_argument("--daemon", action="store_true", help="Run in continuous background monitoring daemon mode")
    guard_parser.add_argument("--interval", type=float, default=3.0, help="Daemon polling interval in seconds (default: 3.0)")
    guard_parser.add_argument("--install-hooks", action="store_true", help="Install pre-push and pre-commit Git hooks")
    guard_parser.add_argument("--uninstall-hooks", action="store_true", help="Remove Agtoosa Git hooks")
    guard_parser.add_argument("--status", action="store_true", help="Query existing cached guard status (.agtoosa/guard_status.json)")
    guard_parser.add_argument("-C", "--workspace", type=str, default=".", help="Target workspace root")
    guard_parser.add_argument("--json", action="store_true", help="Output guard report as JSON")

    # agtoosa mcp
    subparsers.add_parser("mcp", help="Launch native Model Context Protocol (MCP) server on stdio")

    args = parser.parse_args(argv)

    workspace_root = Path(args.workspace).resolve()

    if args.command == "graph":
        if args.graph_action == "build":
            return cmd_graph_build(args, workspace_root)
        elif args.graph_action == "status":
            return cmd_graph_status(args, workspace_root)
        elif args.graph_action == "query":
            return cmd_graph_query(args, workspace_root)
        elif args.graph_action == "explain":
            from agtoosa.cli.graph_cmd import cmd_graph_explain
            return cmd_graph_explain(args, workspace_root)
        elif args.graph_action == "path":
            from agtoosa.cli.graph_cmd import cmd_graph_path
            return cmd_graph_path(args, workspace_root)
        elif args.graph_action == "impact":
            from agtoosa.cli.graph_cmd import cmd_graph_impact
            return cmd_graph_impact(args, workspace_root)
        elif args.graph_action == "symbols":
            from agtoosa.cli.graph_cmd import cmd_graph_symbols
            return cmd_graph_symbols(args, workspace_root)
        elif args.graph_action == "export":
            return cmd_graph_export(args, workspace_root)
        elif args.graph_action == "view":
            from agtoosa.cli.graph_cmd import cmd_graph_view
            return cmd_graph_view(args, workspace_root)
        elif args.graph_action == "report":
            from agtoosa.cli.graph_cmd import cmd_graph_report
            return cmd_graph_report(args, workspace_root)
        elif args.graph_action == "watch":
            from agtoosa.cli.graph_cmd import cmd_graph_watch
            return cmd_graph_watch(args, workspace_root)
        elif args.graph_action == "hooks":
            from agtoosa.cli.graph_cmd import cmd_graph_hooks
            return cmd_graph_hooks(args, workspace_root)
        elif args.graph_action == "embeddings":
            if args.embeddings_action == "build":
                from agtoosa.cli.graph_cmd import cmd_graph_embeddings_build
                return cmd_graph_embeddings_build(args, workspace_root)
            elif args.embeddings_action == "status":
                from agtoosa.cli.graph_cmd import cmd_graph_embeddings_status
                return cmd_graph_embeddings_status(args, workspace_root)
        elif args.graph_action == "federate":
            from agtoosa.cli.graph_cmd import cmd_graph_federate
            return cmd_graph_federate(args, workspace_root)
        elif args.graph_action == "routes":
            from agtoosa.cli.graph_cmd import cmd_graph_routes
            return cmd_graph_routes(args, workspace_root)
        elif args.graph_action == "di":
            from agtoosa.cli.graph_cmd import cmd_graph_di
            return cmd_graph_di(args, workspace_root)
        elif args.graph_action == "events":
            from agtoosa.cli.graph_cmd import cmd_graph_events
            return cmd_graph_events(args, workspace_root)
    elif args.command == "context":

        from agtoosa.cli.lifecycle_cmd import cmd_context_compile
        return cmd_context_compile(args, workspace_root)
    elif args.command == "review":
        if getattr(args, "review_action", None) == "remember":
            from agtoosa.cli.lifecycle_cmd import cmd_review_remember
            return cmd_review_remember(args, workspace_root)
        elif getattr(args, "review_action", None) == "reflect":
            from agtoosa.cli.lifecycle_cmd import cmd_review_reflect
            return cmd_review_reflect(args, workspace_root)
        elif getattr(args, "review_action", None) == "boundaries":
            from agtoosa.cli.lifecycle_cmd import cmd_review_boundaries
            return cmd_review_boundaries(args, workspace_root)
        else:
            from agtoosa.cli.lifecycle_cmd import cmd_lifecycle_review
            return cmd_lifecycle_review(args, workspace_root)
    elif args.command == "ci":
        if args.ci_action == "review":
            from agtoosa.cli.lifecycle_cmd import cmd_ci_review
            return cmd_ci_review(args, workspace_root)
        elif args.ci_action == "check":
            from agtoosa.cli.lifecycle_cmd import cmd_ci_check
            return cmd_ci_check(args, workspace_root)
        elif args.ci_action == "pr-bot":
            from agtoosa.cli.lifecycle_cmd import cmd_ci_pr_bot
            return cmd_ci_pr_bot(args, workspace_root)
    elif args.command == "ship":
        from agtoosa.cli.lifecycle_cmd import cmd_lifecycle_ship
        return cmd_lifecycle_ship(args, workspace_root)
    elif args.command == "telemetry":
        from agtoosa.cli.observability_cmd import cmd_telemetry
        return cmd_telemetry(args, workspace_root)
    elif args.command == "refactor":
        if args.refactor_action == "decouple":
            from agtoosa.cli.refactor_cmd import cmd_refactor_decouple
            return cmd_refactor_decouple(args, workspace_root)
        elif args.refactor_action == "dead-code":
            from agtoosa.cli.refactor_cmd import cmd_refactor_dead_code
            return cmd_refactor_dead_code(args, workspace_root)
        elif args.refactor_action == "rollback":
            from agtoosa.cli.refactor_cmd import cmd_refactor_rollback
            return cmd_refactor_rollback(args, workspace_root)
        elif args.refactor_action == "backups":
            from agtoosa.cli.refactor_cmd import cmd_refactor_backups
            return cmd_refactor_backups(args, workspace_root)
    elif args.command == "guard":
        from agtoosa.cli.guard_cmd import cmd_guard
        return cmd_guard(args, workspace_root)
    elif args.command == "version":
        return cmd_version(args, workspace_root)
    elif args.command == "mcp":
        from agtoosa.mcp.server import MCPServer
        server = MCPServer(workspace_root)
        server.run_stdio()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
