"""Universal Multi-Host Agent Skill & Token-Budgeted Topology Traversal (DEV-037).

Provides:
1. TopologyContextCompiler: PageRank-guided AST skeleton pruning under strict token budgets.
2. SkillInstaller: Automated generator and installer for Claude Code, Antigravity, and Cursor.
"""

from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field, asdict
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.graph.store import GraphStore
from agtoosa.graph.query import hybrid_search, resolve_node


@dataclass
class BudgetedContextPack:
    """Bounded, token-pruned topology context pack for AI agents."""
    query: str
    budget_tokens: int
    tokens_used: int
    strategy: str
    nodes_included: int
    content: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TopologyContextCompiler:
    """Compiles high-signal AST code skeletons prioritized by graph centrality under strict token limits."""

    def __init__(self, store: GraphStore):
        self.store = store

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (standard ~4 characters per token heuristic)."""
        return max(1, math.ceil(len(text) / 4))

    def _compute_pagerank(self, damping: float = 0.85, max_iter: int = 20) -> Dict[str, float]:
        """Compute basic PageRank scores over the code graph."""
        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        if not nodes:
            return {}

        node_ids = [n["id"] for n in nodes]
        n_nodes = len(node_ids)
        if n_nodes == 0:
            return {}

        out_links: Dict[str, List[str]] = defaultdict(list)
        for e in edges:
            src = e["source_id"]
            tgt = e["target_id"]
            out_links[src].append(tgt)

        ranks: Dict[str, float] = {nid: 1.0 / n_nodes for nid in node_ids}

        for _ in range(max_iter):
            new_ranks: Dict[str, float] = {}
            for nid in node_ids:
                in_score = 0.0
                # Incoming edges
                for other, targets in out_links.items():
                    if nid in targets and len(targets) > 0:
                        in_score += ranks[other] / len(targets)
                new_ranks[nid] = (1.0 - damping) / n_nodes + damping * in_score
            ranks = new_ranks

        return ranks

    def _render_skeleton(self, node: Dict[str, Any]) -> str:
        """Render a compact code skeleton for a symbol."""
        ntype = node.get("node_type", "")
        name = node.get("name", "")
        path = node.get("path", "")
        doc = node.get("docstring") or ""
        first_doc_line = doc.strip().split("\n")[0] if doc else ""

        if ntype == "class":
            return f"# {path}\nclass {name}:\n    \"\"\"{first_doc_line}\"\"\"\n    ...\n"
        elif ntype in ("function", "method"):
            return f"# {path}\ndef {name}(...):\n    \"\"\"{first_doc_line}\"\"\"\n    ...\n"
        else:
            return f"# {path} ({ntype}: {name})\n"

    def compile_budgeted_query(
        self,
        query: str,
        budget_tokens: int = 1500,
        strategy: str = "hybrid"
    ) -> BudgetedContextPack:
        """Compile context within budget using specified ranking strategy."""
        # 1. Candidate selection via search or direct symbol resolution
        candidates: List[Dict[str, Any]] = []

        direct = resolve_node(self.store, query)
        if direct:
            candidates.append(direct)
            # Add 1-hop neighbors
            neighbors = self.store.get_neighbors(direct["id"], direction="both")
            candidates.extend(neighbors)

        # Lexical/FTS5 search
        fts_matches = self.store.query_fts(query, limit=15)
        matched_ids = {m["id"] for m in fts_matches}
        for m in fts_matches:
            if not any(c["id"] == m["id"] for c in candidates):
                candidates.append(m)

        if not candidates:
            # Fallback to top nodes in graph
            candidates = self.store.get_all_nodes()[:15]

        # 2. Score candidates based on strategy
        pagerank_scores = self._compute_pagerank() if strategy in ("pagerank", "hybrid") else {}

        def score_node(n: Dict[str, Any]) -> float:
            nid = n["id"]
            pr = pagerank_scores.get(nid, 0.0) * 100.0
            fts_bonus = 5.0 if nid in matched_ids else 0.0
            type_bonus = 2.0 if n.get("node_type") in ("class", "function") else 0.0
            return pr + fts_bonus + type_bonus

        candidates.sort(key=score_node, reverse=True)

        # 3. Assemble skeletons under token budget
        header = f"# 🧭 Agtoosa2 Topology Context Pack for Query: '{query}'\n# Strategy: {strategy} | Token Budget: {budget_tokens}\n\n"
        accumulated_text = header
        tokens_used = self._estimate_tokens(accumulated_text)
        nodes_included = 0

        for n in candidates:
            skeleton = self._render_skeleton(n)
            skel_tokens = self._estimate_tokens(skeleton)

            if tokens_used + skel_tokens > budget_tokens:
                break

            accumulated_text += skeleton + "\n"
            tokens_used += skel_tokens
            nodes_included += 1

        return BudgetedContextPack(
            query=query,
            budget_tokens=budget_tokens,
            tokens_used=tokens_used,
            strategy=strategy,
            nodes_included=nodes_included,
            content=accumulated_text
        )


class SkillInstaller:
    """Installs universal agent skills for Claude Code, Antigravity, and Cursor."""

    CLAUDE_SKILL_TEMPLATE = """---
name: agtoosa
description: Unified Graph-Native Engineering Operating System for codebase navigation, semantic search, and architecture verification.
---

# Agtoosa2 Universal Agent Skill

Use this skill whenever you need to explore code symbols, trace dependencies, verify architecture drift, or generate living C4 architecture wikis.

## Available Commands & CLI Recipes:
- **Topology Search**: `agtoosa query "<question>" --budget 1500`
- **Living C4 Architecture Wiki**: `agtoosa wiki build`
- **Architecture Coupling Metrics**: `agtoosa wiki metrics`
- **Socratic Architecture Audit**: `agtoosa audit`
- **Visual-to-AST Drift Check**: `agtoosa graph drift visual`
- **Autonomous Cycle Decoupling**: `agtoosa refactor decouple`
- **Multimodal Diagram Ingestion**: `agtoosa ingest <path_or_url>`
"""

    CURSOR_RULE_TEMPLATE = """---
description: Agtoosa2 Graph-Native Codebase Rule
globs: *
---

Always use Agtoosa2 to query symbol topology and verify architectural invariants before modifying critical classes or core subsystems.
- Run `agtoosa query "<symbol>" --budget 1000` to inspect interface skeletons.
- Run `agtoosa audit` to review God nodes and dependency cycles.
"""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = (workspace_root or Path.cwd()).resolve()

    def install(self, target: str = "all", custom_path: Optional[Path] = None) -> Dict[str, List[str]]:
        """Install skill bundles to specified agent hosts."""
        installed_files: List[str] = []

        if target in ("all", "claude"):
            claude_dir = self.workspace_root / ".claude" / "skills" / "agtoosa"
            claude_dir.mkdir(parents=True, exist_ok=True)
            skill_file = claude_dir / "SKILL.md"
            skill_file.write_text(self.CLAUDE_SKILL_TEMPLATE, encoding="utf-8")
            installed_files.append(str(skill_file))

        if target in ("all", "antigravity", "gemini"):
            agent_dir = self.workspace_root / ".agents" / "skills" / "agtoosa"
            agent_dir.mkdir(parents=True, exist_ok=True)
            skill_file = agent_dir / "SKILL.md"
            skill_file.write_text(self.CLAUDE_SKILL_TEMPLATE, encoding="utf-8")
            installed_files.append(str(skill_file))

        if target in ("all", "cursor"):
            cursor_dir = self.workspace_root / ".cursor" / "rules"
            cursor_dir.mkdir(parents=True, exist_ok=True)
            rule_file = cursor_dir / "agtoosa.mdc"
            rule_file.write_text(self.CURSOR_RULE_TEMPLATE, encoding="utf-8")
            installed_files.append(str(rule_file))

        if custom_path:
            custom_path.parent.mkdir(parents=True, exist_ok=True)
            custom_path.write_text(self.CLAUDE_SKILL_TEMPLATE, encoding="utf-8")
            installed_files.append(str(custom_path))

        return {
            "target": target,
            "installed_files": installed_files
        }
