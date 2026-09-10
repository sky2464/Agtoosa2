"""Multi-format graph export: JSON, Obsidian Vault, GraphML, Cypher, and Graphviz DOT."""

from collections import defaultdict
import html
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from agtoosa.graph.store import GraphStore


class MultiFormatExporter:
    """Exports Agtoosa2 knowledge graph to various external ecosystem formats."""

    SUPPORTED_FORMATS = ("json", "obsidian", "graphml", "cypher", "dot")

    def __init__(self, store: GraphStore):
        self.store = store

    def export(self, format_name: str, output_path: Optional[Path] = None) -> str:
        """Export graph to the specified format. Writes to disk if output_path is provided."""
        fmt = format_name.lower().strip()
        if fmt not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format '{format_name}'. Must be one of: {', '.join(self.SUPPORTED_FORMATS)}")

        if fmt == "json":
            content = self.to_json()
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(content, encoding="utf-8")
            return content

        elif fmt == "obsidian":
            return self.to_obsidian_vault(output_path)

        elif fmt == "graphml":
            content = self.to_graphml()
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(content, encoding="utf-8")
            return content

        elif fmt == "cypher":
            content = self.to_cypher()
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(content, encoding="utf-8")
            return content

        elif fmt == "dot":
            content = self.to_dot()
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(content, encoding="utf-8")
            return content

        return ""

    def to_json(self) -> str:
        """Export to Agtoosa2 JSON representation."""
        data = self.store.export_json()
        return json.dumps(data, indent=2)

    def to_obsidian_vault(self, target_dir: Optional[Path] = None) -> str:
        """Export graph to an Obsidian-compatible Markdown vault with [[wikilinks]]."""
        if not target_dir:
            target_dir = Path(".agtoosa") / "obsidian_vault"

        target_dir.mkdir(parents=True, exist_ok=True)

        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        node_map = {n["id"]: n for n in nodes}
        out_edges: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        in_edges: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for e in edges:
            src, tgt = e["source_id"], e["target_id"]
            if src in node_map and tgt in node_map:
                out_edges[src].append(e)
                in_edges[tgt].append(e)

        def sanitize_filename(nid: str, name: str) -> str:
            raw = f"{nid.replace(':', '_')}_{name}"
            clean = re.sub(r'[\\/*?:"<>| ]', '_', raw)
            return clean[:100]

        node_filenames = {n["id"]: sanitize_filename(n["id"], n["name"]) for n in nodes}

        # Write each node note
        for n in nodes:
            nid = n["id"]
            fname = node_filenames[nid] + ".md"
            note_path = target_dir / fname

            lines = [
                "---",
                f'id: "{nid}"',
                f'name: "{n["name"]}"',
                f'type: "{n["node_type"]}"',
                f'path: "{n["path"]}"'
            ]
            if n.get("start_line"):
                lines.append(f"start_line: {n['start_line']}")
            lines.extend([
                "---",
                "",
                f"# {n['name']} (`{n['node_type']}`)",
                "",
                f"**File Location**: `{n['path']}`" + (f":L{n['start_line']}" if n.get("start_line") else ""),
                ""
            ])

            if n.get("docstring"):
                lines.extend([
                    "## Description",
                    "",
                    n["docstring"],
                    ""
                ])

            if out_edges[nid]:
                lines.append("## Outgoing Relationships")
                for e in out_edges[nid]:
                    tgt_id = e["target_id"]
                    tgt_node = node_map[tgt_id]
                    tgt_fname = node_filenames[tgt_id]
                    lines.append(f"- **{e['edge_type'].upper()}** ➔ [[{tgt_fname}|{tgt_node['name']}]] (`{tgt_node['node_type']}`)")
                lines.append("")

            if in_edges[nid]:
                lines.append("## Incoming Relationships")
                for e in in_edges[nid]:
                    src_id = e["source_id"]
                    src_node = node_map[src_id]
                    src_fname = node_filenames[src_id]
                    lines.append(f"- **{e['edge_type'].upper()}** from [[{src_fname}|{src_node['name']}]] (`{src_node['node_type']}`)")
                lines.append("")

            note_path.write_text("\n".join(lines), encoding="utf-8")

        # Write Index.md
        index_path = target_dir / "Index.md"
        idx_lines = [
            "# Agtoosa2 Knowledge Graph Vault Index",
            "",
            f"Total Entities: {len(nodes)} | Total Relationships: {len(edges)}",
            "",
            "## Entities by Category",
            ""
        ]

        by_type = defaultdict(list)
        for n in nodes:
            by_type[n["node_type"]].append(n)

        for ntype, items in sorted(by_type.items()):
            idx_lines.append(f"### {ntype.capitalize()} ({len(items)})")
            for item in sorted(items, key=lambda x: x["name"]):
                item_fname = node_filenames[item["id"]]
                idx_lines.append(f"- [[{item_fname}|{item['name']}]] (`{item['path']}`)")
            idx_lines.append("")

        index_path.write_text("\n".join(idx_lines), encoding="utf-8")
        return f"Obsidian vault created at {target_dir} ({len(nodes)} notes + Index.md)"

    def to_graphml(self) -> str:
        """Export graph to standard GraphML XML format."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        xml = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"',
            '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">',
            '  <key id="name" for="node" attr.name="name" attr.type="string"/>',
            '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
            '  <key id="path" for="node" attr.name="path" attr.type="string"/>',
            '  <key id="doc" for="node" attr.name="doc" attr.type="string"/>',
            '  <key id="edge_type" for="edge" attr.name="edge_type" attr.type="string"/>',
            '  <key id="provenance" for="edge" attr.name="provenance" attr.type="string"/>',
            '  <graph id="AgtoosaGraph" edgedefault="directed">'
        ]

        for n in nodes:
            nid = html.escape(n["id"])
            name = html.escape(n["name"])
            ntype = html.escape(n["node_type"])
            path = html.escape(n["path"])
            doc = html.escape(n.get("docstring") or "")
            xml.append(f'    <node id="{nid}">')
            xml.append(f'      <data key="name">{name}</data>')
            xml.append(f'      <data key="type">{ntype}</data>')
            xml.append(f'      <data key="path">{path}</data>')
            if doc:
                xml.append(f'      <data key="doc">{doc}</data>')
            xml.append('    </node>')

        for idx, e in enumerate(edges, start=1):
            src = html.escape(e["source_id"])
            tgt = html.escape(e["target_id"])
            etype = html.escape(e["edge_type"])
            prov = html.escape(e.get("provenance", "extracted"))
            xml.append(f'    <edge id="e{idx}" source="{src}" target="{tgt}">')
            xml.append(f'      <data key="edge_type">{etype}</data>')
            xml.append(f'      <data key="provenance">{prov}</data>')
            xml.append('    </edge>')

        xml.append('  </graph>')
        xml.append('</graphml>')
        return "\n".join(xml)

    def to_cypher(self) -> str:
        """Export graph to Neo4j / Memgraph Cypher statements."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        lines = [
            "// Agtoosa2 Knowledge Graph Cypher Export",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Node) REQUIRE n.id IS UNIQUE;",
            ""
        ]

        def clean_cypher_str(s: str) -> str:
            return s.replace("\\", "\\\\").replace("'", "\\'")

        # Create nodes in batches
        for n in nodes:
            label = "".join(part.capitalize() for part in n["node_type"].split("_"))
            nid = clean_cypher_str(n["id"])
            name = clean_cypher_str(n["name"])
            path = clean_cypher_str(n["path"])
            doc = clean_cypher_str(n.get("docstring") or "")
            lines.append(
                f"MERGE (n:Node:{label} {{id: '{nid}'}}) "
                f"ON CREATE SET n.name = '{name}', n.path = '{path}', n.docstring = '{doc}';"
            )

        lines.append("")

        # Create relationships
        for e in edges:
            rel_type = e["edge_type"].upper().replace("-", "_")
            src = clean_cypher_str(e["source_id"])
            tgt = clean_cypher_str(e["target_id"])
            prov = clean_cypher_str(e.get("provenance", "extracted"))
            lines.append(
                f"MATCH (s:Node {{id: '{src}'}}), (t:Node {{id: '{tgt}'}}) "
                f"MERGE (s)-[:{rel_type} {{provenance: '{prov}'}}]->(t);"
            )

        return "\n".join(lines)

    def to_dot(self) -> str:
        """Export graph to Graphviz DOT notation."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        # Color mapping by node category
        colors = {
            "file": "#475569",
            "module": "#334155",
            "class": "#0284c7",
            "function": "#2563eb",
            "variable": "#64748b",
            "import": "#94a3b8",
            "story": "#7c3aed",
            "epic": "#6d28d9",
            "criterion": "#9333ea",
            "task": "#a855f7",
            "test": "#059669",
            "evidence": "#10b981",
            "adr": "#d97706",
            "doc": "#b45309"
        }

        lines = [
            "digraph Agtoosa2Graph {",
            '  graph [rankdir=LR, bgcolor="#0f172a", fontcolor="#f8fafc", fontname="Helvetica"];',
            '  node [shape=box, style="filled,rounded", fontcolor="#ffffff", fontname="Helvetica", fontsize=10];',
            '  edge [color="#64748b", fontcolor="#94a3b8", fontname="Helvetica", fontsize=8];',
            ""
        ]

        def clean_dot_id(nid: str) -> str:
            return '"' + nid.replace('"', '\\"') + '"'

        for n in nodes:
            dot_id = clean_dot_id(n["id"])
            color = colors.get(n["node_type"], "#3b82f6")
            label = f"{n['name']}\\n({n['node_type']})"
            lines.append(f'  {dot_id} [label="{label}", fillcolor="{color}"];')

        lines.append("")

        for e in edges:
            src = clean_dot_id(e["source_id"])
            tgt = clean_dot_id(e["target_id"])
            etype = e["edge_type"]
            lines.append(f'  {src} -> {tgt} [label="{etype}"];')

        lines.append("}")
        return "\n".join(lines)
