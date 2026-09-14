"""Parser capability registry, dialect inventory, and standardized ParseResult (DEV-040).

Addresses R-01 by explicitly inventorying recognized file extensions, dialects,
active extraction backends (standard-library AST vs regex fallback vs tree-sitter),
and extracted node/edge relationship types.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any


class ParserBackend(str, Enum):
    PYTHON_AST = "python_ast"
    REGEX_FALLBACK = "regex_fallback"
    TREE_SITTER = "tree_sitter"
    MARKDOWN_PROSE = "markdown_prose"
    SPECIALIZED = "specialized"


class CoverageTier(str, Enum):
    FULL_AST = "full_ast"
    LIMITED_FALLBACK = "limited_fallback"
    GRAMMAR_BACKED = "grammar_backed"
    PLANNED = "planned"


@dataclass
class UnboundReference:
    """A syntactically observed symbol reference before resolution (DEV-040/041)."""
    caller_id: str
    target_name: str
    relation: str  # e.g., "calls", "imports", "inherits", "publishes", "subscribes"
    file_path: str
    line: int
    column: int = 0
    context_scope: Optional[str] = None


@dataclass
class ParseDiagnostic:
    """A warning, syntax defect, or unsupported construct noted during parsing."""
    file_path: str
    line: int
    severity: str  # "warning", "info", "error"
    message: str
    code: str  # e.g. "REGEX_LIMITATION", "UNSUPPORTED_DYNAMIC", "SYNTAX_ERROR"


@dataclass
class ParseResult:
    """Common envelope produced by language parser adapters."""
    nodes: List[Any] = field(default_factory=list)
    edges: List[Any] = field(default_factory=list)
    unbound_references: List[UnboundReference] = field(default_factory=list)
    diagnostics: List[ParseDiagnostic] = field(default_factory=list)
    parser_name: str = ""
    parser_version: str = "1.0.0"
    backend: ParserBackend = ParserBackend.REGEX_FALLBACK
    coverage_tier: CoverageTier = CoverageTier.LIMITED_FALLBACK
    source_hash: str = ""


@dataclass
class LanguageCapability:
    """Explicit capability declaration for a language or schema family."""
    family_id: str
    display_name: str
    file_extensions: List[str]
    active_backend: ParserBackend
    coverage_tier: CoverageTier
    extracted_node_types: List[str]
    extracted_edge_types: List[str]
    supports_nested_functions: bool
    supports_type_signatures: bool
    supports_rationale_markers: bool  # WHY:, NOTE:, HACK: (DEV-047)
    limitations: List[str] = field(default_factory=list)


class ParserCapabilityRegistry:
    """Central registry tracking parser capability across all supported languages."""

    def __init__(self):
        self._capabilities: Dict[str, LanguageCapability] = {}
        self._extension_map: Dict[str, str] = {}
        self._register_defaults()

    def _register_defaults(self):
        # 1. Python
        self.register(LanguageCapability(
            family_id="python",
            display_name="Python",
            file_extensions=[".py", ".pyw"],
            active_backend=ParserBackend.PYTHON_AST,
            coverage_tier=CoverageTier.FULL_AST,
            extracted_node_types=["module", "class", "function", "endpoint", "topic"],
            extracted_edge_types=["defines", "calls", "imports", "inherits", "publishes", "subscribes"],
            supports_nested_functions=True,
            supports_type_signatures=True,
            supports_rationale_markers=True,
            limitations=["Dynamic eval/exec and runtime monkeypatching not resolvable statically"]
        ))

        # 2. JavaScript / TypeScript
        self.register(LanguageCapability(
            family_id="javascript_typescript",
            display_name="JavaScript / TypeScript",
            file_extensions=[".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"],
            active_backend=ParserBackend.REGEX_FALLBACK,
            coverage_tier=CoverageTier.LIMITED_FALLBACK,
            extracted_node_types=["module", "class", "function", "endpoint", "topic"],
            extracted_edge_types=["defines", "calls", "imports", "publishes", "subscribes"],
            supports_nested_functions=False,
            supports_type_signatures=False,
            supports_rationale_markers=False,
            limitations=["Regex parsing misses arrow functions inside complex callbacks and nested scopes"]
        ))

        # 3. Shell
        self.register(LanguageCapability(
            family_id="shell",
            display_name="Shell (Bash/Sh/Zsh)",
            file_extensions=[".sh", ".bash", ".zsh"],
            active_backend=ParserBackend.REGEX_FALLBACK,
            coverage_tier=CoverageTier.LIMITED_FALLBACK,
            extracted_node_types=["file", "function"],
            extracted_edge_types=["defines", "calls", "imports"],
            supports_nested_functions=False,
            supports_type_signatures=False,
            supports_rationale_markers=False,
            limitations=["Dynamic variable expansion in source paths ($DIR/lib.sh) not resolved"]
        ))

        # 4. Go
        self.register(LanguageCapability(
            family_id="go",
            display_name="Go",
            file_extensions=[".go"],
            active_backend=ParserBackend.REGEX_FALLBACK,
            coverage_tier=CoverageTier.LIMITED_FALLBACK,
            extracted_node_types=["file", "class", "function"],
            extracted_edge_types=["defines", "calls", "imports"],
            supports_nested_functions=False,
            supports_type_signatures=True,
            supports_rationale_markers=False,
            limitations=["Receiver methods extracted via regex; interface satisfaction not computed"]
        ))

        # 5. Rust
        self.register(LanguageCapability(
            family_id="rust",
            display_name="Rust",
            file_extensions=[".rs"],
            active_backend=ParserBackend.REGEX_FALLBACK,
            coverage_tier=CoverageTier.LIMITED_FALLBACK,
            extracted_node_types=["file", "class", "function"],
            extracted_edge_types=["defines", "calls", "imports"],
            supports_nested_functions=False,
            supports_type_signatures=True,
            supports_rationale_markers=False,
            limitations=["Macro-generated functions and trait impl blocks partially resolved"]
        ))

        # 6. Java & Kotlin
        self.register(LanguageCapability(
            family_id="jvm",
            display_name="Java & Kotlin",
            file_extensions=[".java", ".kt", ".kts"],
            active_backend=ParserBackend.REGEX_FALLBACK,
            coverage_tier=CoverageTier.LIMITED_FALLBACK,
            extracted_node_types=["file", "class", "function"],
            extracted_edge_types=["defines", "calls", "imports"],
            supports_nested_functions=False,
            supports_type_signatures=True,
            supports_rationale_markers=False,
            limitations=["Overloaded methods share identical name node; reflection calls invisible"]
        ))

        # 7. C / C++
        self.register(LanguageCapability(
            family_id="cpp",
            display_name="C / C++",
            file_extensions=[".c", ".h", ".cpp", ".hpp", ".cc", ".cxx"],
            active_backend=ParserBackend.REGEX_FALLBACK,
            coverage_tier=CoverageTier.LIMITED_FALLBACK,
            extracted_node_types=["file", "class", "function"],
            extracted_edge_types=["defines", "calls", "imports"],
            supports_nested_functions=False,
            supports_type_signatures=True,
            supports_rationale_markers=False,
            limitations=["Pre-processor macros, template specializations, and include path resolution unverified"]
        ))

        # 8. C#
        self.register(LanguageCapability(
            family_id="csharp",
            display_name="C#",
            file_extensions=[".cs"],
            active_backend=ParserBackend.REGEX_FALLBACK,
            coverage_tier=CoverageTier.LIMITED_FALLBACK,
            extracted_node_types=["file", "class", "function"],
            extracted_edge_types=["defines", "calls", "imports"],
            supports_nested_functions=False,
            supports_type_signatures=True,
            supports_rationale_markers=False,
            limitations=["Namespace using aliases and partial classes not unified"]
        ))

        # 9. SQL DDL
        self.register(LanguageCapability(
            family_id="sql",
            display_name="SQL DDL",
            file_extensions=[".sql"],
            active_backend=ParserBackend.REGEX_FALLBACK,
            coverage_tier=CoverageTier.LIMITED_FALLBACK,
            extracted_node_types=["file", "class"],
            extracted_edge_types=["defines", "references"],
            supports_nested_functions=False,
            supports_type_signatures=False,
            supports_rationale_markers=False,
            limitations=["CREATE TABLE / VIEW supported; complex dialect-specific triggers unindexed"]
        ))

        # 10. Dockerfile
        self.register(LanguageCapability(
            family_id="dockerfile",
            display_name="Dockerfile",
            file_extensions=["Dockerfile", ".dockerfile"],
            active_backend=ParserBackend.REGEX_FALLBACK,
            coverage_tier=CoverageTier.LIMITED_FALLBACK,
            extracted_node_types=["file", "class"],
            extracted_edge_types=["defines", "references"],
            supports_nested_functions=False,
            supports_type_signatures=False,
            supports_rationale_markers=False,
            limitations=["Multi-stage FROM/COPY relationships extracted; ARG expansion uncomputed"]
        ))

        # 11. Prisma ORM
        self.register(LanguageCapability(
            family_id="prisma",
            display_name="Prisma Schema",
            file_extensions=[".prisma"],
            active_backend=ParserBackend.SPECIALIZED,
            coverage_tier=CoverageTier.LIMITED_FALLBACK,
            extracted_node_types=["file", "class"],
            extracted_edge_types=["defines", "references"],
            supports_nested_functions=False,
            supports_type_signatures=True,
            supports_rationale_markers=False,
            limitations=["Extracts models, enums, @relation fields; client generator unindexed"]
        ))

        # 12. Markdown Documentation
        self.register(LanguageCapability(
            family_id="markdown",
            display_name="Markdown Specs & Docs",
            file_extensions=[".md", ".markdown"],
            active_backend=ParserBackend.MARKDOWN_PROSE,
            coverage_tier=CoverageTier.SPECIALIZED if hasattr(CoverageTier, 'SPECIALIZED') else CoverageTier.FULL_AST,
            extracted_node_types=["document", "story", "criterion", "task"],
            extracted_edge_types=["implements", "verifies", "evidenced_by", "references"],
            supports_nested_functions=False,
            supports_type_signatures=False,
            supports_rationale_markers=True,
            limitations=["General prose unindexed; specifically parses EARS criteria, story tags, task lists"]
        ))

    def register(self, cap: LanguageCapability):
        self._capabilities[cap.family_id] = cap
        for ext in cap.file_extensions:
            self._extension_map[ext.lower()] = cap.family_id

    def get_capability(self, family_id: str) -> Optional[LanguageCapability]:
        return self._capabilities.get(family_id)

    def find_capability_for_file(self, file_path: Path) -> Optional[LanguageCapability]:
        name = file_path.name.lower()
        # Direct file name match (e.g. Dockerfile)
        if name in self._extension_map:
            return self._capabilities[self._extension_map[name]]
        suffix = file_path.suffix.lower()
        if suffix in self._extension_map:
            return self._capabilities[self._extension_map[suffix]]
        return None

    def list_all(self) -> List[LanguageCapability]:
        return list(self._capabilities.values())

    def get_summary(self) -> Dict[str, Any]:
        """Generate human and machine-readable capability audit."""
        tier_counts = {}
        for cap in self._capabilities.values():
            tier = cap.coverage_tier.value
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        return {
            "total_families": len(self._capabilities),
            "tier_distribution": tier_counts,
            "families": {
                fid: {
                    "display_name": cap.display_name,
                    "extensions": cap.file_extensions,
                    "backend": cap.active_backend.value,
                    "tier": cap.coverage_tier.value,
                    "supports_nested": cap.supports_nested_functions,
                    "supports_rationale": cap.supports_rationale_markers,
                    "limitations_count": len(cap.limitations)
                }
                for fid, cap in self._capabilities.items()
            }
        }


# Global singleton
CAPABILITY_REGISTRY = ParserCapabilityRegistry()
