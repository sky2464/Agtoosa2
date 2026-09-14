"""Autonomous Architecture Refactoring Engine Subsystem."""


def __getattr__(name: str):
    if name in ("CycleDecouplerEngine", "DecouplingStrategy", "DecouplingReport"):
        from agtoosa.refactor.decoupler import CycleDecouplerEngine, DecouplingStrategy, DecouplingReport
        return locals()[name]
    elif name in ("DeadCodePruner", "ZombieSymbol", "DeadCodeReport"):
        from agtoosa.refactor.dead_code import DeadCodePruner, ZombieSymbol, DeadCodeReport
        return locals()[name]
    elif name in ("RefactorEngine", "PatchPlan", "PatchAction"):
        from agtoosa.refactor.engine import RefactorEngine, PatchPlan, PatchAction
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CycleDecouplerEngine", "DecouplingStrategy", "DecouplingReport",
    "DeadCodePruner", "ZombieSymbol", "DeadCodeReport",
    "RefactorEngine", "PatchPlan", "PatchAction",
]

