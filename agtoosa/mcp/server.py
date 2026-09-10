"""Native Model Context Protocol (MCP) Server for Agtoosa2."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from agtoosa.graph.store import GraphStore
from agtoosa.graph.query import explain_node, compute_impact
from agtoosa.core.context_compiler import ContextCompiler
from agtoosa.core.lifecycle import LifecycleEngine
from agtoosa.cli.graph_cmd import get_default_db_path


class MCPServer:
    """JSON-RPC 2.0 stdio server providing Agtoosa graph tools to AI assistants."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.db_path = get_default_db_path(workspace_root)
        self.store = GraphStore(self.db_path)
        self.compiler = ContextCompiler(self.store)
        self.lifecycle = LifecycleEngine(self.store, workspace_root)
        self.subscriptions: Set[str] = set()

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "agtoosa_search_graph",
                "description": "Full-text search across all codebase symbols, docstrings, and specifications.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query string"},
                        "limit": {"type": "integer", "description": "Maximum matches to return", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "agtoosa_get_symbol",
                "description": "Inspect an exact symbol or file: definition, docstring, callers, and callees.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Symbol name or file path"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "agtoosa_query_impact",
                "description": "Calculate upstream blast radius (who calls or depends on target) before making edits.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Modified symbol or file"},
                        "depth": {"type": "integer", "description": "Max traversal depth", "default": 3}
                    },
                    "required": ["target"]
                }
            },
            {
                "name": "agtoosa_get_task_context",
                "description": "Compile a bounded, high-signal prompt pack for an active task or story.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_or_story": {"type": "string", "description": "Story ID (e.g. DEV-001) or Task ID"}
                    },
                    "required": ["task_or_story"]
                }
            },
            {
                "name": "agtoosa_verify_ship",
                "description": "Verify that all acceptance criteria and tasks for a story are complete.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "story_id": {"type": "string", "description": "Story ID to verify"}
                    },
                    "required": ["story_id"]
                }
            },
            {
                "name": "agtoosa_watch_status",
                "description": "Get real-time continuous watcher status, graph stats, and pending drift findings.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> str:
        if name == "agtoosa_search_graph":
            query = args.get("query", "")
            limit = args.get("limit", 10)
            results = self.store.query_fts(query, limit=limit)
            return json.dumps(results, indent=2)

        elif name == "agtoosa_get_symbol":
            symbol = args.get("symbol", "")
            res = explain_node(self.store, symbol)
            return json.dumps(res or {"error": f"Symbol '{symbol}' not found"}, indent=2)

        elif name == "agtoosa_query_impact":
            target = args.get("target", "")
            raw_depth = args.get("depth", 3)
            try:
                depth = max(1, min(int(raw_depth), 5))
            except (ValueError, TypeError):
                depth = 3
            res = compute_impact(self.store, target, max_depth=depth)
            return json.dumps(res or {"error": f"Target '{target}' not found"}, indent=2)

        elif name == "agtoosa_get_task_context":
            target = args.get("task_or_story", "")
            pack = self.compiler.compile_context(target)
            return pack or f"Target '{target}' not found in knowledge graph."

        elif name == "agtoosa_verify_ship":
            story_id = args.get("story_id", "")
            can_ship, reasons = self.lifecycle.verify_ship_proof(story_id)
            return json.dumps({"approved": can_ship, "reasons": reasons}, indent=2)

        elif name == "agtoosa_watch_status":
            stats = self.store.get_stats().to_dict()
            review_res = self.lifecycle.review()
            return json.dumps({
                "status": "active",
                "graph_stats": stats,
                "review_verdict": review_res.get("verdict"),
                "modified_files": review_res.get("modified_files", []),
                "findings": review_res.get("findings", [])
            }, indent=2)

        return json.dumps({"error": f"Unknown tool: {name}"})

    def notify_resource_updated(self, uri: str) -> None:
        """Send a JSON-RPC notification to clients when a subscribed resource updates."""
        if uri in self.subscriptions:
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/resources/updated",
                "params": {"uri": uri}
            }
            try:
                sys.stdout.write(json.dumps(notification) + "\n")
                sys.stdout.flush()
            except OSError:
                pass

    def handle_message(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {"subscribe": True, "listChanged": True}
                    },
                    "serverInfo": {"name": "agtoosa-mcp", "version": "0.2.1"}
                }
            }
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": self.get_tool_definitions()}
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            output_text = self.handle_tool_call(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": output_text}]
                }
            }
        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "resources": [
                        {
                            "uri": "agtoosa://graph/stats",
                            "name": "Knowledge Graph Stats",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": "agtoosa://graph/review",
                            "name": "Live Review Verdict",
                            "mimeType": "application/json"
                        }
                    ]
                }
            }
        elif method == "resources/subscribe":
            uri = params.get("uri")
            if uri:
                self.subscriptions.add(uri)
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
        elif method == "resources/unsubscribe":
            uri = params.get("uri")
            if uri and uri in self.subscriptions:
                self.subscriptions.remove(uri)
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
        elif method == "resources/read":
            uri = params.get("uri")
            if uri == "agtoosa://graph/stats":
                text = json.dumps(self.store.get_stats().to_dict(), indent=2)
            elif uri == "agtoosa://graph/review":
                text = json.dumps(self.lifecycle.review(), indent=2)
            else:
                text = json.dumps({"error": f"Resource not found: {uri}"})
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "contents": [{"uri": uri, "mimeType": "application/json", "text": text}]
                }
            }

        if msg_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }
        return None
        return None

    MAX_LINE_BYTES = 1024 * 1024  # 1MB limit to prevent DoS memory exhaustion

    def run_stdio(self) -> None:
        """Run standard stdio message loop with input bounds."""
        for line in sys.stdin:
            if len(line) > self.MAX_LINE_BYTES:
                continue
            line_str = line.strip()
            if not line_str:
                continue
            try:
                msg = json.loads(line_str)
                resp = self.handle_message(msg)
                if resp:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                continue
