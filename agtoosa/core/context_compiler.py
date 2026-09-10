"""Context Compiler v2: High-signal, token-efficient graph prompt packs for AI coding agents."""

from typing import Any, Dict, List, Optional, Set
from agtoosa.graph.store import GraphStore
from agtoosa.graph.query import resolve_node, compute_impact


class ContextCompiler:
    """Extracts bounded subgraphs and renders clean Markdown context packs for LLMs."""

    def __init__(self, store: GraphStore):
        self.store = store

    def compile_context(self, target_id: str, radius: int = 2, hybrid: bool = False) -> Optional[str]:
        """Compile a bounded prompt pack for a target task, story, or symbol."""
        target_node = resolve_node(self.store, target_id)
        if not target_node:
            return None

        node_type = target_node["node_type"]
        
        # 1. Gather Story and Criteria
        story_node = None
        criteria: List[Dict[str, Any]] = []
        tasks: List[Dict[str, Any]] = []

        if node_type == "story":
            story_node = target_node
            neighbors = self.store.get_neighbors(story_node["id"], direction="out")
            for n in neighbors:
                if n["node_type"] == "criterion":
                    criteria.append(n)
                elif n["node_type"] == "task":
                    tasks.append(n)
        elif node_type == "task":
            # Find parent story
            in_neighbors = self.store.get_neighbors(target_node["id"], direction="in")
            for n in in_neighbors:
                if n["node_type"] == "story":
                    story_node = n
                    break
            if story_node:
                s_neighbors = self.store.get_neighbors(story_node["id"], direction="out")
                for n in s_neighbors:
                    if n["node_type"] == "criterion":
                        criteria.append(n)
            tasks.append(target_node)
        elif node_type in ("function", "class", "file"):
            # Symbol-focused context
            impact_res = compute_impact(self.store, target_node["id"], max_depth=radius)
            sem_related = None
            if hybrid:
                try:
                    from agtoosa.graph.query import hybrid_search
                    query_text = f"{target_node['name']} {target_node.get('docstring', '')}"
                    matches = hybrid_search(self.store, query_text, top_k=6)
                    sem_related = [m for m in matches if m["node"]["id"] != target_node["id"]]
                except Exception:
                    sem_related = None
            return self._render_symbol_pack(target_node, impact_res, sem_related)

        # 2. Extract relevant code symbols mentioned in criteria or tasks
        symbols = self._find_related_code_symbols(story_node, criteria, tasks, hybrid=hybrid)

        # 3. Render Markdown Context Pack
        return self._render_lifecycle_pack(story_node or target_node, criteria, tasks, symbols, hybrid=hybrid)

    def _find_related_code_symbols(
        self,
        story: Optional[Dict[str, Any]],
        criteria: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        hybrid: bool = False
    ) -> List[Dict[str, Any]]:
        text_corpus = ""
        if story:
            text_corpus += f"{story['name']} {story.get('docstring', '')} "
        for c in criteria:
            text_corpus += f"{c['name']} {c.get('docstring', '')} "
        for t in tasks:
            text_corpus += f"{t['name']} {t.get('docstring', '')} "

        if not text_corpus.strip():
            return []

        # If hybrid search is requested, use Hybrid GraphRAG v2 (Vector + FTS5 RRF)
        if hybrid:
            try:
                from agtoosa.graph.query import hybrid_search
                hybrid_matches = hybrid_search(self.store, text_corpus, top_k=15)
                symbols: List[Dict[str, Any]] = []
                seen: Set[str] = set()
                for item in hybrid_matches:
                    n = item["node"]
                    if n["node_type"] in ("function", "class", "file") and n["id"] not in seen:
                        seen.add(n["id"])
                        node_copy = dict(n)
                        node_copy["rrf_score"] = item.get("rrf_score")
                        node_copy["vector_score"] = item.get("vector_score")
                        node_copy["match_source"] = item.get("match_source")
                        symbols.append(node_copy)
                if symbols:
                    return symbols[:10]
            except Exception:
                pass

        # Clean words and build single-pass query
        words = [w.strip("`'\",():.") for w in text_corpus.split() if len(w) > 4 and w.isalnum()]
        if not words:
            return []

        # Deduplicate terms while preserving order
        unique_words = list(dict.fromkeys(words))[:20]
        query_terms = " OR ".join(unique_words)

        try:
            matches = self.store.query_fts(query_terms, limit=20)
            symbols = [m for m in matches if m["node_type"] in ("function", "class")]
            return symbols[:10]
        except Exception:
            # Fallback to batched individual queries if compound query syntax fails
            symbols: List[Dict[str, Any]] = []
            seen_ids: Set[str] = set()
            for word in unique_words[:8]:
                for m in self.store.query_fts(word, limit=3):
                    if m["node_type"] in ("function", "class") and m["id"] not in seen_ids:
                        seen_ids.add(m["id"])
                        symbols.append(m)
            return symbols[:10]

    def _render_lifecycle_pack(
        self,
        root_node: Dict[str, Any],
        criteria: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        symbols: List[Dict[str, Any]],
        hybrid: bool = False
    ) -> str:
        lines = []
        engine_label = " (Hybrid GraphRAG v2)" if hybrid else ""
        lines.append(f"# Agtoosa Context Pack{engine_label}: {root_node['name']}")
        lines.append(f"> **Target ID:** `{root_node['id']}`")
        lines.append(f"> **Source Spec:** `{root_node['path']}`\n")

        if criteria:
            lines.append("## Acceptance Criteria (EARS Requirements)")
            for c in criteria:
                doc = f" — {c['docstring']}" if c.get("docstring") else ""
                lines.append(f"- **{c['name']}**{doc}")
            lines.append("")

        if tasks:
            lines.append("## Assigned Tasks")
            for t in tasks:
                meta = t.get("metadata", {})
                status = "✅ Completed" if meta.get("completed") else "🟨 Todo"
                doc = f": {t['docstring']}" if t.get("docstring") else ""
                lines.append(f"- [{status}] **{t['name']}**{doc}")
            lines.append("")

        if symbols:
            title = "## Direct Code Context (Hybrid Vector & Graph Retrieval)" if hybrid else "## Direct Code Context (Symbols & Locations)"
            lines.append(title)
            for s in symbols:
                line_info = f":L{s['start_line']}" if s.get("start_line") else ""
                doc = f"\n  > {s['docstring'][:120]}..." if s.get("docstring") else ""
                score_badge = ""
                if s.get("vector_score") is not None:
                    score_badge = f" [Cosine: {s['vector_score']:.3f}, Source: {s.get('match_source', 'hybrid')}]"
                lines.append(f"- `{s['node_type'].upper()}` **{s['name']}** ({s['path']}{line_info}){score_badge}{doc}")
            lines.append("")

        # Architectural memory injection
        try:
            from agtoosa.review.memory import ArchitecturalMemory
            memory = ArchitecturalMemory(self.store)
            rules = memory.get_relevant_rules(root_node.get("name"))
            if rules:
                lines.append("## Architectural Invariants & Memory")
                for r in rules[:5]:
                    lines.append(f"- ⚠️ **Invariant:** {r}")
                lines.append("")
        except Exception:
            pass

        lines.append("## Instructions for AI Assistant")
        lines.append("1. Fulfill only the assigned tasks above while strictly obeying the Acceptance Criteria.")
        lines.append("2. Do not modify unlinked modules or alter unrelated public interfaces.")
        lines.append("3. Verify your implementation by running targeted tests before reporting completion.")

        return "\n".join(lines)

    def _render_symbol_pack(
        self,
        target: Dict[str, Any],
        impact: Optional[Dict[str, Any]],
        sem_related: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        lines = []
        lines.append(f"# Symbol Context Pack: {target['name']}")
        lines.append(f"> **Type:** `{target['node_type'].upper()}` | **Location:** `{target['path']}`")
        if target.get("docstring"):
            lines.append(f"> **Docstring:** {target['docstring']}\n")

        if sem_related:
            lines.append(f"## Semantically Related Symbols (Hybrid GraphRAG)")
            for item in sem_related[:5]:
                node = item["node"]
                score = item.get("vector_score", 0.0)
                source = item.get("match_source", "hybrid")
                lines.append(f"- `{node['node_type'].upper()}` **{node['name']}** ({node['path']}) [Similarity: {score:.3f} | {source}]")
            lines.append("")

        if impact and impact.get("impacted"):
            lines.append(f"## Blast Radius ({impact['impacted_count']} upstream callers/dependents)")
            lines.append("Be careful not to break the following dependents when refactoring:")
            for imp in impact["impacted"][:10]:
                lines.append(f"- [Hop {imp['depth']}] `{imp['node_type'].upper()}` **{imp['name']}** ({imp['path']}) via {imp['relationship']}")
            lines.append("")

        return "\n".join(lines)
