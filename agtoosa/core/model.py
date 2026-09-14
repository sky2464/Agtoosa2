"""Core domain models for Agtoosa2 Knowledge Graph."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class NodeType(str, Enum):
    # Implementation Layer
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    VARIABLE = "variable"
    IMPORT = "import"

    # Runtime Framework & Data Layer
    ENDPOINT = "endpoint"
    TABLE = "table"
    TOPIC = "topic"
    SERVICE = "service"

    # Specification & Delivery Layer
    EPIC = "epic"
    STORY = "story"
    CRITERION = "criterion"
    TASK = "task"

    # Verification & Evidence Layer
    TEST = "test"
    EVIDENCE = "evidence"

    # Knowledge Layer
    ADR = "adr"
    DOC = "doc"
    CONCEPT = "concept"


class EdgeType(str, Enum):
    CONTAINS = "contains"
    CALLS = "calls"
    IMPORTS = "imports"
    DEFINES = "defines"
    INHERITS = "inherits"
    IMPLEMENTS = "implements"
    VERIFIES = "verifies"
    EVIDENCED_BY = "evidenced_by"
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"

    # Runtime Framework & Semantic Edges
    ROUTES_TO = "routes_to"
    INJECTS = "injects"
    MAPS_TO = "maps_to"
    PUBLISHES = "publishes"
    SUBSCRIBES = "subscribes"
    NETWORK_CALLS = "network_calls"



@dataclass
class Node:
    id: str
    name: str
    node_type: NodeType
    path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    docstring: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["node_type"] = self.node_type.value
        return d


@dataclass
class Edge:
    source_id: str
    target_id: str
    edge_type: EdgeType
    provenance: str = "extracted"  # extracted, inferred, manual
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["edge_type"] = self.edge_type.value
        return d


@dataclass
class GraphStats:
    total_nodes: int = 0
    total_edges: int = 0
    node_counts_by_type: Dict[str, int] = field(default_factory=dict)
    edge_counts_by_type: Dict[str, int] = field(default_factory=dict)
    files_indexed: int = 0
    last_indexed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceClass(str, Enum):
    EXTRACTED = "extracted"
    INFERRED = "inferred"
    MANUAL = "manual"


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


@dataclass
class Citation:
    path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    content_hash: Optional[str] = None
    snapshot_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContractEnvelope:
    contract_version: str = "1.0.0"
    snapshot_id: Optional[str] = None
    freshness: str = "fresh"  # fresh, stale, unknown
    completeness: str = "complete"  # complete, partial, empty
    resolution_status: ResolutionStatus = ResolutionStatus.RESOLVED
    data: Any = None
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    diagnostics: List[str] = field(default_factory=list)
    coverage_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "snapshot_id": self.snapshot_id,
            "freshness": self.freshness,
            "completeness": self.completeness,
            "resolution_status": self.resolution_status.value if hasattr(self.resolution_status, "value") else str(self.resolution_status),
            "data": self.data,
            "candidates": self.candidates,
            "citations": [c.to_dict() if hasattr(c, "to_dict") else c for c in self.citations],
            "diagnostics": self.diagnostics,
            "coverage_summary": self.coverage_summary,
        }

