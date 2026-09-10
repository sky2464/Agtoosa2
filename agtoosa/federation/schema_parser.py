"""Contract Schema Parser: Extracts REST, gRPC, and GraphQL contracts into graph entities."""

from __future__ import annotations
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from agtoosa.core.model import Node, Edge, NodeType, EdgeType


class ContractSchemaParser:
    """Parses OpenAPI 3.0 / Swagger, gRPC Protobuf, and GraphQL schema files into knowledge graph entities."""

    def parse_schema_file(self, file_path: Path, repo_name: str = "local") -> Tuple[List[Node], List[Edge]]:
        """Parse an API contract schema file and return extracted nodes and edges."""
        if not file_path.exists():
            return [], []

        suffix = file_path.suffix.lower()
        if suffix in (".json", ".yaml", ".yml"):
            return self.parse_openapi(file_path, repo_name)
        elif suffix == ".proto":
            return self.parse_protobuf(file_path, repo_name)
        elif suffix in (".graphql", ".gql"):
            return self.parse_graphql(file_path, repo_name)

        return [], []

    def parse_openapi(self, file_path: Path, repo_name: str = "local") -> Tuple[List[Node], List[Edge]]:
        """Extract REST endpoints, parameters, and schema models from OpenAPI/Swagger definition."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        data: Dict[str, Any] = {}

        if file_path.suffix.lower() == ".json":
            try:
                data = json.loads(content)
            except Exception:
                return [], []
        else:
            # Try PyYAML if installed, otherwise basic fallback
            try:
                # pyrefly: ignore [missing-import]
                import yaml
                data = yaml.safe_load(content) or {}
            except ImportError:
                data = self._parse_simple_yaml(content)
            except Exception:
                return [], []

        if not isinstance(data, dict):
            return [], []

        nodes: List[Node] = []
        edges: List[Edge] = []
        rel_path = str(file_path)

        paths = data.get("paths", {})
        if isinstance(paths, dict):
            for route, methods in paths.items():
                if not isinstance(methods, dict):
                    continue

                for method_name, spec in methods.items():
                    method_lower = method_name.lower()
                    if method_lower not in ("get", "post", "put", "delete", "patch", "head", "options"):
                        continue

                    if not isinstance(spec, dict):
                        spec = {}

                    op_id = spec.get("operationId") or f"{method_lower.upper()} {route}"
                    summary = spec.get("summary") or spec.get("description") or f"REST API Endpoint {method_lower.upper()} {route}"
                    endpoint_id = f"endpoint:{method_lower.upper()}:{route}"
                    if repo_name != "local":
                        endpoint_id = f"repo:{repo_name}:{endpoint_id}"

                    endpoint_node = Node(
                        id=endpoint_id,
                        name=op_id,
                        node_type=NodeType.FUNCTION,
                        path=rel_path,
                        docstring=summary,
                        metadata={
                            "kind": "rest_endpoint",
                            "protocol": "rest",
                            "method": method_lower.upper(),
                            "route": route,
                            "tags": spec.get("tags", []),
                            "repo": repo_name
                        }
                    )
                    nodes.append(endpoint_node)

        # Parse schemas / definitions
        components = data.get("components", {}).get("schemas", {}) or data.get("definitions", {})
        if isinstance(components, dict):
            for schema_name, schema_spec in components.items():
                schema_id = f"schema:{schema_name}"
                if repo_name != "local":
                    schema_id = f"repo:{repo_name}:{schema_id}"

                doc = ""
                if isinstance(schema_spec, dict):
                    doc = schema_spec.get("description", "")

                schema_node = Node(
                    id=schema_id,
                    name=schema_name,
                    node_type=NodeType.CLASS,
                    path=rel_path,
                    docstring=doc or f"Data model schema for {schema_name}",
                    metadata={
                        "kind": "api_schema",
                        "repo": repo_name
                    }
                )
                nodes.append(schema_node)

        return nodes, edges

    def parse_protobuf(self, file_path: Path, repo_name: str = "local") -> Tuple[List[Node], List[Edge]]:
        """Extract gRPC services, RPC methods, and message types from a Protobuf .proto file."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        nodes: List[Node] = []
        edges: List[Edge] = []
        rel_path = str(file_path)

        # Regex for services
        service_pattern = re.compile(r"service\s+([A-Za-z0-9_]+)\s*\{([^}]+)\}", re.MULTILINE | re.DOTALL)
        rpc_pattern = re.compile(r"rpc\s+([A-Za-z0-9_]+)\s*\(\s*([A-Za-z0-9_.]+)\s*\)\s*returns\s*\(\s*([A-Za-z0-9_.]+)\s*\)", re.MULTILINE)

        for svc_match in service_pattern.finditer(content):
            svc_name = svc_match.group(1)
            svc_body = svc_match.group(2)

            svc_id = f"service:{svc_name}"
            if repo_name != "local":
                svc_id = f"repo:{repo_name}:{svc_id}"

            svc_node = Node(
                id=svc_id,
                name=svc_name,
                node_type=NodeType.CLASS,
                path=rel_path,
                docstring=f"gRPC Service: {svc_name}",
                metadata={"kind": "grpc_service", "protocol": "grpc", "repo": repo_name}
            )
            nodes.append(svc_node)

            for rpc_match in rpc_pattern.finditer(svc_body):
                rpc_name = rpc_match.group(1)
                req_type = rpc_match.group(2)
                res_type = rpc_match.group(3)

                rpc_id = f"rpc:{svc_name}.{rpc_name}"
                if repo_name != "local":
                    rpc_id = f"repo:{repo_name}:{rpc_id}"

                rpc_node = Node(
                    id=rpc_id,
                    name=f"{svc_name}.{rpc_name}",
                    node_type=NodeType.FUNCTION,
                    path=rel_path,
                    docstring=f"gRPC RPC method {svc_name}.{rpc_name}({req_type}) -> {res_type}",
                    metadata={
                        "kind": "grpc_rpc",
                        "protocol": "grpc",
                        "service": svc_name,
                        "method": rpc_name,
                        "request_type": req_type,
                        "response_type": res_type,
                        "repo": repo_name
                    }
                )
                nodes.append(rpc_node)

                # Link service -> rpc
                edges.append(Edge(
                    source_id=svc_id,
                    target_id=rpc_id,
                    edge_type=EdgeType.CONTAINS,
                    provenance="contract"
                ))

        # Regex for message schemas
        msg_pattern = re.compile(r"message\s+([A-Za-z0-9_]+)\s*\{", re.MULTILINE)
        for msg_match in msg_pattern.finditer(content):
            msg_name = msg_match.group(1)
            msg_id = f"schema:{msg_name}"
            if repo_name != "local":
                msg_id = f"repo:{repo_name}:{msg_id}"

            nodes.append(Node(
                id=msg_id,
                name=msg_name,
                node_type=NodeType.CLASS,
                path=rel_path,
                docstring=f"Protobuf message type: {msg_name}",
                metadata={"kind": "protobuf_message", "repo": repo_name}
            ))

        return nodes, edges

    def parse_graphql(self, file_path: Path, repo_name: str = "local") -> Tuple[List[Node], List[Edge]]:
        """Extract GraphQL queries, mutations, and types."""
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        nodes: List[Node] = []
        edges: List[Edge] = []
        rel_path = str(file_path)

        type_pattern = re.compile(r"type\s+([A-Za-z0-9_]+)\s*\{([^}]+)\}", re.MULTILINE | re.DOTALL)
        field_pattern = re.compile(r"^\s*([A-Za-z0-9_]+)(?:\([^)]*\))?\s*:\s*([A-Za-z0-9_!\[\]]+)", re.MULTILINE)

        for match in type_pattern.finditer(content):
            type_name = match.group(1)
            body = match.group(2)

            if type_name in ("Query", "Mutation", "Subscription"):
                for f_match in field_pattern.finditer(body):
                    field_name = f_match.group(1)
                    ret_type = f_match.group(2)

                    endpoint_id = f"graphql:{type_name}.{field_name}"
                    if repo_name != "local":
                        endpoint_id = f"repo:{repo_name}:{endpoint_id}"

                    nodes.append(Node(
                        id=endpoint_id,
                        name=f"{type_name}.{field_name}",
                        node_type=NodeType.FUNCTION,
                        path=rel_path,
                        docstring=f"GraphQL {type_name} operation: {field_name} -> {ret_type}",
                        metadata={
                            "kind": "graphql_operation",
                            "protocol": "graphql",
                            "operation": type_name,
                            "field": field_name,
                            "return_type": ret_type,
                            "repo": repo_name
                        }
                    ))
            else:
                type_id = f"schema:{type_name}"
                if repo_name != "local":
                    type_id = f"repo:{repo_name}:{type_id}"
                nodes.append(Node(
                    id=type_id,
                    name=type_name,
                    node_type=NodeType.CLASS,
                    path=rel_path,
                    docstring=f"GraphQL Object Type: {type_name}",
                    metadata={"kind": "graphql_type", "repo": repo_name}
                ))

        return nodes, edges

    def _parse_simple_yaml(self, text: str) -> Dict[str, Any]:
        """Fallback lightweight YAML path/method extractor if PyYAML is not installed."""
        result: Dict[str, Any] = {"paths": {}}
        current_path: Optional[str] = None
        current_method: Optional[str] = None

        lines = text.splitlines()
        for line in lines:
            line_str = line.strip()
            # Detect route under paths: e.g. "  /api/v1/users:"
            if line_str.startswith("/") and line_str.endswith(":"):
                current_path = line_str[:-1]
                result["paths"][current_path] = {}
                current_method = None
            elif current_path and line_str.lower() in ("get:", "post:", "put:", "delete:", "patch:"):
                current_method = line_str[:-1].lower()
                result["paths"][current_path][current_method] = {"operationId": f"{current_method.upper()} {current_path}"}

        return result
