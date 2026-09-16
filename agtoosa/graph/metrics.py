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

        adj_out_dep: Dict[str, List[str]] = defaultdict(list)
        for e in edges:
            src = e["source_id"]
            tgt = e["target_id"]
            if src in node_map and tgt in node_map:
                adj_out[src].append(tgt)
                adj_in[tgt].append(src)
                if e.get("edge_type") in ("calls", "imports", "depends_on", "routes_to", "inherits"):
                    adj_out_dep[src].append(tgt)

        # 1. PageRank & Hub Centrality
        pagerank = self._compute_pagerank(nodes, adj_out, adj_in)
        all_hubs = sorted(
            [{"id": nid, "name": node_map[nid]["name"], "type": node_map[nid]["node_type"], "score": round(score, 4)}
             for nid, score in pagerank.items()],
            key=lambda x: x["score"],
            reverse=True
        )
        top_hubs = all_hubs[:10]

        # Domain vs Infrastructure Hubs Classification (DEV-057)
        INFRA_NAMES = {
            "_get_connection", "logger", "log", "to_dict", "from_dict", "to_json",
            "from_json", "format", "render", "get_node", "insert_batch", "uuid", "config",
            "dict", "json", "as_dict", "Node", "Edge", "NodeType", "EdgeType", "format_text"
        }
        for h in top_hubs:
            is_infra = any(p.lower() == h["name"].lower() or p.lower() in h["name"].lower() for p in INFRA_NAMES)
            h["category"] = "infrastructure" if is_infra else "domain"

        top_domain_hubs = [h for h in all_hubs if not any(p.lower() in h["name"].lower() for p in INFRA_NAMES)][:5]
        top_infra_hubs = [h for h in all_hubs if any(p.lower() in h["name"].lower() for p in INFRA_NAMES)][:5]

        # 2. Cycle Detection (Tarjan's strongly connected components / elementary cycles)
        cycles = self._detect_cycles(nodes, adj_out_dep, node_map)

        # 3. Community Clustering
        communities = self._detect_communities(nodes, edges, node_map)

        # 4. Architecture Health Scorecard
        health = self._compute_health_scorecard(nodes, edges, adj_in, adj_out, cycles)

        # 5. Spectral & Algebraic Invariants
        from agtoosa.graph.spectral import SpectralEngine
        from agtoosa.graph.curvature import CurvatureEngine

        spectral_eng = SpectralEngine(nodes, edges)
        fiedler = spectral_eng.compute_fiedler_cut()
        sr = spectral_eng.compute_spectral_radius()
        entropy = spectral_eng.compute_von_neumann_entropy()

        spectral_data = {
            "algebraic_connectivity": fiedler["algebraic_connectivity"],
            "cheeger_conductance": fiedler["cheeger_conductance"],
            "cheeger_lower_bound": fiedler["cheeger_lower_bound"],
            "cheeger_upper_bound": fiedler["cheeger_upper_bound"],
            "spectral_radius": sr["spectral_radius"],
            "epidemic_threshold": sr["epidemic_threshold"],
            "von_neumann_entropy": entropy,
            "is_connected": fiedler["is_connected"]
        }

        # 6. Discrete Differential Geometry & Forman-Ricci Curvature
        curvature_eng = CurvatureEngine(nodes, edges)
        curvature_data = curvature_eng.compute_forman_ricci_curvature()

        return {
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "density": round(len(edges) / (len(nodes) * (len(nodes) - 1) + 1e-9), 4) if len(nodes) > 1 else 0.0,
            },
            "health_scorecard": health,
            "top_hubs": top_hubs,
            "top_domain_hubs": top_domain_hubs,
            "top_infra_hubs": top_infra_hubs,
            "cycles": cycles,
            "communities": communities,
            "spectral": spectral_data,
            "curvature": {
                "average_curvature": curvature_data["average_curvature"],
                "bottleneck_count": curvature_data["bottleneck_count"],
                "top_bottlenecks": curvature_data["top_bottlenecks"]
            }
        }

    def detect_cycles(self, max_cycles: int = 15) -> List[Dict[str, Any]]:
        """Detect circular dependencies and return formatted summary."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()
        node_map = {n["id"]: n for n in nodes}
        adj_out: Dict[str, List[str]] = defaultdict(list)
        for e in edges:
            if e.get("edge_type") in ("calls", "imports", "depends_on", "routes_to", "inherits"):
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

        # Check isolated code symbols / executable components
        isolated = [
            n["name"] for n in nodes
            if (
                n["node_type"] in ("function", "class", "service", "endpoint", "module")
                or (
                    n["node_type"] == "file"
                    and any(n.get("path", "").endswith(ext) for ext in (".py", ".js", ".ts", ".sh"))
                    and not n.get("path", "").endswith("__init__.py")
                    and not n.get("path", "").startswith("agtoosa/graph/web/")
                )
            )
            and len(adj_in[n["id"]]) == 0
            and len(adj_out[n["id"]]) == 0
        ]
        if isolated:
            warnings.append(f"{len(isolated)} disconnected/isolated nodes detected.")
            deductions += min(15, len(isolated) * 2)

        # Check circular dependencies
        if cycles:
            warnings.append(f"{len(cycles)} circular dependency chain(s) detected.")
            deductions += min(35, len(cycles) * 10)

        # Check verified code symbols
        code_nodes = [n for n in nodes if n["node_type"] in ("function", "class")]
        test_edges = [
            e for e in edges
            if e["edge_type"] in ("verifies", "evidenced_by")
            or (e["edge_type"] == "calls" and (e["source_id"].startswith(("func:tests/", "class:tests/")) or "tests/" in e["source_id"]))
        ]
        verified_targets = {e["target_id"] for e in test_edges}
        tested_count = sum(1 for c in code_nodes if c["id"] in verified_targets)
        test_ratio = round(tested_count / len(code_nodes), 2) if code_nodes else 1.0

        if test_ratio < 0.2 and len(code_nodes) > 5:
            warnings.append(f"Low test verification coverage: {int(test_ratio * 100)}% of code units verified.")
            deductions += 10

        # Score computation
        score = max(0, 100 - deductions)
        if score >= 95:
            grade = "A+"
        elif score >= 90:
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

        if "spectral" in report:
            spec = report["spectral"]
            lines.append("\n📐 Spectral & Geometric Invariants:")
            lines.append(f"   • Algebraic Connectivity (λ₂): {spec['algebraic_connectivity']} ({'Robust' if spec['is_connected'] else 'Disconnected/Fragile'})")
            lines.append(f"   • Cheeger Conductance Cut: h(G) = {spec['cheeger_conductance']} (Bounds: [{spec['cheeger_lower_bound']}, {spec['cheeger_upper_bound']}])")
            lines.append(f"   • Von Neumann Graph Entropy: {spec['von_neumann_entropy']} bits")
            lines.append(f"   • Spectral Radius: λ₁(A) = {spec['spectral_radius']} (Epidemic Threshold τ_c = {spec['epidemic_threshold']})")

        if "curvature" in report:
            curv = report["curvature"]
            lines.append(f"   • Forman-Ricci Geometric Bottlenecks: {curv['bottleneck_count']} fragile edge bridge(s) (Avg Curvature: {curv['average_curvature']})")
            for b in curv.get("top_bottlenecks", [])[:3]:
                lines.append(f"     - Choke Point: {b['source_name']} <-> {b['target_name']} (Curvature: {b['curvature']})")

        lines.append("\n💡 What This Means & Actionable Next Steps:")
        if health.get("isolated_count", 0) > 0:
            lines.append(f"   • 🧹 Prune Dead Code: Run 'agtoosa refactor dead-code --dry-run' to safely inspect {health['isolated_count']} candidate(s).")
        if report.get("top_hubs"):
            top_hub = report["top_hubs"][0]
            lines.append(f"   • 🔍 Inspect Gravity Hubs: Run 'agtoosa graph explain \"{top_hub['name']}\"' or 'agtoosa graph impact \"{top_hub['name']}\"'.")
        if health.get("cycle_count", 0) > 0:
            lines.append(f"   • 🔄 Decouple Cycles: Run 'agtoosa refactor decouple' to break circular dependencies.")
        if health.get("verified_units_ratio", 1.0) < 0.2:
            lines.append(f"   • 📜 Trace Requirements: Run 'agtoosa ship verify' to link story specs to test proof evidence.")
        lines.append("   • 🌐 Visual Studio: Run 'agtoosa graph view --serve' to explore interactive topology on port 8080.")
        lines.append("   • 🧭 Context for AI Agents: Run 'agtoosa query \"<symbol>\" --budget 1500' for token-budgeted GraphRAG.")

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

        if "spectral" in report or "curvature" in report:
            md.extend([
                "",
                "## 5. Spectral & Geometric Invariants",
                "",
                "| Invariant | Mathematical Value | Interpretation |",
                "|---|---|---|"
            ])
            if "spectral" in report:
                s = report["spectral"]
                md.append(f"| **Algebraic Connectivity ($\\lambda_2$)** | `{s['algebraic_connectivity']}` | {'Connected & structurally robust' if s['is_connected'] else 'Fragile / contains disconnected components'} |")
                md.append(f"| **Cheeger Conductance Cut ($h(G)$)** | `{s['cheeger_conductance']}` | Optimal bisection conductance (Bounds: `[{s['cheeger_lower_bound']}, {s['cheeger_upper_bound']}]`) |")
                md.append(f"| **Von Neumann Graph Entropy** | `{s['von_neumann_entropy']}` bits | Topological complexity and disorder |")
                md.append(f"| **Perron-Frobenius Spectral Radius ($\\lambda_1$)** | `{s['spectral_radius']}` | Epidemic percolation threshold: $\\tau_c = {s['epidemic_threshold']}$ |")
            if "curvature" in report:
                c = report["curvature"]
                md.append(f"| **Forman-Ricci Choke Points** | `{c['bottleneck_count']}` edges | Negative curvature bridges prone to failure |")

        return "\n".join(md)
