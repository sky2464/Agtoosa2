"""Transactional SQLite graph store with FTS5 inverted search."""

from __future__ import annotations
import json
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Iterator

# Ensure repository root is on sys.path if run directly as a script
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Python version guard
if sys.version_info < (3, 11):
    sys.exit(f"Error: Agtoosa2 requires Python 3.11 or newer (currently running on Python {sys.version.split()[0]}).")

from agtoosa.core.model import Node, Edge, NodeType, EdgeType, GraphStats
from agtoosa.core.security import redact_secrets


class GraphStore:
    """Manages the SQLite-backed knowledge graph at .agtoosa/graph.db."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    start_line INTEGER,
                    end_line INTEGER,
                    docstring TEXT,
                    metadata_json TEXT
                );

                CREATE TABLE IF NOT EXISTS file_fingerprints (
                    path TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    mtime REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS edges (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    metadata_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);
                CREATE INDEX IF NOT EXISTS idx_nodes_path ON nodes(path);
                CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(source_id);
                CREATE INDEX IF NOT EXISTS idx_edges_tgt ON edges(target_id);
                CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type);

                CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                    id UNINDEXED,
                    name,
                    node_type,
                    path,
                    docstring,
                    content='nodes',
                    content_rowid='rowid'
                );

                -- Triggers to keep FTS5 synchronized with nodes
                CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
                    INSERT INTO nodes_fts(rowid, id, name, node_type, path, docstring)
                    VALUES (new.rowid, new.id, new.name, new.node_type, new.path, new.docstring);
                END;

                CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
                    INSERT INTO nodes_fts(nodes_fts, rowid, id, name, node_type, path, docstring)
                    VALUES('delete', old.rowid, old.id, old.name, old.node_type, old.path, old.docstring);
                END;

                CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
                    INSERT INTO nodes_fts(nodes_fts, rowid, id, name, node_type, path, docstring)
                    VALUES('delete', old.rowid, old.id, old.name, old.node_type, old.path, old.docstring);
                    INSERT INTO nodes_fts(rowid, id, name, node_type, path, docstring)
                    VALUES (new.rowid, new.id, new.name, new.node_type, new.path, new.docstring);
                END;
            """)
            conn.execute(
                "INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', ?);",
                (str(self.SCHEMA_VERSION),)
            )

    def clear(self) -> None:
        """Clear all graph data for a clean rebuild."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM edges;")
            conn.execute("DELETE FROM nodes;")
            conn.execute("DELETE FROM file_fingerprints;")
            conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")

    def get_fingerprints(self) -> Dict[str, str]:
        """Return mapping of rel_path -> content_hash."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT path, content_hash FROM file_fingerprints;").fetchall()
            return {r[0]: r[1] for r in rows}

    def set_fingerprint(self, path: str, content_hash: str, mtime: float) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO file_fingerprints (path, content_hash, mtime) VALUES (?, ?, ?);",
                (path, content_hash, mtime)
            )

    def remove_file(self, rel_path: str) -> None:
        """Remove all nodes and edges belonging to a file path."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM file_fingerprints WHERE path = ?;", (rel_path,))
            node_rows = conn.execute("SELECT id FROM nodes WHERE path = ?;", (rel_path,)).fetchall()
            node_ids = [r[0] for r in node_rows]
            if node_ids:
                placeholders = ",".join("?" for _ in node_ids)
                conn.execute(f"DELETE FROM edges WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders});", node_ids + node_ids)
                conn.execute("DELETE FROM nodes WHERE path = ?;", (rel_path,))

    def insert_batch(self, nodes: List[Node], edges: List[Edge]) -> None:
        """Insert a batch of nodes and edges transactionally."""
        with self._get_connection() as conn:
            # Insert nodes first
            node_rows = [
                (
                    n.id,
                    n.name,
                    n.node_type.value,
                    n.path,
                    n.start_line,
                    n.end_line,
                    redact_secrets(n.docstring),
                    json.dumps(n.metadata)
                )
                for n in nodes
            ]
            conn.executemany(
                """
                INSERT OR REPLACE INTO nodes 
                (id, name, node_type, path, start_line, end_line, docstring, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                node_rows
            )

            # Insert edges
            edge_rows = [
                (
                    e.source_id,
                    e.target_id,
                    e.edge_type.value,
                    e.provenance,
                    json.dumps(e.metadata)
                )
                for e in edges
            ]
            conn.executemany(
                """
                INSERT INTO edges 
                (source_id, target_id, edge_type, provenance, metadata_json)
                VALUES (?, ?, ?, ?, ?);
                """,
                edge_rows
            )

            # Record timestamp
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_indexed_at', ?);",
                (now,)
            )

    def query_fts(self, query_str: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search nodes using SQLite FTS5."""
        clean_query = query_str.replace("'", "''").strip()
        if not clean_query:
            return []

        # Format terms for prefix matching while preserving FTS5 boolean operators
        terms = [t for t in clean_query.split() if t]
        parts = []
        for term in terms:
            if term.upper() in ("OR", "AND", "NOT"):
                parts.append(term.upper())
            elif term.startswith('"') and term.endswith('"'):
                parts.append(term)
            else:
                clean_term = term.strip('"*')
                if clean_term:
                    parts.append(f'"{clean_term}"*')
        fts_expr = " ".join(parts)

        with self._get_connection() as conn:
            try:
                rows = conn.execute(
                    """
                    SELECT n.id, n.name, n.node_type, n.path, n.start_line, n.end_line, n.docstring,
                           rank
                    FROM nodes_fts fts
                    JOIN nodes n ON fts.rowid = n.rowid
                    WHERE nodes_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?;
                    """,
                    (fts_expr, limit)
                ).fetchall()
            except sqlite3.OperationalError:
                # Fallback to simple LIKE query if FTS expression syntax fails
                like_expr = f"%{clean_query}%"
                rows = conn.execute(
                    """
                    SELECT id, name, node_type, path, start_line, end_line, docstring, 0 as rank
                    FROM nodes
                    WHERE name LIKE ? OR docstring LIKE ? OR path LIKE ?
                    LIMIT ?;
                    """,
                    (like_expr, like_expr, like_expr, limit)
                ).fetchall()

            return [dict(r) for r in rows]

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Retrieve all nodes from store with parsed metadata."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM nodes;").fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
                results.append(d)
            return results

    def get_all_edges(self) -> List[Dict[str, Any]]:
        """Retrieve all edges from store with parsed metadata."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM edges;").fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
                results.append(d)
            return results

    def stream_nodes(self, chunk_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """Stream nodes in chunks to avoid O(N) memory consumption."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes ORDER BY id;")
            while True:
                rows = cursor.fetchmany(chunk_size)
                if not rows:
                    break
                yield [
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "node_type": r["node_type"],
                        "path": r["path"],
                        "start_line": r["start_line"],
                        "end_line": r["end_line"],
                        "docstring": r["docstring"],
                        "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                    }
                    for r in rows
                ]

    def stream_edges(self, chunk_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """Stream edges in chunks to avoid O(N) memory consumption."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM edges;")
            while True:
                rows = cursor.fetchmany(chunk_size)
                if not rows:
                    break
                yield [
                    {
                        "source_id": r["source_id"],
                        "target_id": r["target_id"],
                        "edge_type": r["edge_type"],
                        "provenance": r["provenance"],
                        "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                    }
                    for r in rows
                ]

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM nodes WHERE id = ?;", (node_id,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
            return d

    def get_neighbors(self, node_id: str, direction: str = "both") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            results = []
            if direction in ("out", "both"):
                out_rows = conn.execute(
                    """
                    SELECT e.edge_type, e.provenance, n.*
                    FROM edges e
                    JOIN nodes n ON e.target_id = n.id
                    WHERE e.source_id = ?;
                    """,
                    (node_id,)
                ).fetchall()
                for r in out_rows:
                    d = dict(r)
                    d["direction"] = "out"
                    d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
                    results.append(d)

            if direction in ("in", "both"):
                in_rows = conn.execute(
                    """
                    SELECT e.edge_type, e.provenance, n.*
                    FROM edges e
                    JOIN nodes n ON e.source_id = n.id
                    WHERE e.target_id = ?;
                    """,
                    (node_id,)
                ).fetchall()
                for r in in_rows:
                    d = dict(r)
                    d["direction"] = "in"
                    d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
                    results.append(d)

            return results

    def get_stats(self) -> GraphStats:
        """Compute aggregate graph metrics."""
        with self._get_connection() as conn:
            total_nodes = conn.execute("SELECT COUNT(*) FROM nodes;").fetchone()[0]
            total_edges = conn.execute("SELECT COUNT(*) FROM edges;").fetchone()[0]

            node_counts: Dict[str, int] = {}
            for row in conn.execute("SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type;").fetchall():
                node_counts[row[0]] = row[1]

            edge_counts: Dict[str, int] = {}
            for row in conn.execute("SELECT edge_type, COUNT(*) FROM edges GROUP BY edge_type;").fetchall():
                edge_counts[row[0]] = row[1]

            files_indexed = conn.execute("SELECT COUNT(DISTINCT path) FROM nodes WHERE node_type = 'file';").fetchone()[0]
            last_ts_row = conn.execute("SELECT value FROM metadata WHERE key = 'last_indexed_at';").fetchone()
            last_ts = last_ts_row[0] if last_ts_row else None

            return GraphStats(
                total_nodes=total_nodes,
                total_edges=total_edges,
                node_counts_by_type=node_counts,
                edge_counts_by_type=edge_counts,
                files_indexed=files_indexed,
                last_indexed_at=last_ts
            )

    def export_json(self) -> Dict[str, Any]:
        """Export full graph representation for JSON serialization."""
        with self._get_connection() as conn:
            nodes = [dict(r) for r in conn.execute("SELECT * FROM nodes;").fetchall()]
            for n in nodes:
                n["metadata"] = json.loads(n.pop("metadata_json", "{}") or "{}")

            edges = [dict(r) for r in conn.execute("SELECT * FROM edges;").fetchall()]
            for e in edges:
                e["metadata"] = json.loads(e.pop("metadata_json", "{}") or "{}")

            stats = self.get_stats().to_dict()

            return {
                "schema_version": self.SCHEMA_VERSION,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "stats": stats,
                "nodes": nodes,
                "edges": edges
            }


if __name__ == "__main__":
    db_file = repo_root / ".agtoosa" / "graph.db"
    print(f"📊 Agtoosa2 GraphStore Diagnostics")
    print(f"   • Database path: {db_file}")
    if not db_file.exists():
        print("   • Status: Database does not exist yet. Run `agtoosa graph build` to index.")
    else:
        store = GraphStore(db_file)
        stats = store.get_stats()
        size_kb = db_file.stat().st_size / 1024.0
        print(f"   • Database size: {size_kb:.1f} KB")
        print(f"   • Total Nodes: {stats.total_nodes}")
        print(f"   • Total Edges: {stats.total_edges}")
        print(f"   • Files Indexed: {stats.files_indexed}")
        print(f"   • Last Indexed: {stats.last_indexed_at}")

