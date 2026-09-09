"""Parser subsystem orchestrating AST extractors and file scanning."""

from pathlib import Path
from typing import List, Tuple

from agtoosa.core.model import Node, Edge, NodeType, GraphStats
from agtoosa.graph.store import GraphStore
from agtoosa.parser.base import BaseParser
from agtoosa.parser.python_parser import PythonASTParser
from agtoosa.parser.shell_parser import ShellScriptParser
from agtoosa.parser.scanner import scan_workspace


class ParserEngine:
    """Orchestrates file discovery and language-specific AST parsing."""

    def __init__(self):
        self.parsers: List[BaseParser] = [
            PythonASTParser(),
            ShellScriptParser()
        ]

    def index_workspace(self, workspace_root: Path, store: GraphStore, clean: bool = False) -> GraphStats:
        """Scan workspace, extract AST nodes/edges, and persist into SQLite graph."""
        if clean:
            store.clear()

        files = scan_workspace(workspace_root)
        all_nodes: List[Node] = []
        all_edges: List[Edge] = []

        for file_path in files:
            for parser in self.parsers:
                if parser.can_parse(file_path):
                    try:
                        nodes, edges = parser.parse(file_path, workspace_root)
                        all_nodes.extend(nodes)
                        all_edges.extend(edges)
                    except Exception:
                        # Continue indexing remaining files on unexpected parser error
                        pass
                    break
            else:
                # Generic file node for other text files (e.g. Markdown, JSON, YAML)
                rel_path = str(file_path.relative_to(workspace_root))
                all_nodes.append(
                    Node(
                        id=f"file:{rel_path}",
                        name=file_path.name,
                        node_type=NodeType.FILE,
                        path=rel_path
                    )
                )

        store.insert_batch(all_nodes, all_edges)
        return store.get_stats()
