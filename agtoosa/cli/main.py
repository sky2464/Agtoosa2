"""Main command-line entrypoint for Agtoosa2."""

import argparse
import sys
from pathlib import Path

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
    export_p = graph_sub.add_parser("export", help="Export graph to JSON format")
    export_p.add_argument("-o", "--output", type=str, help="Path to write JSON export")

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

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
