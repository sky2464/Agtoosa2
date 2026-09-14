"""Source rationale and decision provenance extractor (DEV-047).

Extracts `# WHY:`, `# NOTE:`, `# HACK:`, and `# ASSUMPTION:` markers from source code
comments, binds them to enclosing symbols or file spans without guessing, extracts ADR/story
citations, and applies security redaction before persistence.
"""

import re
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.core.security import redact_secrets


# Supported rationale marker prefixes
RATIONALE_MARKERS = ["WHY:", "NOTE:", "HACK:", "ASSUMPTION:"]

# ADR / Story citation regex: e.g. "ADR-001", "DEV-040", "STORY-12"
CITATION_REGEX = re.compile(r'\b(ADR-\d+|DEV-\d+|STORY-[A-Za-z0-9_-]+|RFC-\d+)\b', re.IGNORECASE)


@dataclass
class SourceRationale:
    """A decision rationale, assumption, or warning extracted from source comments."""
    rationale_id: str
    marker_type: str  # "WHY", "NOTE", "HACK", "ASSUMPTION"
    content: str
    file_path: str
    line_number: int
    enclosing_symbol_id: Optional[str] = None  # Bound symbol, or None if file-level span
    content_hash: str = ""
    citations: List[str] = field(default_factory=list)


def extract_comment_rationale(
    file_path: Path,
    workspace_root: Path,
    symbol_spans: Optional[List[Dict[str, Any]]] = None
) -> List[SourceRationale]:
    """Scan file lines for comment rationale markers and bind to enclosing symbol spans.

    Args:
        file_path: Path to the target source file.
        workspace_root: Root workspace path for relative path calculation.
        symbol_spans: List of dicts with {"id": symbol_id, "start_line": int, "end_line": int}

    Returns:
        List of SourceRationale instances.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return []

    rel_path = str(file_path.relative_to(workspace_root)) if file_path.is_relative_to(workspace_root) else str(file_path)
    lines = content.splitlines()
    results: List[SourceRationale] = []

    # Comment prefixes depending on file extension
    ext = file_path.suffix.lower()
    if ext in [".py", ".sh", ".bash", ".zsh", ".dockerfile"] or file_path.name.lower() == "dockerfile":
        comment_prefixes = ["#"]
    elif ext in [".sql"]:
        comment_prefixes = ["--", "/*"]
    else:
        comment_prefixes = ["//", "/*", "*", "#"]

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        is_comment = any(stripped.startswith(prefix) for prefix in comment_prefixes)
        if not is_comment:
            continue

        for marker in RATIONALE_MARKERS:
            if marker in stripped:
                marker_key = marker.rstrip(":")
                # Extract text after marker
                marker_pos = stripped.find(marker)
                raw_text = stripped[marker_pos + len(marker):].strip()
                # Redact any accidental secrets or credentials (DEV-007 / DEV-047)
                clean_text = redact_secrets(raw_text)

                # Determine enclosing symbol span without guessing
                enclosing_id = None
                if symbol_spans:
                    for sym in symbol_spans:
                        s_line = sym.get("start_line", 0)
                        e_line = sym.get("end_line", 0)
                        if s_line <= idx <= e_line:
                            enclosing_id = sym.get("id")
                            break

                # Extract citations (e.g. ADR-001, DEV-040)
                citations = CITATION_REGEX.findall(clean_text)

                h = hashlib.sha256(f"{rel_path}:{idx}:{clean_text}".encode()).hexdigest()[:12]
                rid = f"rationale:{rel_path}:{idx}:{marker_key.lower()}"

                results.append(SourceRationale(
                    rationale_id=rid,
                    marker_type=marker_key,
                    content=clean_text,
                    file_path=rel_path,
                    line_number=idx,
                    enclosing_symbol_id=enclosing_id,
                    content_hash=h,
                    citations=[c.upper() for c in citations]
                ))
                break  # Only one marker per comment line

    return results


def rationale_to_graph_entities(
    rationales: List[SourceRationale]
) -> tuple[List[Node], List[Edge]]:
    """Convert SourceRationale items into Node and Edge graph primitives."""
    nodes: List[Node] = []
    edges: List[Edge] = []

    for r in rationales:
        # Create Rationale Node
        r_node = Node(
            id=r.rationale_id,
            name=f"[{r.marker_type}] {r.content[:40]}...",
            node_type=NodeType.DOC,
            path=r.file_path,
            docstring=r.content,
            metadata={
                "marker_type": r.marker_type,
                "line": r.line_number,
                "content_hash": r.content_hash,
                "citations": r.citations
            }
        )
        nodes.append(r_node)

        # Bind to enclosing symbol if resolved, else bind to file node
        target_id = r.enclosing_symbol_id or f"file:{r.file_path}"
        edges.append(Edge(
            source_id=r.rationale_id,
            target_id=target_id,
            edge_type=EdgeType.REFERENCES,
            metadata={"provenance": "source_comment_rationale", "line": r.line_number}
        ))

        # Link to cited lifecycle ADRs or Stories
        for citation in r.citations:
            edges.append(Edge(
                source_id=r.rationale_id,
                target_id=f"doc:{citation}",
                edge_type=EdgeType.EVIDENCED_BY,
                metadata={"citation": citation}
            ))

    return nodes, edges
