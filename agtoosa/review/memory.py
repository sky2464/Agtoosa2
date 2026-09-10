"""Architectural Memory Bank: Storing team decisions, architectural lessons, and design rules."""

from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, List, Optional

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore


class ArchitecturalMemory:
    """Stores and queries institutional memory, design rules, and historical review findings."""

    def __init__(self, store: GraphStore):
        self.store = store

    def _slugify(self, text: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
        return s[:40].strip("_")

    def remember(self, lesson: str, domain: Optional[str] = None, tags: Optional[List[str]] = None) -> Node:
        """Store an architectural lesson or design invariant into the graph memory bank."""
        now = datetime.now(timezone.utc).isoformat()
        slug = self._slugify(lesson) or f"rule_{int(datetime.now().timestamp())}"
        node_id = f"concept:memory:{slug}"

        node = Node(
            id=node_id,
            name=f"Architectural Rule: {slug.replace('_', ' ').title()}",
            node_type=NodeType.CONCEPT,
            path=".agtoosa/memory",
            docstring=lesson,
            metadata={
                "kind": "architectural_memory",
                "domain": domain or "global",
                "tags": tags or [],
                "created_at": now
            }
        )

        edges: List[Edge] = []
        # If domain specified, link to relevant file or class nodes
        if domain:
            with self.store._get_connection() as conn:
                matched_nodes = conn.execute(
                    "SELECT id FROM nodes WHERE path LIKE ? OR name LIKE ? LIMIT 5;",
                    (f"%{domain}%", f"%{domain}%")
                ).fetchall()
                for (mid,) in matched_nodes:
                    edges.append(Edge(
                        source_id=node_id,
                        target_id=mid,
                        edge_type=EdgeType.REFERENCES,
                        provenance="architectural_memory"
                    ))

        self.store.insert_batch([node], edges)
        return node

    def reflect(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve stored architectural rules and team lessons."""
        with self.store._get_connection() as conn:
            if domain:
                rows = conn.execute(
                    """
                    SELECT id, name, docstring, metadata_json
                    FROM nodes
                    WHERE node_type = 'concept'
                      AND metadata_json LIKE '%architectural_memory%'
                      AND (metadata_json LIKE ? OR metadata_json LIKE '%"domain": "global"%');
                    """,
                    (f'%"domain": "{domain}"%',)
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, name, docstring, metadata_json
                    FROM nodes
                    WHERE node_type = 'concept'
                      AND metadata_json LIKE '%architectural_memory%';
                    """
                ).fetchall()

            rules = []
            for r in rows:
                meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                rules.append({
                    "id": r["id"],
                    "name": r["name"],
                    "rule": r["docstring"],
                    "domain": meta.get("domain", "global"),
                    "tags": meta.get("tags", []),
                    "created_at": meta.get("created_at")
                })
            return rules

    def get_relevant_rules(self, domain_or_text: Optional[str] = None) -> List[str]:
        """Fetch matching text rules to inject into AI Context Packs."""
        rules = self.reflect(domain=None)
        if not domain_or_text:
            return [r["rule"] for r in rules if r.get("rule")]

        relevant = []
        search_lower = domain_or_text.lower()
        for r in rules:
            r_domain = str(r.get("domain", "")).lower()
            r_text = str(r.get("rule", "")).lower()
            if r_domain in search_lower or any(word in r_text for word in search_lower.split() if len(word) > 4):
                relevant.append(r["rule"])

        return relevant or [r["rule"] for r in rules[:3] if r.get("rule")]
