"""Tests for Agtoosa Studio HTTP Server and Two-Way Interactive Actions (Stage 23)."""

import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.request
from typing import Any, Dict, Optional

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.server import run_studio_server


class TestStudioServer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.db_path = self.workspace / ".agtoosa" / "graph.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.store = GraphStore(self.db_path)

        # Populate sample node
        node = Node(id="func:svc.py:zombie", name="zombie", node_type=NodeType.FUNCTION, path="svc.py")
        self.store.insert_batch([node], [])

        # Create source file
        self.target_file = self.workspace / "svc.py"
        self.target_file.write_text("def zombie():\n    return 'dead'\n\ndef keep():\n    return 1\n", encoding="utf-8")

        # Start test HTTP server on an ephemeral port
        self.server = run_studio_server(self.store, self.workspace, port=0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.1)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp_dir.cleanup()

    def _request(self, path: str, method: str = "GET", data: Optional[Dict[str, Any]] = None):
        url = f"http://127.0.0.1:{self.port}{path}"
        req_data = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=req_data, method=method)
        if req_data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            return resp.status, json.loads(content.decode("utf-8")) if "application/json" in resp.headers.get("Content-Type", "") else content.decode("utf-8")

    def test_get_html_and_api_graph(self):
        status, html = self._request("/")
        self.assertEqual(status, 200)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Agtoosa Studio — Architecture Command Center", html)

        status, graph_json = self._request("/api/graph")
        self.assertEqual(status, 200)
        self.assertIn("graphData", graph_json)

    def test_head_request(self):
        url = f"http://127.0.0.1:{self.port}/"
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/html", resp.headers.get("Content-Type", ""))

        url_api = f"http://127.0.0.1:{self.port}/api/graph"
        req_api = urllib.request.Request(url_api, method="HEAD")
        with urllib.request.urlopen(req_api) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("application/json", resp.headers.get("Content-Type", ""))

    def test_favicon_request(self):
        url_favicon = f"http://127.0.0.1:{self.port}/favicon.ico"
        req_get = urllib.request.Request(url_favicon, method="GET")
        with urllib.request.urlopen(req_get) as resp:
            self.assertEqual(resp.status, 204)

        req_head = urllib.request.Request(url_favicon, method="HEAD")
        with urllib.request.urlopen(req_head) as resp:
            self.assertEqual(resp.status, 204)

    def test_api_refactor_prune_and_rollback(self):
        # 1. Prune
        payload = {
            "node_id": "func:svc.py:zombie",
            "path": "svc.py",
            "name": "zombie",
            "start_line": 1,
            "end_line": 2
        }
        status, res = self._request("/api/refactor/prune", method="POST", data=payload)
        self.assertEqual(status, 200)
        self.assertEqual(res["status"], "applied")
        backup_id = res["backup_id"]

        # File should be modified
        self.assertNotIn("def zombie", self.target_file.read_text(encoding="utf-8"))
        self.assertIn("def keep", self.target_file.read_text(encoding="utf-8"))

        # 2. Check backups endpoint
        status, backups_res = self._request("/api/refactor/backups")
        self.assertEqual(status, 200)
        self.assertTrue(any(b["plan_id"] == backup_id for b in backups_res["backups"]))

        # 3. Rollback
        status, roll_res = self._request("/api/refactor/rollback", method="POST", data={"backup_id": backup_id})
        self.assertEqual(status, 200)
        self.assertTrue(roll_res["success"])

        # File should be restored
        self.assertIn("def zombie", self.target_file.read_text(encoding="utf-8"))

    def test_api_refactor_decouple(self):
        payload = {
            "proposed_interface_name": "TestServiceProtocol",
            "generated_code_stub": "class TestServiceProtocol:\n    pass\n",
            "target_path": "interfaces/test_service.py"
        }
        status, res = self._request("/api/refactor/decouple", method="POST", data=payload)
        self.assertEqual(status, 200)
        self.assertEqual(res["status"], "applied")

        gen_file = self.workspace / "interfaces" / "test_service.py"
        self.assertTrue(gen_file.exists())
        self.assertIn("class TestServiceProtocol", gen_file.read_text(encoding="utf-8"))

    def test_api_spectral_and_curvature(self):
        # 1. GET /api/spectral
        status, spectral_res = self._request("/api/spectral")
        self.assertEqual(status, 200)
        self.assertIn("algebraic_connectivity", spectral_res)
        self.assertIn("cheeger_conductance", spectral_res)
        self.assertIn("spectral_radius", spectral_res)
        self.assertIn("von_neumann_entropy", spectral_res)

        # 2. GET /api/curvature
        status, curvature_res = self._request("/api/curvature")
        self.assertEqual(status, 200)
        self.assertIn("total_edges", curvature_res)
        self.assertIn("average_curvature", curvature_res)
        self.assertIn("bottleneck_count", curvature_res)
        self.assertIn("top_bottlenecks", curvature_res)

        # 3. Verify visualizer graph data includes spectralData and curvatureData
        status, graph_json = self._request("/api/graph")
        self.assertEqual(status, 200)
        self.assertIn("spectralData", graph_json)
        self.assertIn("curvatureData", graph_json)

    def test_auto_port_fallback(self):
        # self.server is already listening on self.port
        # Requesting self.port with auto_port=True should bind to a different port
        fallback_server = run_studio_server(self.store, self.workspace, port=self.port, auto_port=True)
        try:
            new_port = fallback_server.server_address[1]
            self.assertNotEqual(new_port, self.port)
            self.assertGreater(new_port, self.port)
        finally:
            fallback_server.server_close()

    def test_strict_port_raises_on_conflict(self):
        # self.server is already listening on self.port
        # Requesting self.port with auto_port=False should raise OSError
        with self.assertRaises(OSError):
            run_studio_server(self.store, self.workspace, port=self.port, auto_port=False)


if __name__ == "__main__":
    unittest.main()
