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

    # agtoosa graph explain <target>
    explain_p = graph_sub.add_parser("explain", help="Inspect an entity's definition, callers, and callees")
    explain_p.add_argument("target", type=str, help="Target symbol or file name")

    # agtoosa graph path <source> <target>
    path_p = graph_sub.add_parser("path", help="Find directed path between two entities")
    path_p.add_argument("source", type=str, help="Starting node name")
    path_p.add_argument("target", type=str, help="Destination node name")

    # agtoosa graph impact <target>
    impact_p = graph_sub.add_parser("impact", help="Calculate upstream blast radius when an entity changes")
    impact_p.add_argument("target", type=str, help="Modified symbol or file name")
    impact_p.add_argument("-d", "--depth", type=int, default=3, help="Max traversal depth (default: 3)")

    # agtoosa graph export
    export_p = graph_sub.add_parser("export", help="Export graph to JSON, Obsidian, GraphML, Cypher, or DOT")
    export_p.add_argument("-o", "--output", type=str, help="Path to write export output")
    export_p.add_argument("-f", "--format", type=str, default="json", choices=["json", "obsidian", "graphml", "cypher", "dot"], help="Export format (default: json)")

    # agtoosa graph view
    view_p = graph_sub.add_parser("view", help="Generate standalone offline HTML graph visualizer")
    view_p.add_argument("-o", "--output", type=str, help="Path to write HTML file (default: .agtoosa/graph_view.html)")
    view_p.add_argument("--filter", type=str, help="Filter by node type (e.g. class, function, story)")
    view_p.add_argument("--open", action="store_true", help="Automatically open generated visualizer in web browser")

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

    # agtoosa context compile <target>
    context_parser = subparsers.add_parser("context", help="Context Compilation v2 (Graph RAG for AI Agents)")
    context_sub = context_parser.add_subparsers(dest="context_action", required=True)
    compile_p = context_sub.add_parser("compile", help="Compile bounded context pack for task/story")
    compile_p.add_argument("target", type=str, help="Target Story, Task, or Symbol name")
    compile_p.add_argument("-r", "--radius", type=int, default=2, help="Context extraction radius (default: 2)")
    compile_p.add_argument("-o", "--output", type=str, help="Write context pack to file")

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

    # agtoosa ship <story>
    ship_parser = subparsers.add_parser("ship", help="Verify proof graph and ship story")
    ship_parser.add_argument("story", type=str, help="Target Story ID to verify and ship")

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
        else:
            from agtoosa.cli.lifecycle_cmd import cmd_lifecycle_review
    elif args.command == "ci":
        if args.ci_action == "review":
            from agtoosa.cli.lifecycle_cmd import cmd_ci_review
            return cmd_ci_review(args, workspace_root)
        elif args.ci_action == "check":
            from agtoosa.cli.lifecycle_cmd import cmd_ci_check
            return cmd_ci_check(args, workspace_root)
    elif args.command == "ship":
        from agtoosa.cli.lifecycle_cmd import cmd_lifecycle_ship
        return cmd_lifecycle_ship(args, workspace_root)
    elif args.command == "mcp":
        from agtoosa.mcp.server import MCPServer
        server = MCPServer(workspace_root)
        server.run_stdio()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
