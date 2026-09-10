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
from agtoosa.parser.scanner import scan_workspace


class ParserEngine:
    """Orchestrates file discovery and language-specific AST parsing."""

    def __init__(self):
        self.parsers: List[BaseParser] = [
            PythonASTParser(),
            ShellScriptParser(),
            JavaScriptTypeScriptParser(),
            MarkdownDocParser()
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

            # Modified or new file
            if rel_path in existing_fingerprints:
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
        """Link import nodes and function calls to matching defined symbols across files."""
        with store._get_connection() as conn:
            # Map symbol names to target node IDs (classes, functions)
            symbol_rows = conn.execute(
                "SELECT name, id FROM nodes WHERE node_type IN ('class', 'function');"
            ).fetchall()
            symbol_map = {}
            for name, nid in symbol_rows:
                # Map both short name and full name
                symbol_map[name] = nid

            # Find import nodes
            import_rows = conn.execute(
                "SELECT id, name FROM nodes WHERE node_type = 'import';"
            ).fetchall()

            resolution_edges = []
            for import_id, full_import_name in import_rows:
                short_name = full_import_name.split(".")[-1]
                if short_name in symbol_map:
                    target_id = symbol_map[short_name]
                    if target_id != import_id:
                        resolution_edges.append((import_id, target_id, "references", "resolved", "{}"))

            if resolution_edges:
                conn.executemany(
                    """
                    INSERT INTO edges (source_id, target_id, edge_type, provenance, metadata_json)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    resolution_edges
                )

            # Resolve function call placeholders to actual symbol nodes
            call_edges = conn.execute(
                "SELECT rowid, source_id, target_id FROM edges WHERE target_id LIKE 'func_call:%';"
            ).fetchall()
            for rowid, src_id, tgt_placeholder in call_edges:
                callee_name = tgt_placeholder.split(":", 1)[-1]
                if callee_name in symbol_map:
                    real_target_id = symbol_map[callee_name]
                    conn.execute(
                        "UPDATE edges SET target_id = ?, provenance = 'resolved' WHERE rowid = ?;",
                        (real_target_id, rowid)
                    )

