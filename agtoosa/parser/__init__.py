"""Parser subsystem orchestrating AST extractors and file scanning."""

from pathlib import Path
from typing import List, Tuple

from agtoosa.core.model import Node, Edge, NodeType, GraphStats
from agtoosa.graph.store import GraphStore
from agtoosa.parser.base import BaseParser
from agtoosa.parser.python_parser import PythonASTParser
from agtoosa.parser.shell_parser import ShellScriptParser
from agtoosa.parser.js_ts_parser import JavaScriptTypeScriptParser
from agtoosa.parser.doc_parser import MarkdownDocParser
from agtoosa.parser.polyglot_parser import PolyglotParser
from agtoosa.parser.frameworks import PrismaParser
from agtoosa.parser.scanner import scan_workspace


class ParserEngine:
    """Orchestrates file discovery and language-specific AST parsing."""

    def __init__(self):
        self.parsers: List[BaseParser] = [
            PythonASTParser(),
            ShellScriptParser(),
            JavaScriptTypeScriptParser(),
            MarkdownDocParser(),
            PolyglotParser(),
            PrismaParser(),
        ]


    def index_workspace(self, workspace_root: Path, store: GraphStore, clean: bool = False) -> GraphStats:
        """Scan workspace, extract AST nodes/edges, and persist into SQLite graph."""
        import hashlib

        if clean:
            store.clear()

        existing_fingerprints = store.get_fingerprints()
        files = scan_workspace(workspace_root)
        current_rel_paths = set()

        files_to_parse = []
        for file_path in files:
            rel_path = str(file_path.relative_to(workspace_root))
            current_rel_paths.add(rel_path)

            try:
                content_bytes = file_path.read_bytes()
                content_hash = hashlib.sha256(content_bytes).hexdigest()
                mtime = file_path.stat().st_mtime
            except (OSError, PermissionError):
                continue

            if rel_path in existing_fingerprints and existing_fingerprints[rel_path] == content_hash:
                # Unchanged - skip parsing
                continue

            # Modified or new file - remove old nodes before reparsing
            store.remove_file(rel_path)
            files_to_parse.append((file_path, rel_path, content_hash, mtime))

        # Handle deleted files
        for old_rel_path in list(existing_fingerprints.keys()):
            if old_rel_path not in current_rel_paths:
                store.remove_file(old_rel_path)

        all_nodes: List[Node] = []
        all_edges: List[Edge] = []

        for file_path, rel_path, content_hash, mtime in files_to_parse:
            parsed = False
            for parser in self.parsers:
                if parser.can_parse(file_path):
                    try:
                        nodes, edges = parser.parse(file_path, workspace_root)
                        all_nodes.extend(nodes)
                        all_edges.extend(edges)
                        parsed = True
                    except Exception:
                        pass
                    break

            if not parsed:
                # Generic file node
                all_nodes.append(
                    Node(
                        id=f"file:{rel_path}",
                        name=file_path.name,
                        node_type=NodeType.FILE,
                        path=rel_path
                    )
                )

            store.set_fingerprint(rel_path, content_hash, mtime)

        if all_nodes or all_edges:
            store.insert_batch(all_nodes, all_edges)
            self._resolve_cross_file_symbols(store)

        return store.get_stats()

    def _resolve_cross_file_symbols(self, store: GraphStore) -> None:
        """Link import nodes and function calls to matching defined symbols across files (DEV-041)."""
        from agtoosa.parser.resolver import SymbolResolver
        resolver = SymbolResolver(store)
        resolver.resolve_all_symbols()


