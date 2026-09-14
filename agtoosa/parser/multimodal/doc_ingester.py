"""Multimodal document and web ingester (DEV-033)."""

from __future__ import annotations
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import urllib.request

from agtoosa.core.model import Node, Edge, NodeType, EdgeType


class DocumentIngester:
    """Ingests Markdown specifications, research papers, and technical web documents."""

    def ingest_markdown(self, file_path: Path, workspace_root: Path) -> Tuple[List[Node], List[Edge]]:
        """Extract sections, requirements, and document references from Markdown."""
        if not file_path.exists():
            return [], []

        rel_path = str(file_path.relative_to(workspace_root)) if file_path.is_relative_to(workspace_root) else str(file_path)
        content = file_path.read_text(encoding="utf-8", errors="replace")
        nodes: List[Node] = []
        edges: List[Edge] = []

        doc_id = f"doc:{rel_path}"
        title = file_path.stem
        lines = content.splitlines()

        # Extract H1 title if present
        for line in lines:
            if line.startswith("# "):
                title = line.lstrip("# ").strip()
                break

        doc_node = Node(
            id=doc_id,
            name=title,
            node_type=NodeType.DOC,
            path=rel_path,
            start_line=1,
            end_line=len(lines),
            metadata={"word_count": len(content.split())}
        )
        nodes.append(doc_node)

        # Extract sections
        current_section = None
        for i, line in enumerate(lines, start=1):
            if line.startswith("## ") or line.startswith("### "):
                sec_name = line.lstrip("# ").strip()
                sec_id = f"section:{rel_path}:{sec_name.lower().replace(' ', '_')}"
                sec_node = Node(
                    id=sec_id,
                    name=sec_name,
                    node_type=NodeType.CONCEPT,
                    path=rel_path,
                    start_line=i,
                    metadata={"section_title": sec_name}
                )
                nodes.append(sec_node)
                edges.append(
                    Edge(
                        source_id=doc_id,
                        target_id=sec_id,
                        edge_type=EdgeType.CONTAINS,
                        provenance="extracted"
                    )
                )

        return nodes, edges

    def ingest_url(self, url: str) -> Tuple[List[Node], List[Edge]]:
        """Fetch remote technical document and extract title and summary."""
        nodes: List[Node] = []
        edges: List[Edge] = []

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Agtoosa-Multimodal-Ingester/0.6.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_bytes = resp.read(500_000)  # max 500KB preview
                html = raw_bytes.decode("utf-8", errors="replace")

            # Simple regex title extraction
            title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else url

            url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
            node_id = f"url:{url_hash}"

            doc_node = Node(
                id=node_id,
                name=title,
                node_type=NodeType.DOC,
                path=url,
                metadata={"url": url, "source_type": "web_url"}
            )
            nodes.append(doc_node)
        except Exception as ex:
            # Fallback placeholder
            url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
            doc_node = Node(
                id=f"url:{url_hash}",
                name=url,
                node_type=NodeType.DOC,
                path=url,
                metadata={"url": url, "error": str(ex)}
            )
            nodes.append(doc_node)

        return nodes, edges
