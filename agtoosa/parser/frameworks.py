"""Framework Semantic Extractors (DEV-025 / Stage 25).

Extracts runtime framework architecture patterns:
- FastAPI / Flask route endpoints and Dependency Injection (Depends)
- SQLAlchemy and Django ORM models and database tables
- Express route definitions and NestJS controllers / DI constructors
- Prisma schema models and table relationships
"""

import ast
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from agtoosa.core.model import Node, Edge, NodeType, EdgeType


class PythonFrameworkExtractor:
    """Extracts FastAPI, Flask, SQLAlchemy, and Django semantic architecture from Python AST."""

    HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}

    @classmethod
    def extract(cls, source: str, rel_path: str, tree: ast.AST, file_node_id: str) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        class FrameworkVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_class_id: Optional[str] = None
                self.current_class_name: Optional[str] = None

            def visit_ClassDef(self, node: ast.ClassDef):
                class_id = f"class:{rel_path}:{node.name}"
                prev_class_id = self.current_class_id
                prev_class_name = self.current_class_name
                self.current_class_id = class_id
                self.current_class_name = node.name

                # 1. SQLAlchemy ORM Model Detection
                table_name = None
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name) and target.id == "__tablename__":
                                if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                                    table_name = stmt.value.value

                # 2. Django Model Detection
                is_django_model = any(
                    isinstance(b, ast.Attribute) and b.attr == "Model"
                    or isinstance(b, ast.Name) and b.id == "Model"
                    for b in node.bases
                )

                if is_django_model and not table_name:
                    table_name = node.name.lower()

                if table_name:
                    table_id = f"table:{table_name}"
                    nodes.append(
                        Node(
                            id=table_id,
                            name=table_name,
                            node_type=NodeType.TABLE,
                            path=rel_path,
                            start_line=node.lineno,
                            metadata={"orm": "django" if is_django_model else "sqlalchemy", "model_class": node.name}
                        )
                    )
                    edges.append(
                        Edge(
                            source_id=class_id,
                            target_id=table_id,
                            edge_type=EdgeType.MAPS_TO,
                            metadata={"orm": "django" if is_django_model else "sqlalchemy"}
                        )
                    )

                self.generic_visit(node)
                self.current_class_id = prev_class_id
                self.current_class_name = prev_class_name

            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._process_function(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._process_function(node)

            def _process_function(self, node):
                func_id = f"func:{rel_path}:{self.current_class_name}.{node.name}" if self.current_class_name else f"func:{rel_path}:{node.name}"

                # 1. Route Decorator Detection (FastAPI, Flask)
                for dec in node.decorator_list:
                    endpoint_info = cls._parse_route_decorator(dec)
                    if endpoint_info:
                        method, path, fw = endpoint_info
                        endpoint_id = f"endpoint:{method}:{path}"
                        nodes.append(
                            Node(
                                id=endpoint_id,
                                name=f"{method} {path}",
                                node_type=NodeType.ENDPOINT,
                                path=rel_path,
                                start_line=node.lineno,
                                metadata={
                                    "http_method": method,
                                    "path": path,
                                    "framework": fw,
                                    "handler": node.name
                                }
                            )
                        )
                        edges.append(
                            Edge(
                                source_id=endpoint_id,
                                target_id=func_id,
                                edge_type=EdgeType.ROUTES_TO,
                                metadata={"framework": fw}
                            )
                        )

                # 2. Dependency Injection Detection (FastAPI Depends)
                cls._extract_di_dependencies(node, func_id, rel_path, edges)

                self.generic_visit(node)

        visitor = FrameworkVisitor()
        visitor.visit(tree)
        return nodes, edges

    @classmethod
    def _parse_route_decorator(cls, dec: ast.AST) -> Optional[Tuple[str, str, str]]:
        """Parse decorator into (HTTP_METHOD, PATH, FRAMEWORK) if it matches route conventions."""
        if not isinstance(dec, ast.Call):
            return None

        method = None
        path = "/"
        framework = "fastapi"

        # e.g. @app.get("/users"), @router.post("/items"), @bp.route("/items", methods=["POST"])
        if isinstance(dec.func, ast.Attribute):
            attr_name = dec.func.attr.lower()
            caller_name = dec.func.value.id.lower() if isinstance(dec.func.value, ast.Name) else ""

            if caller_name in ("bp", "blueprint"):
                framework = "flask"

            if attr_name in cls.HTTP_METHODS:
                method = attr_name.upper()
            elif attr_name in ("route", "api_route"):
                method = "GET"  # default
                # Check methods keyword arg
                for kw in dec.keywords:
                    if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                        if kw.value.elts and isinstance(kw.value.elts[0], ast.Constant):
                            method = str(kw.value.elts[0].value).upper()
            else:
                return None
        else:
            return None

        # Extract path from first positional arg
        if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
            path = dec.args[0].value
            if not path.startswith("/"):
                path = "/" + path

        return (method, path, framework)

    @classmethod
    def _extract_di_dependencies(cls, func_node: ast.AST, func_id: str, rel_path: str, edges: List[Edge]) -> None:
        """Inspect function arguments for Depends(...) or Annotated[..., Depends(...)]."""
        args_list = func_node.args.args

        # Match positional defaults
        defaults = func_node.args.defaults
        num_args = len(args_list)
        num_defaults = len(defaults)
        offset = num_args - num_defaults

        for idx, arg in enumerate(args_list):
            provider_name = None

            # 1. Default value = Depends(provider)
            if idx >= offset:
                default_val = defaults[idx - offset]
                if isinstance(default_val, ast.Call):
                    if (isinstance(default_val.func, ast.Name) and default_val.func.id == "Depends") or \
                       (isinstance(default_val.func, ast.Attribute) and default_val.func.attr == "Depends"):
                        if default_val.args:
                            first_arg = default_val.args[0]
                            if isinstance(first_arg, ast.Name):
                                provider_name = first_arg.id
                            elif isinstance(first_arg, ast.Attribute):
                                provider_name = first_arg.attr

            # 2. Type annotation = Annotated[Type, Depends(provider)]
            if not provider_name and arg.annotation:
                if isinstance(arg.annotation, ast.Subscript):
                    if isinstance(arg.annotation.value, ast.Name) and arg.annotation.value.id == "Annotated":
                        slice_node = arg.annotation.slice
                        # In Python 3.9+, slice can be ast.Tuple
                        elts = slice_node.elts if isinstance(slice_node, ast.Tuple) else [slice_node]
                        for elt in elts:
                            if isinstance(elt, ast.Call):
                                if (isinstance(elt.func, ast.Name) and elt.func.id == "Depends") or \
                                   (isinstance(elt.func, ast.Attribute) and elt.func.attr == "Depends"):
                                    if elt.args and isinstance(elt.args[0], ast.Name):
                                        provider_name = elt.args[0].id

            if provider_name:
                edges.append(
                    Edge(
                        source_id=func_id,
                        target_id=f"symbol:{provider_name}",
                        edge_type=EdgeType.INJECTS,
                        metadata={"param": arg.arg, "provider": provider_name, "framework": "fastapi"}
                    )
                )


class TypeScriptFrameworkExtractor:
    """Extracts Express routes, NestJS controllers, and constructor dependency injection."""

    # Express route regex: app.get('/path', handler) or router.post('/path', handler)
    EXPRESS_ROUTE_REGEX = re.compile(
        r"""(?:app|router)\.(get|post|put|delete|patch)\(\s*['"]([^'"]+)['"]\s*,\s*(?:(?:[a-zA-Z0-9_$]+\s*,\s*)*([a-zA-Z0-9_$]+))?""",
        re.MULTILINE
    )

    # NestJS Controller: @Controller('prefix') class MyController
    NEST_CONTROLLER_REGEX = re.compile(
        r"""@Controller\(\s*(?:['"]([^'"]*)['"])?\s*\)\s*(?:export\s+)?class\s+([a-zA-Z0-9_$]+)""",
        re.MULTILINE
    )

    # NestJS Route Method: @Get('subpath') methodName(
    NEST_METHOD_REGEX = re.compile(
        r"""@(Get|Post|Put|Delete|Patch)\(\s*(?:['"]([^'"]*)['"])?\s*\)\s*(?:async\s+)?([a-zA-Z0-9_$]+)\s*\(""",
        re.MULTILINE
    )

    # Constructor injection: constructor(private readonly svc: MyService, ...)
    CONSTRUCTOR_INJECT_REGEX = re.compile(
        r"""constructor\s*\(([^)]*)\)""",
        re.DOTALL
    )
    PARAM_TYPE_REGEX = re.compile(
        r"""(?:private|protected|public|readonly)?\s*([a-zA-Z0-9_$]+)\s*:\s*([a-zA-Z0-9_$]+)"""
    )

    @classmethod
    def extract(cls, content: str, rel_path: str, file_node_id: str) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        # 1. Express Route Extraction
        for match in cls.EXPRESS_ROUTE_REGEX.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            handler_name = match.group(3)
            if not path.startswith("/"):
                path = "/" + path

            endpoint_id = f"endpoint:{method}:{path}"
            nodes.append(
                Node(
                    id=endpoint_id,
                    name=f"{method} {path}",
                    node_type=NodeType.ENDPOINT,
                    path=rel_path,
                    metadata={"http_method": method, "path": path, "framework": "express", "handler": handler_name}
                )
            )
            if handler_name:
                edges.append(
                    Edge(
                        source_id=endpoint_id,
                        target_id=f"func:{rel_path}:{handler_name}",
                        edge_type=EdgeType.ROUTES_TO,
                        metadata={"framework": "express"}
                    )
                )

        # 2. NestJS Controllers & Routes
        for c_match in cls.NEST_CONTROLLER_REGEX.finditer(content):
            prefix = c_match.group(1) or ""
            controller_name = c_match.group(2)
            class_id = f"class:{rel_path}:{controller_name}"

            if prefix and not prefix.startswith("/"):
                prefix = "/" + prefix

            # Scan methods within controller
            for m_match in cls.NEST_METHOD_REGEX.finditer(content):
                m_method = m_match.group(1).upper()
                subpath = m_match.group(2) or ""
                method_name = m_match.group(3)

                if subpath and not subpath.startswith("/"):
                    subpath = "/" + subpath

                full_path = (prefix + subpath) if (prefix or subpath) else "/"
                full_path = full_path.replace("//", "/")

                endpoint_id = f"endpoint:{m_method}:{full_path}"
                nodes.append(
                    Node(
                        id=endpoint_id,
                        name=f"{m_method} {full_path}",
                        node_type=NodeType.ENDPOINT,
                        path=rel_path,
                        metadata={"http_method": m_method, "path": full_path, "framework": "nestjs", "controller": controller_name}
                    )
                )
                edges.append(
                    Edge(
                        source_id=endpoint_id,
                        target_id=f"func:{rel_path}:{controller_name}.{method_name}",
                        edge_type=EdgeType.ROUTES_TO,
                        metadata={"framework": "nestjs"}
                    )
                )

        # 3. NestJS Constructor DI Parameter Injection
        for ctor_match in cls.CONSTRUCTOR_INJECT_REGEX.finditer(content):
            ctor_params = ctor_match.group(1)
            for p_match in cls.PARAM_TYPE_REGEX.finditer(ctor_params):
                param_name = p_match.group(1)
                type_name = p_match.group(2)
                # Ignore primitives
                if type_name not in ("string", "number", "boolean", "any", "unknown", "object"):
                    edges.append(
                        Edge(
                            source_id=file_node_id,
                            target_id=f"symbol:{type_name}",
                            edge_type=EdgeType.INJECTS,
                            metadata={"param": param_name, "provider": type_name, "framework": "nestjs"}
                        )
                    )

        return nodes, edges


class PrismaSchemaParser:
    """Parses Prisma schema files (schema.prisma) into database Table nodes and relational edges."""

    MODEL_REGEX = re.compile(r"""model\s+([a-zA-Z0-9_]+)\s*\{([^}]*)\}""", re.MULTILINE)
    FIELD_RELATION_REGEX = re.compile(r"""^\s*([a-zA-Z0-9_]+)\s+([a-zA-Z0-9_]+)(?:\[\]|\?)?\s+@relation""", re.MULTILINE)

    @classmethod
    def parse(cls, file_path: Path, workspace_root: Path) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        rel_path = str(file_path.relative_to(workspace_root))
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            return nodes, edges

        file_node_id = f"file:{rel_path}"
        nodes.append(
            Node(
                id=file_node_id,
                name=file_path.name,
                node_type=NodeType.FILE,
                path=rel_path,
                metadata={"format": "prisma"}
            )
        )

        for match in cls.MODEL_REGEX.finditer(content):
            model_name = match.group(1)
            body = match.group(2)
            table_id = f"table:{model_name}"

            nodes.append(
                Node(
                    id=table_id,
                    name=model_name,
                    node_type=NodeType.TABLE,
                    path=rel_path,
                    metadata={"orm": "prisma", "model": model_name}
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=table_id,
                    edge_type=EdgeType.CONTAINS
                )
            )

            # Detect @relation references to other models
            for r_match in cls.FIELD_RELATION_REGEX.finditer(body):
                target_model = r_match.group(2)
                edges.append(
                    Edge(
                        source_id=table_id,
                        target_id=f"table:{target_model}",
                        edge_type=EdgeType.REFERENCES,
                        metadata={"relation": "prisma_relation"}
                    )
                )

        return nodes, edges


from agtoosa.parser.base import BaseParser


class PrismaParser(BaseParser):
    """BaseParser wrapper for Prisma schema files."""

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".prisma" or file_path.name == "schema.prisma"

    def parse(self, file_path: Path, workspace_root: Path) -> Tuple[List[Node], List[Edge]]:
        return PrismaSchemaParser.parse(file_path, workspace_root)

