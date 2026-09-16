"""Unit and integration tests for DEV-025: Framework Dependency Injection & Dynamic Routes."""

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

from agtoosa.cli.main import main
from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.graph.query import query_routes, query_di
from agtoosa.mcp.server import MCPServer
from agtoosa.parser import ParserEngine
from agtoosa.parser.python_parser import PythonASTParser
from agtoosa.parser.js_ts_parser import JavaScriptTypeScriptParser


class TestFrameworkSemantics(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.db_path = self.workspace / ".agtoosa" / "graph.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.store = GraphStore(self.db_path)
        self.engine = ParserEngine()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_fastapi_routes_and_depends(self):
        """FastAPI route decorators and Depends() dependency injection extraction."""
        py_file = self.workspace / "api.py"
        py_file.write_text(
            """from fastapi import APIRouter, Depends

router = APIRouter()

def get_db():
    return "session"

@router.get("/items/{item_id}")
def read_item(item_id: int, db = Depends(get_db)):
    return {"id": item_id}

@router.post("/items")
async def create_item(payload: dict, db = Depends(get_db)):
    return payload
""",
            encoding="utf-8"
        )

        parser = PythonASTParser()
        nodes, edges = parser.parse(py_file, self.workspace)

        # Check Endpoint Nodes
        endpoints = [n for n in nodes if n.node_type == NodeType.ENDPOINT]
        self.assertEqual(len(endpoints), 2)
        ep_paths = {e.metadata["path"] for e in endpoints}
        self.assertIn("/items/{item_id}", ep_paths)
        self.assertIn("/items", ep_paths)

        # Check ROUTES_TO edges
        route_edges = [e for e in edges if e.edge_type == EdgeType.ROUTES_TO]
        self.assertEqual(len(route_edges), 2)

        # Check INJECTS edges
        inject_edges = [e for e in edges if e.edge_type == EdgeType.INJECTS]
        self.assertEqual(len(inject_edges), 2)
        for ie in inject_edges:
            self.assertEqual(ie.metadata["provider"], "get_db")

    def test_flask_routes(self):
        """Flask Blueprint route extraction with HTTP methods."""
        flask_file = self.workspace / "views.py"
        flask_file.write_text(
            """from flask import Blueprint

bp = Blueprint("auth", __name__)

@bp.route("/login", methods=["POST"])
def login_view():
    return "ok"
""",
            encoding="utf-8"
        )

        parser = PythonASTParser()
        nodes, edges = parser.parse(flask_file, self.workspace)

        endpoint = next((n for n in nodes if n.node_type == NodeType.ENDPOINT), None)
        self.assertIsNotNone(endpoint)
        self.assertEqual(endpoint.metadata["http_method"], "POST")
        self.assertEqual(endpoint.metadata["path"], "/login")
        self.assertEqual(endpoint.metadata["framework"], "flask")

    def test_sqlalchemy_and_django_orm(self):
        """SQLAlchemy __tablename__ and Django models mapped to database Table nodes."""
        models_file = self.workspace / "models.py"
        models_file.write_text(
            """from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)

class DjangoProfile(Model):
    title = models.CharField(max_length=100)
""",
            encoding="utf-8"
        )

        parser = PythonASTParser()
        nodes, edges = parser.parse(models_file, self.workspace)

        tables = [n for n in nodes if n.node_type == NodeType.TABLE]
        self.assertEqual(len(tables), 2)
        tbl_names = {t.name for t in tables}
        self.assertIn("users", tbl_names)
        self.assertIn("djangoprofile", tbl_names)

        maps_to_edges = [e for e in edges if e.edge_type == EdgeType.MAPS_TO]
        self.assertEqual(len(maps_to_edges), 2)

    def test_express_routes(self):
        """Express app and router HTTP endpoints extraction."""
        js_file = self.workspace / "server.js"
        js_file.write_text(
            """const express = require('express');
const app = express();
const router = express.Router();

app.get('/health', checkHealth);
router.post('/api/auth/token', generateToken);
""",
            encoding="utf-8"
        )

        parser = JavaScriptTypeScriptParser()
        nodes, edges = parser.parse(js_file, self.workspace)

        endpoints = [n for n in nodes if n.node_type == NodeType.ENDPOINT]
        self.assertEqual(len(endpoints), 2)
        paths = {e.metadata["path"] for e in endpoints}
        self.assertIn("/health", paths)
        self.assertIn("/api/auth/token", paths)

    def test_nestjs_controllers_and_di(self):
        """NestJS @Controller, @Get methods, and constructor parameter dependency injection."""
        ts_file = self.workspace / "cats.controller.ts"
        ts_file.write_text(
            """import { Controller, Get, Post } from '@nestjs/common';
import { CatsService } from './cats.service';

@Controller('cats')
export class CatsController {
    constructor(private readonly catsService: CatsService) {}

    @Get(':id')
    async findOne() {
        return this.catsService.find();
    }
}
""",
            encoding="utf-8"
        )

        parser = JavaScriptTypeScriptParser()
        nodes, edges = parser.parse(ts_file, self.workspace)

        # Check Endpoint
        ep = next((n for n in nodes if n.node_type == NodeType.ENDPOINT), None)
        self.assertIsNotNone(ep)
        self.assertEqual(ep.metadata["http_method"], "GET")
        self.assertEqual(ep.metadata["path"], "/cats/:id")
        self.assertEqual(ep.metadata["framework"], "nestjs")

        # Check INJECTS edge
        inject_edge = next((e for e in edges if e.edge_type == EdgeType.INJECTS), None)
        self.assertIsNotNone(inject_edge)
        self.assertEqual(inject_edge.metadata["provider"], "CatsService")

    def test_prisma_schema(self):
        """Prisma schema models and relational table mapping."""
        prisma_file = self.workspace / "schema.prisma"
        prisma_file.write_text(
            """datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id    Int     @id @default(autoincrement())
  email String  @unique
  posts Post[]
}

model Post {
  id       Int    @id @default(autoincrement())
  title    String
  authorId Int
  author   User   @relation(fields: [authorId], references: [id])
}
""",
            encoding="utf-8"
        )

        self.engine.index_workspace(self.workspace, self.store, clean=True)

        user_tbl = self.store.get_node("table:User")
        post_tbl = self.store.get_node("table:Post")
        self.assertIsNotNone(user_tbl)
        self.assertIsNotNone(post_tbl)
        self.assertEqual(user_tbl["node_type"], "table")

    def test_cli_graph_routes_and_di(self):
        """CLI invocation of agtoosa graph routes and agtoosa graph di."""
        py_file = self.workspace / "main.py"
        py_file.write_text(
            """from fastapi import FastAPI, Depends

app = FastAPI()

def db_provider():
    return 1

@app.get("/api/v1/ping")
def ping(db = Depends(db_provider)):
    return {"ping": "pong"}
""",
            encoding="utf-8"
        )

        self.engine.index_workspace(self.workspace, self.store, clean=True)

        # 1. Test agtoosa graph routes --json
        stdout = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = stdout
            code = main(["-C", str(self.workspace), "graph", "routes", "--json"])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(code, 0)
        data = json.loads(stdout.getvalue())
        self.assertGreaterEqual(data["routes_count"], 1)
        self.assertEqual(data["routes"][0]["path"], "/api/v1/ping")

        # 2. Test agtoosa graph di <symbol> --json
        stdout_di = io.StringIO()
        try:
            sys.stdout = stdout_di
            code_di = main(["-C", str(self.workspace), "graph", "di", "ping", "--json"])
        finally:
            sys.stdout = old_stdout

        self.assertEqual(code_di, 0)
        di_data = json.loads(stdout_di.getvalue())
        self.assertTrue(len(di_data["injected_into_target"]) >= 1)
        self.assertEqual(di_data["injected_into_target"][0]["provider"], "db_provider")

    def test_mcp_route_and_di_tools(self):
        """MCP tools agtoosa_get_route_context and agtoosa_get_di_graph."""
        py_file = self.workspace / "app.py"
        py_file.write_text(
            """from fastapi import FastAPI, Depends

app = FastAPI()

def auth_service():
    return True

@app.get("/secure/data")
def get_secure_data(auth = Depends(auth_service)):
    return {"secure": True}
""",
            encoding="utf-8"
        )

        self.engine.index_workspace(self.workspace, self.store, clean=True)
        mcp = MCPServer(self.workspace)

        # 1. agtoosa_get_route_context
        res_routes = json.loads(mcp.handle_tool_call("agtoosa_get_route_context", {"path": "/secure/data"}))
        self.assertTrue(len(res_routes["matched_routes"]) >= 1)
        self.assertEqual(res_routes["matched_routes"][0]["http_method"], "GET")

        # 2. agtoosa_get_di_graph
        res_di = json.loads(mcp.handle_tool_call("agtoosa_get_di_graph", {"symbol": "get_secure_data"}))
        self.assertTrue(len(res_di["injected_into_target"]) >= 1)
        self.assertEqual(res_di["injected_into_target"][0]["provider"], "auth_service")

    def test_nestjs_injectable_service(self):
        """NestJS @Injectable() service classes extracted into knowledge graph."""
        ts_file = self.workspace / "cats.service.ts"
        ts_file.write_text(
            """import { Injectable } from '@nestjs/common';

@Injectable()
export class CatsService {
    findAll() {
        return ['cat1', 'cat2'];
    }
}
""",
            encoding="utf-8"
        )
        parser = JavaScriptTypeScriptParser()
        nodes, edges = parser.parse(ts_file, self.workspace)
        class_node = next((n for n in nodes if n.node_type == NodeType.CLASS and n.name == "CatsService"), None)
        self.assertIsNotNone(class_node)
        self.assertTrue(class_node.metadata.get("injectable"))

    def test_framework_semantics_prevent_false_dead_code(self):
        """FastAPI route handlers and injected providers are not flagged as dead code."""
        from agtoosa.refactor.dead_code import DeadCodePruner
        py_file = self.workspace / "api_live.py"
        py_file.write_text(
            """from fastapi import FastAPI, Depends

app = FastAPI()

def get_db():
    return "session"

@app.get("/users")
def get_users(db = Depends(get_db)):
    return []
""",
            encoding="utf-8"
        )
        self.engine.index_workspace(self.workspace, self.store, clean=True)
        pruner = DeadCodePruner(self.store, self.workspace)
        report = pruner.analyze()
        zombies = [z.name for z in report.zombies]
        self.assertNotIn("get_users", zombies)
        self.assertNotIn("get_db", zombies)


if __name__ == "__main__":
    unittest.main()
