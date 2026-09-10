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

                CREATE TABLE IF NOT EXISTS node_embeddings (
                    node_id TEXT PRIMARY KEY,
                    dimension INTEGER NOT NULL,
                    vector BLOB NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_node_embeddings_id ON node_embeddings(node_id);

                CREATE TABLE IF NOT EXISTS federated_repos (
                    name TEXT PRIMARY KEY,
                    uri TEXT NOT NULL,
                    local_path TEXT NOT NULL,
                    repo_type TEXT NOT NULL,
                    schema_path TEXT,
                    synced_at TEXT,
                    metadata_json TEXT
                );

                CREATE TABLE IF NOT EXISTS runtime_telemetry (
                    node_id TEXT PRIMARY KEY,
                    call_count INTEGER DEFAULT 0,
                    total_duration_ms REAL DEFAULT 0.0,
                    avg_duration_ms REAL DEFAULT 0.0,
                    p95_duration_ms REAL DEFAULT 0.0,
                    error_count INTEGER DEFAULT 0,
                    error_rate REAL DEFAULT 0.0,
                    last_seen TEXT,
                    metadata_json TEXT DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_telemetry_calls ON runtime_telemetry(call_count);
                CREATE INDEX IF NOT EXISTS idx_telemetry_latency ON runtime_telemetry(avg_duration_ms);

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
            conn.execute("DELETE FROM node_embeddings;")
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
                conn.execute(f"DELETE FROM node_embeddings WHERE node_id IN ({placeholders});", node_ids)
                conn.execute("DELETE FROM nodes WHERE path = ?;", (rel_path,))

    def save_embeddings(self, embeddings: Dict[str, bytes], dimension: int) -> None:
        """Save a dictionary of node_id -> vector BLOB transactionally."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            rows = [(nid, dimension, blob, now) for nid, blob in embeddings.items()]
            conn.executemany(
                """
                INSERT OR REPLACE INTO node_embeddings (node_id, dimension, vector, updated_at)
                VALUES (?, ?, ?, ?);
                """,
                rows
            )

    def get_all_embeddings(self) -> Dict[str, bytes]:
        """Retrieve all node vector BLOBs."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT node_id, vector FROM node_embeddings;").fetchall()
            return {r["node_id"]: r["vector"] for r in rows}

    def get_embedding(self, node_id: str) -> Optional[bytes]:
        """Retrieve a specific node's vector BLOB."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT vector FROM node_embeddings WHERE node_id = ?;", (node_id,)).fetchone()
            return row[0] if row else None

    def get_embedding_count(self) -> int:
        """Return total count of indexed embeddings."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM node_embeddings;").fetchone()
            return row[0] if row else 0

    def clear_embeddings(self) -> None:
        """Clear all stored embeddings."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM node_embeddings;")

    def add_federated_repo(
        self,
        name: str,
        uri: str,
        local_path: str,
        repo_type: str = "local_dir",
        schema_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register or update a federated repository."""
        meta_json = json.dumps(metadata or {})
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO federated_repos 
                (name, uri, local_path, repo_type, schema_path, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (name, uri, local_path, repo_type, schema_path, meta_json)
            )

    def get_federated_repos(self) -> List[Dict[str, Any]]:
        """List all registered federated repositories."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM federated_repos ORDER BY name;").fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
                results.append(d)
            return results

    def get_federated_repo(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific federated repository by name."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM federated_repos WHERE name = ?;", (name,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
            return d

    def update_federated_repo_sync(self, name: str, synced_at: Optional[str] = None) -> None:
        """Update the synced_at timestamp for a federated repository."""
        ts = synced_at or datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE federated_repos SET synced_at = ? WHERE name = ?;",
                (ts, name)
            )

    def remove_federated_repo(self, name: str) -> bool:
        """Remove a federated repository and all its indexed nodes and edges."""
        self.remove_repo_nodes(name)
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM federated_repos WHERE name = ?;", (name,))
            return cur.rowcount > 0

    def remove_repo_nodes(self, repo_name: str) -> None:
        """Remove all nodes and edges belonging to a federated repository."""
        prefix = f"repo:{repo_name}:%"
        with self._get_connection() as conn:
            # Find nodes with prefixed IDs or matching repo metadata
            rows = conn.execute(
                "SELECT id FROM nodes WHERE id LIKE ? OR metadata_json LIKE ?;",
                (prefix, f'%"repo": "{repo_name}"%')
            ).fetchall()
            node_ids = [r[0] for r in rows]
            if node_ids:
                placeholders = ",".join("?" for _ in node_ids)
                conn.execute(f"DELETE FROM edges WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders});", node_ids + node_ids)
                conn.execute(f"DELETE FROM node_embeddings WHERE node_id IN ({placeholders});", node_ids)
                conn.execute(f"DELETE FROM nodes WHERE id IN ({placeholders});", node_ids)

    def save_telemetry_batch(self, records: List[Dict[str, Any]]) -> None:
        """Upsert a batch of runtime telemetry records."""
        if not records:
            return
        now_ts = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            for rec in records:
                node_id = rec["node_id"]
                calls = int(rec.get("call_count", 0))
                total_ms = float(rec.get("total_duration_ms", 0.0))
                avg_ms = float(rec.get("avg_duration_ms", total_ms / calls if calls > 0 else 0.0))
                p95_ms = float(rec.get("p95_duration_ms", avg_ms * 1.5))
                errors = int(rec.get("error_count", 0))
                error_rate = float(rec.get("error_rate", errors / calls if calls > 0 else 0.0))
                last_seen = rec.get("last_seen", now_ts)
                meta_json = json.dumps(rec.get("metadata", {}))

                conn.execute(
                    """
                    INSERT INTO runtime_telemetry 
                    (node_id, call_count, total_duration_ms, avg_duration_ms, p95_duration_ms, error_count, error_rate, last_seen, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(node_id) DO UPDATE SET
                        call_count = runtime_telemetry.call_count + excluded.call_count,
                        total_duration_ms = runtime_telemetry.total_duration_ms + excluded.total_duration_ms,
                        avg_duration_ms = (runtime_telemetry.total_duration_ms + excluded.total_duration_ms) / 
                                          NULLIF(runtime_telemetry.call_count + excluded.call_count, 0),
                        p95_duration_ms = MAX(runtime_telemetry.p95_duration_ms, excluded.p95_duration_ms),
                        error_count = runtime_telemetry.error_count + excluded.error_count,
                        error_rate = CAST(runtime_telemetry.error_count + excluded.error_count AS REAL) / 
                                     NULLIF(runtime_telemetry.call_count + excluded.call_count, 0),
                        last_seen = excluded.last_seen,
                        metadata_json = excluded.metadata_json;
                    """,
                    (node_id, calls, total_ms, avg_ms, p95_ms, errors, error_rate, last_seen, meta_json)
                )

    def get_telemetry_for_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Fetch runtime telemetry for a specific node ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM runtime_telemetry WHERE node_id = ?;", (node_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
            return d

    def get_all_telemetry(self) -> Dict[str, Dict[str, Any]]:
        """Retrieve all runtime telemetry indexed by node_id."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM runtime_telemetry;").fetchall()
            results = {}
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
                results[d["node_id"]] = d
            return results

    def clear_telemetry(self) -> int:
        """Clear all runtime telemetry."""
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM runtime_telemetry;")
            return cur.rowcount

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
                    e.edge_type.value if hasattr(e.edge_type, "value") else str(e.edge_type),
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
            row = conn.execute("SELECT * FROM nodes WHERE id = ?;", (node_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
            return d

    def find_nodes_by_name(self, name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find nodes matching name exactly or case-insensitively."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM nodes WHERE name = ? COLLATE NOCASE LIMIT ?;", (name, limit)).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json", "{}") or "{}")
                results.append(d)
            return results

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

