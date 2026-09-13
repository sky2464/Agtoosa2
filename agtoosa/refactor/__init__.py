"""Autonomous Architecture Refactoring Engine Subsystem."""

from agtoosa.refactor.decoupler import CycleDecouplerEngine, DecouplingStrategy, DecouplingReport
from agtoosa.refactor.dead_code import DeadCodePruner, ZombieSymbol, DeadCodeReport
from agtoosa.refactor.engine import RefactorEngine, PatchPlan, PatchAction

__all__ = [
    "CycleDecouplerEngine", "DecouplingStrategy", "DecouplingReport",
    "DeadCodePruner", "ZombieSymbol", "DeadCodeReport",
    "RefactorEngine", "PatchPlan", "PatchAction",
]
