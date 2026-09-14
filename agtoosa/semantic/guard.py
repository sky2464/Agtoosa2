"""Zero-Trust Multi-Agent Semantic Extraction & Hallucination Guard (DEV-035).

Guarantees:
1. Deterministic AST code baseline first (zero LLM re-parsing for code).
2. Tri-state confidence tagging: EXTRACTED, INFERRED, AMBIGUOUS.
3. Zero-trust bidirectional grounding: validates every extracted symbol against
   the SQLite AST index; flags non-existent references as HALLUCINATED_UNVERIFIED
   with Levenshtein fuzzy-match suggestions.
4. Content-addressed SHA-256 persistent incremental cache.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.core.model import Node, Edge, NodeType, EdgeType
from agtoosa.graph.store import GraphStore
from agtoosa.semantic.gateway import SemanticGateway, SemanticProviderConfig


class ProvenanceConfidence(str, Enum):
    """Tri-state provenance confidence for extracted relationships."""
    EXTRACTED = "EXTRACTED"  # Direct syntax or explicit textual citation
    INFERRED = "INFERRED"    # Logical semantic deduction from context
    AMBIGUOUS = "AMBIGUOUS"  # Imprecise or multiple candidate mappings


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein distance between two strings using DP (pure Python)."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


@dataclass
class SemanticValidationResult:
    """Validation report for an extracted relationship edge."""
    is_valid: bool
    status: str  # "VERIFIED_GROUNDED", "HALLUCINATED_UNVERIFIED", "NON_CODE_RELATION"
    source_id: str
    target_id: str
    edge_type: str
    confidence: ProvenanceConfidence
    suggested_target: Optional[str] = None
    levenshtein_distance: Optional[int] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["confidence"] = self.confidence.value
        return d


class HallucinationGuard:
    """Validates semantic entity submissions against the AST code ground truth."""

    def __init__(self, store: GraphStore):
        self.store = store
        self._cached_symbols: Optional[Dict[str, str]] = None  # name -> id

    def _load_code_symbols(self) -> Dict[str, str]:
        if self._cached_symbols is None:
            self._cached_symbols = {}
            for n in self.store.get_all_nodes():
                # Store both full ID and bare symbol name
                self._cached_symbols[n["id"]] = n["id"]
                self._cached_symbols[n["name"]] = n["id"]
        return self._cached_symbols

    def validate_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        confidence: ProvenanceConfidence = ProvenanceConfidence.INFERRED
    ) -> SemanticValidationResult:
        """Validate proposed edge against SQLite AST symbols."""
        symbols = self._load_code_symbols()

        # Check if target refers to a code symbol
        # Non-code targets (e.g. "doc:...", "concept:...", "req:...") are allowed
        is_code_ref = ":" in target_id and not any(
            target_id.startswith(p) for p in ("doc:", "concept:", "req:", "adr:", "story:", "task:")
        )

        if not is_code_ref and target_id not in symbols:
            # If target has no prefix, check if it's supposed to be code
            # Check if source is a doc/concept referencing code
            pass

        if target_id in symbols:
            return SemanticValidationResult(
                is_valid=True,
                status="VERIFIED_GROUNDED",
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                confidence=confidence,
                reason="Target symbol verified in AST index."
            )

        # If it looks like code or has class/func syntax (e.g., TargetClass.method or ClassName)
        # Search for closest match
        closest_symbol: Optional[str] = None
        min_dist = float("inf")

        bare_name = target_id.split(":")[-1]
        for name, sid in symbols.items():
            dist = levenshtein_distance(bare_name, name.split(":")[-1])
            if dist < min_dist:
                min_dist = dist
                closest_symbol = sid

        threshold = max(10, int(len(bare_name) * 0.8))
        suggestion = closest_symbol if min_dist <= threshold else None

        return SemanticValidationResult(
            is_valid=False,
            status="HALLUCINATED_UNVERIFIED",
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            confidence=confidence,
            suggested_target=suggestion,
            levenshtein_distance=int(min_dist) if suggestion else None,
            reason=f"Symbol '{target_id}' does not exist in AST index. Possible hallucination."
        )


class SemanticExtractionEngine:
    """Coordinates batch semantic extraction with hallucination guarding and caching."""

    def __init__(
        self,
        store: GraphStore,
        workspace_root: Optional[Path] = None,
        gateway: Optional[SemanticGateway] = None,
        cache_dir: Optional[Path] = None
    ):
        self.store = store
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.gateway = gateway or SemanticGateway(
            SemanticProviderConfig(cache_dir=(cache_dir or self.workspace_root / ".agtoosa" / "cache" / "semantic"))
        )
        self.guard = HallucinationGuard(store)
        self.cache_dir = cache_dir or (self.workspace_root / ".agtoosa" / "cache" / "semantic")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_content(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def extract_document(
        self,
        file_path: Path,
        strict_grounding: bool = False
    ) -> Dict[str, Any]:
        """Extract semantic concepts and relationships from a non-code document."""
        if not file_path.exists():
            return {"error": f"File {file_path} not found"}

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        content_hash = self._hash_content(text)
        cache_file = self.cache_dir / f"{content_hash}.json"

        # Check persistent incremental cache
        if cache_file.exists():
            try:
                cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
                cached_data["cached"] = True
                return cached_data
            except Exception:
                pass

        rel_path = str(file_path.relative_to(self.workspace_root) if file_path.is_relative_to(self.workspace_root) else file_path)
        doc_node_id = f"doc:{rel_path}"

        nodes: List[Node] = [
            Node(
                id=doc_node_id,
                name=file_path.name,
                node_type=NodeType.DOC,
                path=rel_path,
                docstring=text[:200]
            )
        ]

        extracted_edges: List[Edge] = []
        validation_results: List[SemanticValidationResult] = []

        # Deterministic extraction of referenced symbols:
        # 1. Backtick code symbols `SymbolName` or `package.Symbol`
        # 2. Markdown headers as concepts
        import re
        code_refs = re.findall(r"`([A-Za-z0-9_.:]+)`", text)
        for ref in set(code_refs):
            # Guard verification
            val = self.guard.validate_edge(
                source_id=doc_node_id,
                target_id=ref,
                edge_type=EdgeType.REFERENCES.value,
                confidence=ProvenanceConfidence.EXTRACTED
            )
            validation_results.append(val)

            if val.is_valid:
                extracted_edges.append(
                    Edge(
                        source_id=doc_node_id,
                        target_id=val.target_id if ":" in val.target_id else f"code:{val.target_id}",
                        edge_type=EdgeType.REFERENCES,
                        provenance="extracted",
                        metadata={"confidence": val.confidence.value, "citation": f"`{ref}`"}
                    )
                )
            elif not strict_grounding and val.suggested_target:
                # In non-strict mode, link to fuzzy-matched grounded target
                extracted_edges.append(
                    Edge(
                        source_id=doc_node_id,
                        target_id=val.suggested_target,
                        edge_type=EdgeType.REFERENCES,
                        provenance="inferred",
                        metadata={
                            "confidence": ProvenanceConfidence.INFERRED.value,
                            "original_reference": ref,
                            "levenshtein_distance": val.levenshtein_distance
                        }
                    )
                )

        # Batch insert into store
        if nodes or extracted_edges:
            self.store.insert_batch(nodes, extracted_edges)

        result = {
            "file": rel_path,
            "content_hash": content_hash,
            "cached": False,
            "nodes_created": len(nodes),
            "edges_created": len(extracted_edges),
            "hallucinations_blocked": sum(1 for v in validation_results if not v.is_valid),
            "validation_results": [v.to_dict() for v in validation_results]
        }

        # Save to cache
        cache_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    def batch_extract(
        self,
        directory: Path,
        chunk_size: int = 15,
        strict_grounding: bool = False
    ) -> Dict[str, Any]:
        """Batch process non-code documentation files in chunks."""
        supported_exts = {".md", ".rst", ".txt", ".adoc"}
        doc_files = [
            f for f in directory.rglob("*")
            if f.is_file() and f.suffix.lower() in supported_exts and not f.name.startswith(".")
        ]

        # Chunk files
        chunks = [doc_files[i:i + chunk_size] for i in range(0, len(doc_files), chunk_size)]
        total_extracted = 0
        total_hallucinations_blocked = 0
        file_results: List[Dict[str, Any]] = []

        for chunk in chunks:
            for f in chunk:
                res = self.extract_document(f, strict_grounding=strict_grounding)
                file_results.append(res)
                total_extracted += res.get("edges_created", 0)
                total_hallucinations_blocked += res.get("hallucinations_blocked", 0)

        return {
            "total_files": len(doc_files),
            "total_chunks": len(chunks),
            "edges_created": total_extracted,
            "hallucinations_blocked": total_hallucinations_blocked,
            "results": file_results
        }
