"""Living C4 Architecture Wiki & Robert C. Martin Metrics Engine (DEV-034).

Synthesizes browsable, interconnected codebase documentation in `.agtoosa/wiki/`
with Obsidian [[wikilinks]], embedded Mermaid C4 architecture diagrams, and
package coupling/distance metrics (Ca, Ce, I, A, D).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.graph.store import GraphStore
from agtoosa.graph.community import detect_communities_modularity


@dataclass
class MartinMetrics:
    """Robert C. Martin Package Coupling and Stability Metrics."""
    afferent_coupling: int = 0  # Ca: incoming dependencies from outside
    efferent_coupling: int = 0  # Ce: outgoing dependencies to outside
    instability: float = 0.0    # I = Ce / (Ca + Ce)
    abstractness: float = 0.0   # A = abstract classes / total classes
    distance_from_main_sequence: float = 0.0  # D = |A + I - 1|

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CommunitySummary:
    """Architecture subsystem summary partitioned via modularity optimization."""
    community_id: str
    name: str
    nodes: List[Dict[str, Any]]
    internal_edges: List[Dict[str, Any]]
    external_edges: List[Dict[str, Any]]
    metrics: MartinMetrics = field(default_factory=MartinMetrics)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "community_id": self.community_id,
            "name": self.name,
            "node_count": len(self.nodes),
            "internal_edge_count": len(self.internal_edges),
            "external_edge_count": len(self.external_edges),
            "metrics": self.metrics.to_dict()
        }


class LivingWikiGenerator:
    """Generates interconnected Markdown architecture wiki with C4 diagrams and metrics."""

    def __init__(self, store: GraphStore, workspace_root: Optional[Path] = None):
        self.store = store
        self.workspace_root = (workspace_root or Path.cwd()).resolve()

    def analyze_communities(self) -> List[CommunitySummary]:
        """Partition graph into modularity communities and compute Martin metrics."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        if not nodes:
            return []

        # Filter out visual nodes to partition actual codebase
        code_nodes = [n for n in nodes if not n["id"].startswith("visual:")]
        node_map = {n["id"]: n for n in code_nodes}
        code_ids = set(node_map.keys())

        code_edges = [
            e for e in edges
            if e["source_id"] in code_ids and e["target_id"] in code_ids
        ]

        # First-party modularity community detection (DEV-048)
        det_res = detect_communities_modularity(code_nodes, code_edges, node_map=node_map)
        comm_nodes_map: Dict[str, List[Dict[str, Any]]] = {}

        if det_res.get("is_available") and det_res.get("communities"):
            for c_info in det_res["communities"]:
                cid = str(c_info["community_id"])
                for nid in c_info["members"]:
                    if nid in node_map:
                        comm_nodes_map.setdefault(cid, []).append(node_map[nid])
        else:
            # Fallback grouping by file path top directory
            for n in code_nodes:
                p = n.get("path", "")
                parts = Path(p).parts
                grp = parts[0] if parts else "root"
                comm_nodes_map.setdefault(grp, []).append(n)

        summaries: List[CommunitySummary] = []
        for comm_id, c_nodes in sorted(comm_nodes_map.items(), key=lambda x: len(x[1]), reverse=True):
            c_node_ids = {n["id"] for n in c_nodes}

            internal_e: List[Dict[str, Any]] = []
            external_e: List[Dict[str, Any]] = []
            afferent_count = 0
            efferent_count = 0

            for e in code_edges:
                src_in = e["source_id"] in c_node_ids
                tgt_in = e["target_id"] in c_node_ids

                if src_in and tgt_in:
                    internal_e.append(e)
                elif src_in and not tgt_in:
                    external_e.append(e)
                    efferent_count += 1
                elif not src_in and tgt_in:
                    external_e.append(e)
                    afferent_count += 1

            # Compute Martin metrics
            total_c = afferent_count + efferent_count
            instability = round(efferent_count / total_c, 4) if total_c > 0 else 0.0

            classes = [n for n in c_nodes if n.get("node_type") == "class"]
            # Approximate abstractness by classes containing "abstract", "base", "interface", "protocol" in name
            abstract_classes = [c for c in classes if any(k in c["name"].lower() for k in ["base", "abstract", "protocol", "interface"])]
            abstractness = round(len(abstract_classes) / max(1, len(classes)), 4) if classes else 0.0
            dist = round(abs(abstractness + instability - 1.0), 4)

            metrics = MartinMetrics(
                afferent_coupling=afferent_count,
                efferent_coupling=efferent_count,
                instability=instability,
                abstractness=abstractness,
                distance_from_main_sequence=dist
            )

            # Determine human readable community name from top dominant path or class
            paths = [n.get("path", "") for n in c_nodes if n.get("path")]
            if paths:
                # Find most common directory or module
                parts = [p.split("/")[0] if "/" in p else p for p in paths]
                dominant_dir = max(set(parts), key=parts.count)
                comm_name = f"Subsystem-{dominant_dir.replace('.', '_')}-{comm_id[:4]}"
            else:
                comm_name = f"Subsystem-{comm_id[:6]}"

            summaries.append(
                CommunitySummary(
                    community_id=comm_id,
                    name=comm_name,
                    nodes=c_nodes,
                    internal_edges=internal_e,
                    external_edges=external_e,
                    metrics=metrics
                )
            )

        return summaries

    def generate_c4_diagram(self, comm: CommunitySummary) -> str:
        """Generate a Mermaid C4Component diagram for a specific subsystem."""
        lines = ["```mermaid", "flowchart TD"]
        # Subsystem boundary
        lines.append(f"    subgraph {comm.name.replace('-', '_')}[\"{comm.name}\"]")
        node_aliases = {}
        for idx, n in enumerate(comm.nodes[:12], start=1):
            alias = f"c{idx}"
            node_aliases[n["id"]] = alias
            lines.append(f"        {alias}[\"{n['name']} ({n.get('node_type', 'symbol')})\"]")
        lines.append("    end")

        # Internal edges
        for e in comm.internal_edges:
            src = node_aliases.get(e["source_id"])
            tgt = node_aliases.get(e["target_id"])
            if src and tgt:
                lines.append(f"    {src} -->|{e.get('edge_type', 'calls')}| {tgt}")

        lines.append("```")
        return "\n".join(lines)

    def build_wiki(
        self,
        output_dir: Optional[Path] = None,
        wiki_dir: Optional[Path] = None,
        format: str = "obsidian"
    ) -> Dict[str, Any]:
        """Build structured Markdown wiki in output directory."""
        target_dir = wiki_dir or output_dir or (self.workspace_root / ".agtoosa" / "wiki")
        target_dir.mkdir(parents=True, exist_ok=True)
        wiki_dir = target_dir

        communities = self.analyze_communities()
        articles_created: List[str] = []

        # 1. Generate Index article
        index_lines = [
            f"# Repository Architecture Wiki",
            f"\nAuto-generated living C4 architecture wiki powered by Agtoosa2 modularity analysis.\n",
            f"## Subsystems Overview\n",
            f"| Subsystem | Components | Afferent (Ca) | Efferent (Ce) | Instability (I) | Distance (D) |",
            f"|---|:---:|:---:|:---:|:---:|:---:|"
        ]

        for c in communities:
            m = c.metrics
            link = f"[[{c.name}]]" if format == "obsidian" else f"[{c.name}]({c.name}.md)"
            index_lines.append(
                f"| {link} | {len(c.nodes)} | {m.afferent_coupling} | {m.efferent_coupling} | {m.instability:.2f} | {m.distance_from_main_sequence:.2f} |"
            )

        index_lines.append(f"\n---\n*Total Communities: {len(communities)} | Generated by Agtoosa2 (DEV-034)*\n")
        index_path = wiki_dir / "index.md"
        index_path.write_text("\n".join(index_lines), encoding="utf-8")
        articles_created.append("index.md")

        # 2. Generate Community articles
        for c in communities:
            c_lines = [
                f"# {c.name}",
                f"\n**Community ID:** `{c.community_id}` | **Members:** {len(c.nodes)} symbols\n",
                f"## Architecture Diagram",
                self.generate_c4_diagram(c),
                f"\n## Robert C. Martin Architecture Metrics",
                f"- **Afferent Coupling ($C_a$):** `{c.metrics.afferent_coupling}` (incoming external callers)",
                f"- **Efferent Coupling ($C_e$):** `{c.metrics.efferent_coupling}` (outgoing dependencies)",
                f"- **Instability ($I$):** `{c.metrics.instability:.4f}` ({'Highly Stable / Depended On' if c.metrics.instability < 0.3 else ('Unstable / Independent' if c.metrics.instability > 0.7 else 'Balanced')})",
                f"- **Abstractness ($A$):** `{c.metrics.abstractness:.4f}`",
                f"- **Distance from Main Sequence ($D$):** `{c.metrics.distance_from_main_sequence:.4f}`\n",
                f"## Member Symbols\n",
                f"| Symbol Name | Type | File Location |",
                f"|---|---|---|"
            ]

            for n in c.nodes[:25]:
                c_lines.append(f"| `{n['name']}` | {n.get('node_type', '')} | `{n.get('path', '')}` |")

            c_lines.append(f"\n[Back to Index](index.md)\n")
            art_file = wiki_dir / f"{c.name}.md"
            art_file.write_text("\n".join(c_lines), encoding="utf-8")
            articles_created.append(f"{c.name}.md")

        return {
            "output_dir": str(wiki_dir),
            "format": format,
            "total_communities": len(communities),
            "articles_created": articles_created,
            "communities": [c.to_dict() for c in communities]
        }

    generate_wiki = build_wiki
