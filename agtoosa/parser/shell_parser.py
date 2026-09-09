"""Lightweight AST extractor for Shell and Bash scripts."""

import re
from pathlib import Path
from typing import List, Tuple

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.parser.base import BaseParser


class ShellScriptParser(BaseParser):
    """Extracts functions, source imports, and definitions from shell scripts."""

    FUNC_REGEX = re.compile(r"^(?:function\s+)?([a-zA-Z0-9_:-]+)\s*\(\)\s*\{?", re.MULTILINE)
    SOURCE_REGEX = re.compile(r"^(?:source|\.)\s+([^\s;]+)", re.MULTILINE)

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in (".sh", ".bash", ".zsh")

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
                metadata={"total_lines": len(lines), "language": "shell"}
            )
        )

        for line_idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue

            # Check for source/import
            source_match = self.SOURCE_REGEX.match(line_str)
            if source_match:
                imported_target = source_match.group(1).strip("'\"")
                import_id = f"import:{rel_path}:{imported_target}"
                nodes.append(
                    Node(
                        id=import_id,
                        name=imported_target,
                        node_type=NodeType.IMPORT,
                        path=rel_path,
                        start_line=line_idx,
                        end_line=line_idx
                    )
                )
                edges.append(
                    Edge(
                        source_id=file_node_id,
                        target_id=import_id,
                        edge_type=EdgeType.IMPORTS
                    )
                )
                continue

            # Check for function definition
            func_match = self.FUNC_REGEX.match(line_str)
            if func_match:
                func_name = func_match.group(1)
                func_id = f"func:{rel_path}:{func_name}"
                nodes.append(
                    Node(
                        id=func_id,
                        name=func_name,
                        node_type=NodeType.FUNCTION,
                        path=rel_path,
                        start_line=line_idx,
                        metadata={"language": "shell"}
                    )
                )
                edges.append(
                    Edge(
                        source_id=file_node_id,
                        target_id=func_id,
                        edge_type=EdgeType.CONTAINS
                    )
                )

        return nodes, edges
