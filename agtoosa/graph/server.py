"""Lightweight Interactive HTTP Server for Agtoosa Studio (Stage 23).

Exposes two-way interactive studio actions:
- GET /: Serves live Agtoosa Studio visualizer.
- GET /api/graph: Dynamic graph data payload.
- POST /api/refactor/prune: Executes safe symbol deletion directly in workspace.
- POST /api/refactor/decouple: Generates and writes interface abstraction.
- POST /api/refactor/rollback: Restores original files from backup snapshot.
- GET /api/refactor/backups: Lists all rollback snapshots.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional
import urllib.parse

from agtoosa.graph.store import GraphStore
from agtoosa.graph.visualizer import VisualizerEngine
from agtoosa.refactor.engine import RefactorEngine, PatchPlan, PatchAction


class StudioHTTPHandler(BaseHTTPRequestHandler):
    store: GraphStore
    workspace_root: Path

    def _send_json(self, data: Any, status: int = 200) -> None:
        payload = json.dumps(data).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_HEAD(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/graph_view.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return
        elif parsed.path in ("/api/graph", "/api/refactor/backups"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return
        elif parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self.send_error(404, "Not Found")

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path in ("/", "/graph_view.html"):
            visualizer = VisualizerEngine(self.store)
            html = visualizer.generate_html()
            payload = html.encode("utf-8")
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            return

        elif parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        elif parsed.path == "/api/graph":
            visualizer = VisualizerEngine(self.store)
            data = visualizer.extract_graph_data()
            self._send_json(data)
            return

        elif parsed.path == "/api/refactor/backups":
            refactor_engine = RefactorEngine(self.workspace_root)
            backups = refactor_engine.list_backups()
            self._send_json({"backups": backups})
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            req_data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            req_data = {}

        if parsed.path == "/api/refactor/prune":
            # Expects: { node_id, path, name, start_line, end_line, dry_run? }
            rel_path = req_data.get("path")
            name = req_data.get("name")
            start_line = req_data.get("start_line", 1)
            end_line = req_data.get("end_line", 1)
            dry_run = bool(req_data.get("dry_run", False))

            if not rel_path or not name:
                self._send_json({"error": "Missing required fields 'path' and 'name'"}, status=400)
                return

            action = PatchAction(
                action_type="DELETE_SYMBOL",
                file_path=rel_path,
                symbol_name=name,
                start_line=start_line,
                end_line=end_line,
                reason=f"Interactive Studio Safe Prune for symbol '{name}'"
            )
            plan = PatchPlan(
                plan_id=f"prune_studio_{name}_{start_line}",
                description=f"Studio 1-click safe prune: {name}",
                actions=[action]
            )

            refactor_engine = RefactorEngine(self.workspace_root)
            result = refactor_engine.apply_plan(plan, dry_run=dry_run)
            self._send_json(result)
            return

        elif parsed.path == "/api/refactor/decouple":
            # Expects: { strategy_type, proposed_interface_name, generated_code_stub, target_path? }
            strategy_name = req_data.get("proposed_interface_name", "DecoupledInterface")
            code_stub = req_data.get("generated_code_stub", "")
            target_path = req_data.get("target_path")
            dry_run = bool(req_data.get("dry_run", False))

            if not target_path:
                clean_name = strategy_name.lower().replace("interface", "").replace("protocol", "")
                target_path = f"agtoosa/core/interfaces/{clean_name}.py"

            action = PatchAction(
                action_type="INSERT_INTERFACE",
                file_path=target_path,
                symbol_name=strategy_name,
                code_content=code_stub,
                reason="Interactive Studio Cycle Decoupling Interface Generation"
            )
            plan = PatchPlan(
                plan_id=f"decouple_studio_{strategy_name}",
                description=f"Studio 1-click cycle decoupler: {strategy_name}",
                actions=[action]
            )

            refactor_engine = RefactorEngine(self.workspace_root)
            result = refactor_engine.apply_plan(plan, dry_run=dry_run)
            self._send_json(result)
            return

        elif parsed.path == "/api/refactor/rollback":
            backup_id = req_data.get("backup_id")
            if not backup_id:
                self._send_json({"error": "Missing backup_id"}, status=400)
                return

            refactor_engine = RefactorEngine(self.workspace_root)
            success = refactor_engine.rollback(backup_id)
            self._send_json({"success": success, "backup_id": backup_id})
            return

        self.send_error(404, "Not Found")

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy HTTP request logging
        pass


def run_studio_server(
    store: GraphStore,
    workspace_root: Path,
    port: int = 8080,
    host: str = "127.0.0.1"
) -> HTTPServer:
    """Create and start the Agtoosa Studio HTTP server."""
    handler_cls = type(
        "ConfiguredStudioHandler",
        (StudioHTTPHandler,),
        {"store": store, "workspace_root": workspace_root}
    )
    server = HTTPServer((host, port), handler_cls)
    return server
