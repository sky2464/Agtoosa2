"""Graph intelligence, metrics, community detection, and architectural health scorecard."""

from collections import defaultdict, deque
import json
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.graph.store import GraphStore

try:
    import networkx as nx  # type: ignore[import-not-found,import-untyped]
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


class MetricsEngine:
    """Computes PageRank, circular dependencies, modularity, and architectural health metrics."""

    def __init__(self, store: GraphStore):
        self.store = store

    def compute_all(self) -> Dict[str, Any]:
        """Compute the full suite of graph metrics and health indicators."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        node_map = {n["id"]: n for n in nodes}
        adj_out: Dict[str, List[str]] = defaultdict(list)
        adj_in: Dict[str, List[str]] = defaultdict(list)

        for e in edges:
            src = e["source_id"]
            tgt = e["target_id"]
            if src in node_map and tgt in node_map:
                adj_out[src].append(tgt)
                adj_in[tgt].append(src)

        # 1. PageRank & Hub Centrality
        pagerank = self._compute_pagerank(nodes, adj_out, adj_in)
        top_hubs = sorted(
            [{"id": nid, "name": node_map[nid]["name"], "type": node_map[nid]["node_type"], "score": round(score, 4)}
             for nid, score in pagerank.items()],
            key=lambda x: x["score"],
            reverse=True
        )[:10]

        # 2. Cycle Detection (Tarjan's strongly connected components / elementary cycles)
        cycles = self._detect_cycles(nodes, adj_out, node_map)

        # 3. Community Clustering
        communities = self._detect_communities(nodes, edges, node_map)

        # 4. Architecture Health Scorecard
        health = self._compute_health_scorecard(nodes, edges, adj_in, adj_out, cycles)

        return {
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "density": round(len(edges) / (len(nodes) * (len(nodes) - 1) + 1e-9), 4) if len(nodes) > 1 else 0.0,
            },
            "health_scorecard": health,
            "top_hubs": top_hubs,
            "cycles": cycles,
            "communities": communities
        }

    def detect_cycles(self, max_cycles: int = 15) -> List[Dict[str, Any]]:
        """Detect circular dependencies and return formatted summary."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()
        node_map = {n["id"]: n for n in nodes}
        adj_out: Dict[str, List[str]] = defaultdict(list)
        for e in edges:
            if e.get("edge_type") not in ("contains",):
                adj_out[e["source_id"]].append(e["target_id"])

        raw_cycles = self._detect_cycles(nodes, adj_out, node_map, max_cycles=max_cycles)
        result = []
        for c in raw_cycles:
            names = [n["name"] for n in c]
            result.append({
                "length": len(c),
                "cycle_nodes": names,
                "nodes": c
            })
        return result

    def _compute_pagerank(self, nodes: List[Dict[str, Any]], adj_out: Dict[str, List[str]], adj_in: Dict[str, List[str]],
                          alpha: float = 0.85, max_iter: int = 100, tol: float = 1e-6) -> Dict[str, float]:
        """Compute PageRank using NetworkX or pure-Python power iteration fallback."""
        if not nodes:
            return {}

        if HAS_NETWORKX:
            try:
                g = nx.DiGraph()
                for n in nodes:
                    g.add_node(n["id"])
                for src, tgts in adj_out.items():
                    for tgt in tgts:
                        g.add_edge(src, tgt)
                # pyrefly: ignore [bad-return]
                return dict(nx.pagerank(g, alpha=alpha, max_iter=max_iter, tol=tol))
            except Exception:
                pass

        # Pure-Python Power Iteration
        n = len(nodes)
        node_ids = [node["id"] for node in nodes]
        rank = {nid: 1.0 / n for nid in node_ids}

        for _ in range(max_iter):
            new_rank = {}
            dangling_sum = sum(rank[nid] for nid in node_ids if len(adj_out[nid]) == 0)
            dangling_contrib = alpha * (dangling_sum / n)

            diff = 0.0
            for nid in node_ids:
                in_contrib = sum(rank[src] / len(adj_out[src]) for src in adj_in[nid] if len(adj_out[src]) > 0)
                new_val = (1.0 - alpha) / n + dangling_contrib + alpha * in_contrib
                diff += abs(new_val - rank[nid])
                new_rank[nid] = new_val

            rank = new_rank
            if diff < tol:
                break

        return rank

    def _detect_cycles(self, nodes: List[Dict[str, Any]], adj_out: Dict[str, List[str]],
                       node_map: Dict[str, Dict[str, Any]], max_cycles: int = 15) -> List[List[Dict[str, Any]]]:
        """Detect circular dependencies among non-containment edges."""
        if HAS_NETWORKX:
            try:
                g = nx.DiGraph()
                for n in nodes:
                    g.add_node(n["id"])
                for src, tgts in adj_out.items():
                    for tgt in tgts:
                        g.add_edge(src, tgt)

                raw_cycles = []
                for cycle in nx.simple_cycles(g):
                    if len(cycle) > 1:
                        raw_cycles.append(cycle)
                        if len(raw_cycles) >= max_cycles:
                            break

                formatted = []
                for c in raw_cycles:
                    formatted.append([
                        {"id": str(nid), "name": node_map.get(str(nid), {}).get("name", str(nid)),
                         "path": node_map.get(str(nid), {}).get("path", "")}
                        for nid in c
                    ])
                return formatted
            except Exception:
                pass

        # Pure-Python DFS Cycle Finder
        visited: Set[str] = set()
        on_stack: Set[str] = set()
        path: List[str] = []
        found_cycles: List[List[str]] = []

        def dfs(curr: str):
            if len(found_cycles) >= max_cycles:
                return
            visited.add(curr)
            on_stack.add(curr)
            path.append(curr)

            for neighbor in adj_out[curr]:
                if neighbor in on_stack:
                    # Found cycle
                    cycle_idx = path.index(neighbor)
                    cycle = path[cycle_idx:]
                    if len(cycle) > 1:
                        found_cycles.append(list(cycle))
                        if len(found_cycles) >= max_cycles:
                            break
                elif neighbor not in visited:
                    dfs(neighbor)

            path.pop()
            on_stack.remove(curr)

        for n in nodes:
            nid = n["id"]
            if nid not in visited:
                dfs(nid)

        formatted = []
        for c in found_cycles:
            formatted.append([
                {"id": nid, "name": node_map.get(nid, {}).get("name", nid),
                 "path": node_map.get(nid, {}).get("path", "")}
                for nid in c
            ])
        return formatted

    def _detect_communities(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]],
                            node_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group nodes into modular communities / sub-graphs using first-party modularity optimization (DEV-048)."""
        from agtoosa.graph.community import detect_communities_modularity
        res = detect_communities_modularity(nodes, edges, node_map)
        return res.get("communities", [])

    def _compute_health_scorecard(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]],
                                  adj_in: Dict[str, List[str]], adj_out: Dict[str, List[str]],
                                  cycles: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Evaluate architectural health metrics and assign grade."""
        total_nodes = len(nodes)
        if total_nodes == 0:
            return {"score": 100, "grade": "A+", "warnings": []}

        warnings = []
        deductions = 0

        # Check isolated nodes
        isolated = [n["name"] for n in nodes if len(adj_in[n["id"]]) == 0 and len(adj_out[n["id"]]) == 0]
        if isolated:
            warnings.append(f"{len(isolated)} disconnected/isolated nodes detected.")
            deductions += min(15, len(isolated) * 2)

        # Check circular dependencies
        if cycles:
            warnings.append(f"{len(cycles)} circular dependency chain(s) detected.")
            deductions += min(35, len(cycles) * 10)

        # Check verified code symbols
        code_nodes = [n for n in nodes if n["node_type"] in ("function", "class")]
        test_edges = [e for e in edges if e["edge_type"] in ("verifies", "evidenced_by")]
        verified_targets = {e["target_id"] for e in test_edges}
        tested_count = sum(1 for c in code_nodes if c["id"] in verified_targets)
        test_ratio = round(tested_count / len(code_nodes), 2) if code_nodes else 1.0

        if test_ratio < 0.2 and len(code_nodes) > 5:
            warnings.append(f"Low test verification coverage: {int(test_ratio * 100)}% of code units verified.")
            deductions += 10

        # Score computation
        score = max(0, 100 - deductions)
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"

        return {
            "score": score,
            "grade": grade,
            "warnings": warnings,
            "isolated_count": len(isolated),
            "cycle_count": len(cycles),
            "code_units_count": len(code_nodes),
            "verified_units_ratio": test_ratio
        }

    def format_text(self, report: Dict[str, Any]) -> str:
        """Format metrics into terminal-friendly text."""
        lines: List[str] = []
        lines.append("=" * 60)
        lines.append("📊 Agtoosa2 Architecture Health & Graph Intelligence Report")
        lines.append("=" * 60)

        stats = report["stats"]
        lines.append(f"\n📈 Topology Overview:")
        lines.append(f"   • Total Nodes: {stats['total_nodes']}")
        lines.append(f"   • Total Edges: {stats['total_edges']}")
        lines.append(f"   • Graph Density: {stats['density']}")

        health = report["health_scorecard"]
        lines.append(f"\n🛡️ Architectural Health Scorecard:")
        lines.append(f"   • Grade: {health['grade']} ({health['score']}/100)")
        lines.append(f"   • Circular Dependency Chains: {health['cycle_count']}")
        lines.append(f"   • Disconnected Nodes: {health['isolated_count']}")
        lines.append(f"   • Code Units Verified: {int(health['verified_units_ratio'] * 100)}%")

        if health["warnings"]:
            lines.append("\n   ⚠️  Warnings:")
            for w in health["warnings"]:
                lines.append(f"     - {w}")

        if report["cycles"]:
            lines.append(f"\n🔄 Circular Dependencies Detected ({len(report['cycles'])}):")
            for idx, c in enumerate(report["cycles"], start=1):
                cycle_str = " -> ".join([f"{item['name']} ({item['path']})" for item in c])
                cycle_str += f" -> {c[0]['name']}"
                lines.append(f"   [{idx}] {cycle_str}")

        lines.append("\n🌟 Top Critical Hubs (PageRank Centrality):")
        for idx, hub in enumerate(report["top_hubs"][:5], start=1):
            lines.append(f"   [{idx}] {hub['type'].upper()}: {hub['name']} (Score: {hub['score']})")

        lines.append(f"\n🧩 Modular Communities ({len(report['communities'])}):")
        for comm in report["communities"][:4]:
            members = ", ".join(comm["sample_members"][:3])
            lines.append(f"   • Community #{comm['community_id']} ({comm['size']} nodes): {members}...")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def format_markdown(self, report: Dict[str, Any]) -> str:
        """Format metrics into Github-Flavored Markdown."""
        stats = report["stats"]
        health = report["health_scorecard"]

        md: List[str] = [
            "# Agtoosa2 Architecture Health & Graph Intelligence Report",
            "",
            "## 1. Executive Scorecard",
            "",
            f"| Metric | Value |",
            f"|---|---|",
            f"| **Overall Health Grade** | **`{health['grade']}`** ({health['score']}/100) |",
            f"| **Total Entities** | {stats['total_nodes']} |",
            f"| **Total Relationships** | {stats['total_edges']} |",
            f"| **Graph Density** | {stats['density']} |",
            f"| **Circular Dependencies** | {health['cycle_count']} |",
            f"| **Isolated Entities** | {health['isolated_count']} |",
            f"| **Code Verification Ratio** | {int(health['verified_units_ratio'] * 100)}% |",
            "",
            "## 2. Top Critical Hubs (PageRank Centrality)",
            "",
            "| Rank | Type | Symbol | PageRank Score |",
            "|---|---|---|---|"
        ]

        for idx, hub in enumerate(report["top_hubs"], start=1):
            md.append(f"| {idx} | `{hub['type']}` | `{hub['name']}` | {hub['score']} |")

        if report["cycles"]:
            md.extend([
                "",
                "## 3. Circular Dependencies",
                "",
                "The following circular call or dependency paths were detected:",
                ""
            ])
            for idx, c in enumerate(report["cycles"], start=1):
                cycle_str = " -> ".join([f"`{item['name']}`" for item in c]) + f" -> `{c[0]['name']}`"
                md.append(f"- **Cycle {idx}**: {cycle_str}")

        md.extend([
            "",
            "## 4. Modular Communities",
            "",
            "| Community | Size | Sample Members |",
            "|---|---|---|"
        ])
        for comm in report["communities"]:
            samples = ", ".join([f"`{m}`" for m in comm["sample_members"][:4]])
            md.append(f"| #{comm['community_id']} | {comm['size']} | {samples} |")

        return "\n".join(md)
