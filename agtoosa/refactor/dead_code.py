"""Dead Code & Zombie Symbol Pruning Engine (DEV-020 / Stage 20).

Identifies zero-caller unreachable AST nodes in the knowledge graph and generates
safe deprecation/deletion refactoring plans:
- Functions, classes, and methods with no incoming call edges (zombie symbols).
- Entrypoint exclusion: skips known entrypoints (main, __init__, CLI handlers, test functions).
- Confidence scoring: low/medium/high based on node type, connectivity, and naming patterns.
- Safe deletion blueprints with step-by-step instructions.
"""

from collections import defaultdict
from dataclasses import dataclass, field, asdict
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.graph.store import GraphStore


# Patterns that indicate a node is a legitimate entrypoint and should NOT be flagged
ENTRYPOINT_PATTERNS = {
    # Python entrypoints and magic methods
    "main", "__main__", "__init__", "__new__", "__del__",
    "__enter__", "__exit__", "__call__", "__repr__", "__str__",
    "__eq__", "__hash__", "__lt__", "__gt__", "__le__", "__ge__",
    "__len__", "__iter__", "__next__", "__getitem__", "__setitem__",
    "__contains__", "__add__", "__sub__", "__mul__",
    # Testing frameworks
    "setUp", "tearDown", "setUpClass", "tearDownClass",
    "setUpModule", "tearDownModule",
    # Common framework hooks
    "on_ready", "on_start", "on_stop", "on_event",
    "handle", "handler", "callback", "middleware",
    "configure", "setup", "teardown",
}

ENTRYPOINT_PREFIXES = ("test_", "Test", "cmd_", "handle_", "on_")
ENTRYPOINT_PATH_PATTERNS = ("test_", "tests/", "conftest", "__main__", "cli/", "migrations/")


@dataclass
class ZombieSymbol:
    """A symbol identified as potentially dead/unreachable code."""
    node_id: str
    name: str
    node_type: str
    path: str
    start_line: int
    end_line: int
    confidence: str  # "low", "medium", "high"
    reason: str
    estimated_lines: int
    safe_to_delete: bool
    deletion_steps: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeadCodeReport:
    """Complete dead code analysis report."""
    total_symbols_analyzed: int
    total_dead_candidates: int
    total_estimated_dead_lines: int
    confidence_breakdown: Dict[str, int]
    zombies: List[ZombieSymbol] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_symbols_analyzed": self.total_symbols_analyzed,
            "total_dead_candidates": self.total_dead_candidates,
            "total_estimated_dead_lines": self.total_estimated_dead_lines,
            "confidence_breakdown": self.confidence_breakdown,
            "zombies": [z.to_dict() for z in self.zombies]
        }


class DeadCodePruner:
    """Identifies zero-caller unreachable AST nodes and generates safe deletion refactors."""

    def __init__(self, store: GraphStore, workspace_root: Optional[Path] = None):
        self.store = store
        self.workspace_root = workspace_root or Path.cwd()

    def analyze(self, min_confidence: str = "low") -> DeadCodeReport:
        """Find all potentially dead symbols in the knowledge graph.

        Args:
            min_confidence: Minimum confidence threshold ("low", "medium", "high").

        Returns:
            DeadCodeReport with identified zombie symbols.
        """
        confidence_levels = {"low": 0, "medium": 1, "high": 2}
        min_level = confidence_levels.get(min_confidence, 0)

        nodes = self.store.get_all_nodes()
        edges = self.store.get_all_edges()

        # Build adjacency maps
        callers_of: Dict[str, Set[str]] = defaultdict(set)
        callees_of: Dict[str, Set[str]] = defaultdict(set)
        contained_by: Dict[str, str] = {}

        for e in edges:
            src = e["source_id"]
            tgt = e["target_id"]
            etype = e.get("edge_type", "")

            if etype == "contains":
                contained_by[tgt] = src
            elif etype in ("calls", "imports", "uses", "verifies", "evidenced_by"):
                callers_of[tgt].add(src)
                callees_of[src].add(tgt)

        # Analyze each code symbol
        code_types = {"function", "class", "method"}
        code_nodes = [n for n in nodes if n.get("node_type", "") in code_types]

        zombies: List[ZombieSymbol] = []

        for node in code_nodes:
            nid = node["id"]
            name = node.get("name", "")
            ntype = node.get("node_type", "")
            path = node.get("path", "")
            start_line = node.get("start_line", 0) or 0
            end_line = node.get("end_line", 0) or 0

            # Skip known entrypoints
            if self._is_entrypoint(name, path, ntype):
                continue

            # Count non-containment incoming edges (actual callers)
            incoming_callers = callers_of.get(nid, set())

            if len(incoming_callers) == 0:
                # Zero callers — potential dead code
                confidence = self._assess_confidence(node, incoming_callers, callees_of, contained_by, nodes)
                conf_level = confidence_levels.get(confidence, 0)

                if conf_level >= min_level:
                    estimated_lines = max(1, end_line - start_line + 1)
                    reason = self._build_reason(node, incoming_callers)
                    safe = confidence in ("medium", "high")
                    steps = self._build_deletion_steps(node, callees_of)

                    zombies.append(ZombieSymbol(
                        node_id=nid,
                        name=name,
                        node_type=ntype,
                        path=path,
                        start_line=start_line,
                        end_line=end_line,
                        confidence=confidence,
                        estimated_lines=estimated_lines,
                        safe_to_delete=safe,
                        reason=reason,
                        deletion_steps=steps,
                    ))

        # Sort by confidence (high first), then by estimated_lines (large first)
        order = {"high": 0, "medium": 1, "low": 2}
        zombies.sort(key=lambda z: (order.get(z.confidence, 3), -z.estimated_lines))

        total_dead_lines = sum(z.estimated_lines for z in zombies)
        breakdown = defaultdict(int)
        for z in zombies:
            breakdown[z.confidence] += 1

        return DeadCodeReport(
            total_symbols_analyzed=len(code_nodes),
            total_dead_candidates=len(zombies),
            total_estimated_dead_lines=total_dead_lines,
            confidence_breakdown=dict(breakdown),
            zombies=zombies,
        )

    def _is_entrypoint(self, name: str, path: str, node_type: str) -> bool:
        """Check if a symbol is a known entrypoint and should be excluded from dead code analysis."""
        # Exact name matches
        if name in ENTRYPOINT_PATTERNS:
            return True

        # Prefix matches
        if any(name.startswith(p) for p in ENTRYPOINT_PREFIXES):
            return True

        # Path-based exclusions (tests, CLI, migrations, etc.)
        path_lower = path.lower().replace("\\", "/")
        if any(pat in path_lower for pat in ENTRYPOINT_PATH_PATTERNS):
            return True

        # Dunder methods
        if name.startswith("__") and name.endswith("__"):
            return True

        # Decorated exports (heuristic: capitalized class names are likely public API)
        if node_type == "class" and name[0:1].isupper():
            # Check if it looks like a public exported class
            if any(kw in name.lower() for kw in ("mixin", "base", "abstract", "interface", "protocol")):
                return True

        return False

    def _assess_confidence(self, node: Dict[str, Any], incoming: Set[str],
                           callees_of: Dict[str, Set[str]], contained_by: Dict[str, str],
                           all_nodes: List[Dict[str, Any]]) -> str:
        """Assess confidence that a symbol is truly dead code.

        Returns: "low", "medium", or "high"
        """
        name = node.get("name", "")
        path = node.get("path", "")
        ntype = node.get("node_type", "")
        nid = node["id"]

        # High confidence: private/internal functions with zero callers
        if name.startswith("_") and not name.startswith("__"):
            return "high"

        # High confidence: helper functions in internal modules
        if "_internal" in path or "_private" in path or "_helpers" in path:
            return "high"

        # Medium confidence: regular functions in non-public modules
        if ntype == "function" and not name[0:1].isupper():
            return "medium"

        # Medium confidence: methods (non-dunder) of classes
        if ntype == "method":
            return "medium"

        # Low confidence: public classes or ambiguous symbols
        return "low"

    def _build_reason(self, node: Dict[str, Any], callers: Set[str]) -> str:
        """Build a human-readable explanation for why this symbol is flagged."""
        name = node.get("name", "")
        ntype = node.get("node_type", "")
        path = node.get("path", "")

        return (
            f"Zero incoming callers detected for {ntype} '{name}' in {path}. "
            f"No function, class, or test in the knowledge graph references this symbol."
        )

    def _build_deletion_steps(self, node: Dict[str, Any], callees_of: Dict[str, Set[str]]) -> List[str]:
        """Generate step-by-step safe deletion instructions."""
        name = node.get("name", "")
        path = node.get("path", "")
        start = node.get("start_line", "?")
        end = node.get("end_line", "?")
        nid = node["id"]

        steps = [
            f"1. Verify '{name}' is not referenced via dynamic dispatch, reflection, or string-based imports.",
            f"2. Search codebase for string references: grep -rn '{name}' --include='*.py'",
            f"3. Remove {node.get('node_type', 'symbol')} '{name}' from {path} (lines {start}-{end}).",
        ]

        # Check if this symbol calls other things that might become orphaned
        outgoing = callees_of.get(nid, set())
        if outgoing:
            steps.append(
                f"4. Review {len(outgoing)} downstream callee(s) — they may also become dead code after removal."
            )

        steps.append(f"{len(steps) + 1}. Run full test suite to verify no regressions.")
        return steps


def format_dead_code_text(report: DeadCodeReport) -> str:
    """Format dead code report for terminal output."""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("🧹 Dead Code & Zombie Symbol Pruning Report")
    lines.append("=" * 60)
    lines.append(f"\n📊 Analysis Summary:")
    lines.append(f"   • Total Symbols Analyzed: {report.total_symbols_analyzed}")
    lines.append(f"   • Dead Code Candidates: {report.total_dead_candidates}")
    lines.append(f"   • Estimated Pruneable Lines: {report.total_estimated_dead_lines}")

    if report.confidence_breakdown:
        lines.append(f"\n   📈 Confidence Breakdown:")
        for level in ("high", "medium", "low"):
            count = report.confidence_breakdown.get(level, 0)
            if count:
                emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(level, "⚪")
                lines.append(f"      {emoji} {level.capitalize()}: {count} symbol(s)")

    if not report.zombies:
        lines.append("\n   ✨ No dead code detected! Codebase is clean.")
        return "\n".join(lines)

    lines.append(f"\n{'─' * 60}")
    lines.append(f"🧟 Zombie Symbols ({len(report.zombies)}):")

    for idx, z in enumerate(report.zombies, start=1):
        conf_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(z.confidence, "⚪")
        safe_label = "✅ Safe to Delete" if z.safe_to_delete else "⚠️  Manual Review"
        lines.append(f"\n   [{idx}] {conf_emoji} {z.node_type.upper()}: {z.name}")
        lines.append(f"       📍 {z.path}:{z.start_line}-{z.end_line} ({z.estimated_lines} lines)")
        lines.append(f"       Confidence: {z.confidence.upper()} | {safe_label}")
        lines.append(f"       Reason: {z.reason}")
        lines.append(f"       Deletion Steps:")
        for step in z.deletion_steps:
            lines.append(f"         {step}")

    lines.append(f"\n{'=' * 60}")
    return "\n".join(lines)
