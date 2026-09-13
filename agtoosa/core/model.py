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
