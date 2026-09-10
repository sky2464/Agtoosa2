"""Automated Cycle Decoupling Engine (DEV-019 / Stage 19).

Analyzes architectural cycles detected by Tarjan's algorithm, identifies the optimal
decoupling point (weakest link or interface boundary), and generates concrete
architectural refactoring blueprints:
- Dependency Inversion (Interface / Protocol extraction)
- Shared Kernel Extraction (moving mutually referenced symbols to shared module)
- Event / Observer decoupling
"""

from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.graph.store import GraphStore
from agtoosa.graph.metrics import MetricsEngine


@dataclass
class DecouplingStrategy:
    strategy_type: str  # "DEPENDENCY_INVERSION", "SHARED_KERNEL", "EVENT_DRIVEN"
    cycle: List[str]  # Cycle node sequence
    cut_edge: Tuple[str, str]  # (source_id, target_id) to be decoupled
    rationale: str
    proposed_interface_name: str
    generated_code_stub: str
    refactor_steps: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DecouplingReport:
    total_cycles_detected: int
    strategies: List[DecouplingStrategy] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cycles_detected": self.total_cycles_detected,
            "strategies": [s.to_dict() for s in self.strategies]
        }


class CycleDecouplerEngine:
    """Detects cycles and generates automated refactoring blueprints to restore DAG acyclicity."""

    def __init__(self, store: GraphStore, workspace_root: Optional[Path] = None):
        self.store = store
        self.workspace_root = workspace_root or Path.cwd()
        self.metrics_engine = MetricsEngine(store)

    def analyze_cycles(self) -> DecouplingReport:
        """Find all cyclic dependency loops and formulate decoupling strategies."""
        metrics = self.metrics_engine.compute_all()
        raw_cycles = metrics.get("cycles", [])

        strategies: List[DecouplingStrategy] = []

        for cycle in raw_cycles:
            if len(cycle) < 2:
                continue

            strat = self._formulate_strategy(cycle)
            if strat:
                strategies.append(strat)

        return DecouplingReport(
            total_cycles_detected=len(raw_cycles),
            strategies=strategies
        )

    def _formulate_strategy(self, cycle: List[Any]) -> DecouplingStrategy:
        """Analyze a specific cycle and select the optimal decoupling technique."""
        cycle_nodes: List[Dict[str, Any]] = []
        cycle_ids: List[str] = []

        for item in cycle:
            if isinstance(item, dict):
                cycle_nodes.append(item)
                cycle_ids.append(item.get("id", ""))
            else:
                nid = str(item)
                cycle_ids.append(nid)
                n = self.store.get_node(nid) or {"id": nid, "name": nid, "path": ""}
                cycle_nodes.append(n)

        # Determine cut edge (inspect the last edge back to start: source -> target)
        src_node = cycle_nodes[-1]
        tgt_node = cycle_nodes[0]
        src_id = cycle_ids[-1]
        tgt_id = cycle_ids[0]

        src_name = src_node.get("name", "SourceModule")
        tgt_name = tgt_node.get("name", "TargetModule")

        # Select strategy based on entity types
        has_model = any("model" in n.get("path", "").lower() or "entity" in n.get("path", "").lower() or "schema" in n.get("path", "").lower() for n in cycle_nodes)
        has_event = any("listener" in n.get("name", "").lower() or "event" in n.get("name", "").lower() or "notify" in n.get("name", "").lower() for n in cycle_nodes)

        interface_name = f"I{tgt_name.capitalize()}Protocol"

        if has_model:
            strat_type = "SHARED_KERNEL"
            model_node = next((n for n in cycle_nodes if "model" in n.get("path", "").lower()), tgt_node)
            model_name = model_node.get("name", "SharedEntity")
            rationale = (
                f"Extract shared data structures from '{model_name}' ({model_node.get('path')}) into a common kernel "
                f"so circular imports between '{src_name}' and '{tgt_name}' are eliminated."
            )
            code_stub = (
                f"# Proposed Shared Kernel extraction (e.g. shared_types.py):\n"
                f"from dataclasses import dataclass\n\n"
                f"@dataclass\n"
                f"class {model_name}State:\n"
                f"    id: str\n"
                f"    status: str\n"
            )
            steps = [
                f"1. Move shared types from {model_node.get('path')} to a new or existing shared kernel module.",
                f"2. Update {src_node.get('path')} and {tgt_node.get('path')} to import from the shared kernel.",
                f"3. Remove direct circular dependency between {src_name} and {tgt_name}."
            ]
        elif has_event:
            strat_type = "EVENT_DRIVEN"
            rationale = (
                f"Replace direct invocation from '{src_name}' to '{tgt_name}' with an "
                f"event publisher / subscriber notification to decouple execution flow."
            )
            code_stub = (
                f"# Event-driven decoupling pattern:\n"
                f"class {tgt_name}EventPublisher:\n"
                f"    def __init__(self):\n"
                f"        self._handlers = []\n\n"
                f"    def subscribe(self, handler):\n"
                f"        self._handlers.append(handler)\n"
            )
            steps = [
                f"1. Publish an event from {src_node.get('path')} instead of invoking {tgt_name} directly.",
                f"2. Subscribe {tgt_name} to the event dispatcher during startup.",
                f"3. Remove synchronous call edge between {src_name} and {tgt_name}."
            ]
        else:
            strat_type = "DEPENDENCY_INVERSION"
            rationale = (
                f"Introduce an abstract interface '{interface_name}' in '{src_node.get('path')}' "
                f"and inject '{tgt_name}' as an implementation at runtime (DIP)."
            )
            code_stub = (
                f"# Dependency Inversion Principle (DIP) stub in {src_node.get('path')}:\n"
                f"from typing import Protocol\n\n"
                f"class {interface_name}(Protocol):\n"
                f"    def execute(self, *args, **kwargs) -> Any:\n"
                f"        ...\n\n"
                f"# In {src_name} constructor / function:\n"
                f"def __init__(self, delegate: {interface_name}):\n"
                f"    self.delegate = delegate\n"
            )
            steps = [
                f"1. Define Protocol/interface '{interface_name}' in {src_node.get('path')}.",
                f"2. Have {src_name} call through self.delegate instead of importing {tgt_name}.",
                f"3. Inject concrete {tgt_name} instance from higher-level composition root (e.g. main/cli)."
            ]

        cycle_names = [n.get("name", n.get("id", "")) for n in cycle_nodes]

        return DecouplingStrategy(
            strategy_type=strat_type,
            cycle=cycle_names,
            cut_edge=(src_id, tgt_id),
            rationale=rationale,
            proposed_interface_name=interface_name,
            generated_code_stub=code_stub,
            refactor_steps=steps
        )
