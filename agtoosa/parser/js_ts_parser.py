"""Lightweight AST extractor for JavaScript and TypeScript files."""

import re
from pathlib import Path
from typing import List, Tuple

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.parser.base import BaseParser


class JavaScriptTypeScriptParser(BaseParser):
    """Extracts classes, functions, and import/export statements from JS/TS code."""

    # Imports: import { x } from 'y'; import x from 'y'; const x = require('y')
    IMPORT_ESM_REGEX = re.compile(
        r"""import\s+(?:(?:(?:\*\s+as\s+\w+|[\w$]+|{[^}]*})\s+from\s+)|)['"]([^'"]+)['"]""",
        re.MULTILINE
    )
    IMPORT_CJS_REGEX = re.compile(
        r"""(?:const|let|var)\s+(?:[\w$]+|{[^}]*})\s*=\s*require\(\s*['"]([^'"]+)['"]\s*\)""",
        re.MULTILINE
    )

    # Class definitions: class Foo extends Bar { ... }
    CLASS_REGEX = re.compile(
        r"""(?:export\s+)?(?:default\s+)?class\s+([a-zA-Z0-9_$]+)(?:\s+extends\s+([a-zA-Z0-9_$.]+))?\s*\{""",
        re.MULTILINE
    )

    # Function definitions:
    # 1. function foo(...) {
    # 2. const foo = (...) => { or const foo = function(...) {
    FUNC_DECL_REGEX = re.compile(
        r"""(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(""",
        re.MULTILINE
    )
    ARROW_FUNC_REGEX = re.compile(
        r"""(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z0-9_$]+)\s*=>""",
        re.MULTILINE
    )

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")

    def parse(self, file_path: Path, workspace_root: Path) -> Tuple[List[Node], List[Edge]]:
        nodes: List[Node] = []
        edges: List[Edge] = []

        rel_path = str(file_path.relative_to(workspace_root))
        file_node_id = f"file:{rel_path}"

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            return nodes, edges

        lines = content.splitlines()

        # File Node
        nodes.append(
            Node(
                id=file_node_id,
                name=file_path.name,
                node_type=NodeType.FILE,
                path=rel_path,
                metadata={"total_lines": len(lines), "language": "javascript_typescript"}
            )
        )

        # 1. Extract ESM Imports
        for match in self.IMPORT_ESM_REGEX.finditer(content):
            target_module = match.group(1)
            import_id = f"import:{rel_path}:{target_module}"
            line_idx = content[: match.start()].count("\n") + 1
            nodes.append(
                Node(
                    id=import_id,
                    name=target_module,
                    node_type=NodeType.IMPORT,
                    path=rel_path,
                    start_line=line_idx
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=import_id,
                    edge_type=EdgeType.IMPORTS
                )
            )

        # 2. Extract CommonJS Imports
        for match in self.IMPORT_CJS_REGEX.finditer(content):
            target_module = match.group(1)
            import_id = f"import:{rel_path}:{target_module}"
            line_idx = content[: match.start()].count("\n") + 1
            nodes.append(
                Node(
                    id=import_id,
                    name=target_module,
                    node_type=NodeType.IMPORT,
                    path=rel_path,
                    start_line=line_idx
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=import_id,
                    edge_type=EdgeType.IMPORTS
                )
            )

        # 3. Extract Classes
        for match in self.CLASS_REGEX.finditer(content):
            class_name = match.group(1)
            extends_class = match.group(2)
            class_id = f"class:{rel_path}:{class_name}"
            line_idx = content[: match.start()].count("\n") + 1

            meta = {}
            if extends_class:
                meta["extends"] = extends_class

            nodes.append(
                Node(
                    id=class_id,
                    name=class_name,
                    node_type=NodeType.CLASS,
                    path=rel_path,
                    start_line=line_idx,
                    metadata=meta
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=class_id,
                    edge_type=EdgeType.CONTAINS
                )
            )

            if extends_class:
                edges.append(
                    Edge(
                        source_id=class_id,
                        target_id=f"type:{extends_class}",
                        edge_type=EdgeType.INHERITS,
                        provenance="inferred"
                    )
                )

        # 4. Extract Functions
        found_func_names = set()

        for match in self.FUNC_DECL_REGEX.finditer(content):
            func_name = match.group(1)
            if func_name in found_func_names:
                continue
            found_func_names.add(func_name)
            func_id = f"func:{rel_path}:{func_name}"
            line_idx = content[: match.start()].count("\n") + 1

            nodes.append(
                Node(
                    id=func_id,
                    name=func_name,
                    node_type=NodeType.FUNCTION,
                    path=rel_path,
                    start_line=line_idx
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=func_id,
                    edge_type=EdgeType.CONTAINS
                )
            )

        for match in self.ARROW_FUNC_REGEX.finditer(content):
            func_name = match.group(1)
            if func_name in found_func_names:
                continue
            found_func_names.add(func_name)
            func_id = f"func:{rel_path}:{func_name}"
            line_idx = content[: match.start()].count("\n") + 1

            nodes.append(
                Node(
                    id=func_id,
                    name=func_name,
                    node_type=NodeType.FUNCTION,
                    path=rel_path,
                    start_line=line_idx,
                    metadata={"style": "arrow"}
                )
            )
            edges.append(
                Edge(
                    source_id=file_node_id,
                    target_id=func_id,
                    edge_type=EdgeType.CONTAINS
                )
            )

        # Extract JS/TS Framework Semantics (Express routes, NestJS controllers & DI)
        from agtoosa.parser.frameworks import TypeScriptFrameworkExtractor
        fw_nodes, fw_edges = TypeScriptFrameworkExtractor.extract(content, rel_path, file_node_id)
        nodes.extend(fw_nodes)
        edges.extend(fw_edges)

        # Extract Event Lineage (Kafka, RabbitMQ, Redis, BullMQ)
        from agtoosa.parser.event_lineage import TypeScriptEventExtractor
        ev_nodes, ev_edges = TypeScriptEventExtractor.extract(content, rel_path, file_node_id)
        nodes.extend(ev_nodes)
        edges.extend(ev_edges)

        return nodes, edges

