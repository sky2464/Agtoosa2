"""Autonomous AST Patch Engine (DEV-022 / Stage 22).

Applies safe AST modifications, dead code deletions, and dependency inversion interfaces
to source files with automated unified diff previews, atomic backups, and rollback capabilities.
"""

from dataclasses import dataclass, field, asdict
import datetime
import difflib
import json
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional

from agtoosa.refactor.dead_code import ZombieSymbol
from agtoosa.refactor.decoupler import DecouplingStrategy


@dataclass
class PatchAction:
    """A single atomic file modification action."""
    action_type: str  # "DELETE_SYMBOL", "INSERT_INTERFACE", "CREATE_FILE"
    file_path: str
    symbol_name: str
    start_line: int = 1
    end_line: int = 1
    code_content: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatchAction":
        return cls(**data)


@dataclass
class PatchPlan:
    """A collection of patch actions forming a coherent refactoring changeset."""
    plan_id: str
    description: str
    actions: List[PatchAction] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "description": self.description,
            "actions": [a.to_dict() for a in self.actions],
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatchPlan":
        actions = [PatchAction.from_dict(a) for a in data.get("actions", [])]
        return cls(
            plan_id=data["plan_id"],
            description=data.get("description", ""),
            actions=actions,
            created_at=data.get("created_at", "")
        )


class RefactorEngine:
    """Executes safe code mutations, diff generation, and transactional backups."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.backups_dir = self.workspace_root / ".agtoosa" / "refactor_backups"

    def create_dead_code_plan(
        self,
        zombies: List[ZombieSymbol],
        min_confidence: str = "high"
    ) -> PatchPlan:
        """Formulate a safe dead-code pruning plan from identified zombie symbols."""
        confidence_ranks = {"low": 1, "medium": 2, "high": 3}
        target_rank = confidence_ranks.get(min_confidence.lower(), 3)

        plan_id = f"prune_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        actions: List[PatchAction] = []

        for z in zombies:
            z_rank = confidence_ranks.get(z.confidence.lower(), 1)
            if z.safe_to_delete and z_rank >= target_rank:
                actions.append(
                    PatchAction(
                        action_type="DELETE_SYMBOL",
                        file_path=z.path,
                        symbol_name=z.name,
                        start_line=z.start_line,
                        end_line=z.end_line,
                        reason=f"Dead code removal: {z.reason} ({z.confidence} confidence)"
                    )
                )

        return PatchPlan(
            plan_id=plan_id,
            description=f"Prune {len(actions)} unreachable zombie symbols (confidence >= {min_confidence})",
            actions=actions
        )

    def create_decouple_plan(
        self,
        strategy: DecouplingStrategy,
        target_path: Optional[str] = None
    ) -> PatchPlan:
        """Formulate an interface insertion patch plan from a decoupling strategy."""
        plan_id = f"decouple_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        actions: List[PatchAction] = []

        # If no specific target path is given, generate an interface file
        if not target_path:
            clean_name = strategy.proposed_interface_name.lower().replace("interface", "").replace("protocol", "")
            target_path = f"agtoosa/core/interfaces/{clean_name}.py"

        actions.append(
            PatchAction(
                action_type="INSERT_INTERFACE",
                file_path=target_path,
                symbol_name=strategy.proposed_interface_name,
                code_content=strategy.generated_code_stub,
                reason=f"Cycle Decoupling: {strategy.rationale}"
            )
        )

        return PatchPlan(
            plan_id=plan_id,
            description=f"Decouple cyclic dependency: {strategy.proposed_interface_name}",
            actions=actions
        )

    def generate_diffs(self, plan: PatchPlan) -> Dict[str, str]:
        """Compute unified diffs for all affected files without modifying disk."""
        # Group actions by file path
        actions_by_file: Dict[str, List[PatchAction]] = {}
        for a in plan.actions:
            actions_by_file.setdefault(a.file_path, []).append(a)

        diffs: Dict[str, str] = {}

        for rel_path, actions in actions_by_file.items():
            full_path = self.workspace_root / rel_path

            if not full_path.exists():
                original_lines: List[str] = []
            else:
                original_lines = full_path.read_text(encoding="utf-8").splitlines(keepends=True)

            patched_lines = list(original_lines)

            # Sort actions by start_line descending so line shifts don't invalidate line numbers
            sorted_actions = sorted(actions, key=lambda a: a.start_line, reverse=True)

            for act in sorted_actions:
                if act.action_type == "DELETE_SYMBOL":
                    # Determine line bounds (1-indexed)
                    s_idx = max(0, act.start_line - 1)
                    e_idx = min(len(patched_lines), act.end_line)
                    # Expand upwards to include preceding decorator lines
                    while s_idx > 0 and patched_lines[s_idx - 1].strip().startswith("@"):
                        s_idx -= 1
                    # Remove lines
                    del patched_lines[s_idx:e_idx]
                elif act.action_type == "INSERT_INTERFACE":
                    stub = act.code_content.strip() + "\n\n"
                    patched_lines.append(stub)

            diff_iter = difflib.unified_diff(
                original_lines,
                patched_lines,
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}"
            )
            diff_text = "".join(diff_iter)
            if diff_text:
                diffs[rel_path] = diff_text

        return diffs

    def apply_plan(self, plan: PatchPlan, dry_run: bool = False) -> Dict[str, Any]:
        """Apply patch actions with atomic backup creation and rollback manifest."""
        diffs = self.generate_diffs(plan)

        if dry_run:
            return {
                "plan_id": plan.plan_id,
                "status": "dry_run",
                "files_affected": len(diffs),
                "diffs": diffs
            }

        if not diffs:
            return {
                "plan_id": plan.plan_id,
                "status": "noop",
                "files_affected": 0,
                "diffs": {}
            }

        # Create atomic backup snapshot
        backup_snapshot_dir = self.backups_dir / plan.plan_id
        backup_snapshot_dir.mkdir(parents=True, exist_ok=True)

        manifest: Dict[str, Any] = {
            "plan_id": plan.plan_id,
            "description": plan.description,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "files": []
        }

        # Backup all files that will be touched
        for rel_path in diffs.keys():
            src_file = self.workspace_root / rel_path
            dst_file = backup_snapshot_dir / rel_path
            if src_file.exists():
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
                manifest["files"].append({"path": rel_path, "existed": True})
            else:
                manifest["files"].append({"path": rel_path, "existed": False})

        # Save manifest
        (backup_snapshot_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        # Apply modifications
        actions_by_file: Dict[str, List[PatchAction]] = {}
        for a in plan.actions:
            actions_by_file.setdefault(a.file_path, []).append(a)

        for rel_path, actions in actions_by_file.items():
            full_path = self.workspace_root / rel_path
            if not full_path.exists():
                lines: List[str] = []
            else:
                lines = full_path.read_text(encoding="utf-8").splitlines(keepends=True)

            sorted_actions = sorted(actions, key=lambda a: a.start_line, reverse=True)
            for act in sorted_actions:
                if act.action_type == "DELETE_SYMBOL":
                    s_idx = max(0, act.start_line - 1)
                    e_idx = min(len(lines), act.end_line)
                    while s_idx > 0 and lines[s_idx - 1].strip().startswith("@"):
                        s_idx -= 1
                    del lines[s_idx:e_idx]
                elif act.action_type == "INSERT_INTERFACE":
                    stub = act.code_content.strip() + "\n\n"
                    lines.append(stub)

            modified_text = "".join(lines)
            if rel_path.endswith(".py"):
                import ast
                try:
                    ast.parse(modified_text)
                except SyntaxError:
                    # Syntax validation guard: never write a syntactically invalid Python file!
                    backup_copy = backup_snapshot_dir / rel_path
                    if backup_copy.exists():
                        shutil.copy2(backup_copy, full_path)
                    continue

            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(modified_text, encoding="utf-8")

        return {
            "plan_id": plan.plan_id,
            "status": "applied",
            "backup_id": plan.plan_id,
            "backup_dir": str(backup_snapshot_dir),
            "files_affected": len(diffs),
            "diffs": diffs
        }

    def rollback(self, backup_id: str) -> bool:
        """Roll back an applied refactoring plan by restoring original files from backup."""
        snapshot_dir = self.backups_dir / backup_id
        manifest_file = snapshot_dir / "manifest.json"

        if not manifest_file.exists():
            return False

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

        for item in manifest.get("files", []):
            rel_path = item["path"]
            full_path = self.workspace_root / rel_path
            backup_file = snapshot_dir / rel_path

            if item.get("existed"):
                if backup_file.exists():
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_file, full_path)
            else:
                # File was created by patch; delete it on rollback
                if full_path.exists():
                    full_path.unlink()

        return True

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available rollback snapshots."""
        if not self.backups_dir.exists():
            return []

        backups: List[Dict[str, Any]] = []
        for d in sorted(self.backups_dir.iterdir(), reverse=True):
            manifest_file = d / "manifest.json"
            if d.is_dir() and manifest_file.exists():
                try:
                    data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    backups.append(data)
                except Exception:
                    pass
        return backups
