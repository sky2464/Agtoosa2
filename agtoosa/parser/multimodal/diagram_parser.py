"""Zero-dependency visual architecture diagram parser for Mermaid, PlantUML, and Excalidraw (DEV-033)."""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agtoosa.core.model import Node, Edge, NodeType, EdgeType


class DiagramParser:
    """Extracts conceptual architecture components and directed relationship edges from diagrams."""

    def parse_file(self, file_path: Path, workspace_root: Path) -> Tuple[List[Node], List[Edge]]:
        """Parse diagram file and return conceptual graph nodes and edges."""
        if not file_path.exists():
            return [], []

        rel_path = str(file_path.relative_to(workspace_root)) if file_path.is_relative_to(workspace_root) else str(file_path)
        content = file_path.read_text(encoding="utf-8", errors="replace")
        suffix = file_path.suffix.lower()

        if suffix in {".mmd", ".mermaid"}:
            return self.parse_mermaid(content, rel_path)
        elif suffix in {".puml", ".plantuml"}:
            return self.parse_plantuml(content, rel_path)
        elif suffix in {".excalidraw", ".json"} and "excalidraw" in file_path.name.lower():
            return self.parse_excalidraw(content, rel_path)
        else:
            # Fallback: check content heuristics
            if "graph TD" in content or "flowchart" in content or "C4Context" in content:
                return self.parse_mermaid(content, rel_path)
            elif "@startuml" in content:
                return self.parse_plantuml(content, rel_path)

        return [], []

    def parse_mermaid(self, text: str, rel_path: str) -> Tuple[List[Node], List[Edge]]:
        """Parse Mermaid flowchart or C4 diagram into components and connections."""
        nodes: Dict[str, Node] = {}
        edges: List[Edge] = []

        # 1. Match node declarations: ID["Label"] or ID[Label] or ID("Label") or ID{"Label"}
        node_decl_pattern = re.compile(r'([a-zA-Z0-9_-]+)\s*[\[\(\{]{1,2}["\']?([^"\'\]\)\}]+)["\']?[\]\)\}]{1,2}')
        for match in node_decl_pattern.finditer(text):
            node_id_raw = match.group(1).strip()
            label = match.group(2).strip()
            if node_id_raw.lower() in {"subgraph", "end", "flowchart", "graph", "direction"}:
                continue

            node_id = f"visual:{rel_path}:{node_id_raw}"
            if node_id not in nodes:
                nodes[node_id] = Node(
                    id=node_id,
                    name=label or node_id_raw,
                    node_type=NodeType.CONCEPT,
                    path=rel_path,
                    metadata={"is_visual": True, "diagram_id": node_id_raw, "diagram_type": "mermaid"}
                )

        # 2. Match directed edges line-by-line: A --> B or A["Label"] --> B["Label"] or A -->|text| B
        edge_pattern = re.compile(
            r'([a-zA-Z0-9_-]+)(?:\s*[\[\(\{][^\]\)\}]+[\]\)\}])?\s*--+(?:>|\|([^|]+)\|\s*>|([^-]+)--+>)\s*([a-zA-Z0-9_-]+)'
        )
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("%%"):
                continue
            match = edge_pattern.search(line)
            if not match:
                continue

            src_raw = match.group(1).strip()
            label = (match.group(2) or match.group(3) or "").strip()
            tgt_raw = match.group(4).strip()

            src_id = f"visual:{rel_path}:{src_raw}"
            tgt_id = f"visual:{rel_path}:{tgt_raw}"

            if src_id not in nodes:
                nodes[src_id] = Node(
                    id=src_id,
                    name=src_raw,
                    node_type=NodeType.CONCEPT,
                    path=rel_path,
                    metadata={"is_visual": True, "diagram_id": src_raw, "diagram_type": "mermaid"}
                )
            if tgt_id not in nodes:
                nodes[tgt_id] = Node(
                    id=tgt_id,
                    name=tgt_raw,
                    node_type=NodeType.CONCEPT,
                    path=rel_path,
                    metadata={"is_visual": True, "diagram_id": tgt_raw, "diagram_type": "mermaid"}
                )

            edges.append(
                Edge(
                    source_id=src_id,
                    target_id=tgt_id,
                    edge_type=EdgeType.REFERENCES,
                    provenance="extracted",
                    metadata={"is_visual": True, "label": label, "diagram_type": "mermaid"}
                )
            )

        return list(nodes.values()), edges

    def parse_plantuml(self, text: str, rel_path: str) -> Tuple[List[Node], List[Edge]]:
        """Parse PlantUML components and relationships."""
        nodes: Dict[str, Node] = {}
        edges: List[Edge] = []

        # Match component [Label] as ID or component ID
        comp_pattern = re.compile(r'(?:component|class|interface)\s+(?:\[([^\]]+)\]|"([^"]+)"|([a-zA-Z0-9_-]+))(?:\s+as\s+([a-zA-Z0-9_-]+))?')
        for match in comp_pattern.finditer(text):
            name = match.group(1) or match.group(2) or match.group(3) or ""
            alias = match.group(4) or name
            node_id = f"visual:{rel_path}:{alias}"
            nodes[node_id] = Node(
                id=node_id,
                name=name,
                node_type=NodeType.CONCEPT,
                path=rel_path,
                metadata={"is_visual": True, "diagram_id": alias, "diagram_type": "plantuml"}
            )

        # Match arrows: A --> B : label or A -> B
        arrow_pattern = re.compile(r'([a-zA-Z0-9_\[\]"-]+)\s*-+>\s*([a-zA-Z0-9_\[\]"-]+)(?:\s*:\s*(.+))?')
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("'"):
                continue
            match = arrow_pattern.search(line)
            if not match:
                continue

            src_raw = match.group(1).strip("[]\" ")
            tgt_raw = match.group(2).strip("[]\" ")
            label = (match.group(3) or "").strip()

            src_id = f"visual:{rel_path}:{src_raw}"
            tgt_id = f"visual:{rel_path}:{tgt_raw}"

            if src_id not in nodes:
                nodes[src_id] = Node(id=src_id, name=src_raw, node_type=NodeType.CONCEPT, path=rel_path, metadata={"is_visual": True})
            if tgt_id not in nodes:
                nodes[tgt_id] = Node(id=tgt_id, name=tgt_raw, node_type=NodeType.CONCEPT, path=rel_path, metadata={"is_visual": True})

            edges.append(
                Edge(
                    source_id=src_id,
                    target_id=tgt_id,
                    edge_type=EdgeType.REFERENCES,
                    provenance="extracted",
                    metadata={"is_visual": True, "label": label, "diagram_type": "plantuml"}
                )
            )

        return list(nodes.values()), edges

    def parse_excalidraw(self, json_text: str, rel_path: str) -> Tuple[List[Node], List[Edge]]:
        """Parse Excalidraw JSON elements for labeled shapes and bound arrows."""
        nodes: Dict[str, Node] = {}
        edges: List[Edge] = []

        try:
            data = json.loads(json_text)
            elements = data.get("elements", [])
        except Exception:
            return [], []

        # Find text elements and shapes
        text_by_id = {}
        for el in elements:
            if el.get("type") == "text":
                text_by_id[el.get("id")] = el.get("text", "")

        for el in elements:
            el_type = el.get("type")
            el_id = el.get("id")
            if el_type in {"rectangle", "ellipse", "diamond"}:
                # Look for bound text or nearest label
                label = el.get("text") or el.get("label", {}).get("text") or text_by_id.get(el_id) or f"{el_type}_{el_id[:4]}"
                node_id = f"visual:{rel_path}:{el_id}"
                nodes[node_id] = Node(
                    id=node_id,
                    name=label,
                    node_type=NodeType.CONCEPT,
                    path=rel_path,
                    metadata={"is_visual": True, "diagram_id": el_id, "diagram_type": "excalidraw"}
                )
            elif el_type == "arrow":
                start_binding = el.get("startBinding", {}).get("elementId")
                end_binding = el.get("endBinding", {}).get("elementId")
                if start_binding and end_binding:
                    src_id = f"visual:{rel_path}:{start_binding}"
                    tgt_id = f"visual:{rel_path}:{end_binding}"
                    edges.append(
                        Edge(
                            source_id=src_id,
                            target_id=tgt_id,
                            edge_type=EdgeType.REFERENCES,
                            provenance="extracted",
                            metadata={"is_visual": True, "diagram_type": "excalidraw"}
                        )
                    )

        return list(nodes.values()), edges
