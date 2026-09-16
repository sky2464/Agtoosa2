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
