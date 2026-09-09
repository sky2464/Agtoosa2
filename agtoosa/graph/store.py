"""Transactional SQLite graph store with FTS5 inverted search."""

from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from agtoosa.core.model import Node, Edge, NodeType, EdgeType, GraphStats


class GraphStore:
    """Manages the SQLite-backed knowledge graph at .agtoosa/graph.db."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

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
            conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild');")

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
                    n.docstring,
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

        # Format terms for prefix matching
        terms = [t for t in clean_query.split() if t]
        fts_expr = " ".join(f'"{term}"*' for term in terms)

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
