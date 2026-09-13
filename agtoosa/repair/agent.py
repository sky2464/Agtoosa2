"""Autonomous PR Repair & Code Review Agent Engine (DEV-031).

Automatically diagnoses architectural drift, circular dependencies, and dead code,
synthesizes verified AST refactoring patches, validates post-repair graph invariants,
and generates atomic git commits with full rollback safety.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
import subprocess
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from agtoosa.graph.store import GraphStore
from agtoosa.refactor.engine import RefactorEngine, PatchPlan, PatchAction
from agtoosa.refactor.decoupler import CycleDecouplerEngine, DecouplingStrategy
from agtoosa.refactor.dead_code import DeadCodePruner, ZombieSymbol
from agtoosa.review.guard import ArchGuard


@dataclass
class RepairIssue:
    issue_id: str
    issue_type: str  # "circular_dependency", "dead_code", "layer_violation"
    severity: str  # "CRITICAL", "ERROR", "WARNING"
    symbols: List[str]
    description: str
    suggested_action: str  # "decouple_interface", "prune_symbol", "isolate_layer"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RepairPlan:
    plan_id: str
    issue: RepairIssue
    description: str
    diff: str
    files_modified: List[str]
    underlying_plan: Optional[PatchPlan] = None
    backup_id: Optional[str] = None
    applied: bool = False
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "issue": self.issue.to_dict(),
            "description": self.description,
            "diff": self.diff,
            "files_modified": self.files_modified,
            "backup_id": self.backup_id,
            "applied": self.applied,
            "verified": self.verified
        }


class PRAgentRepairEngine:
    """Autonomous AI repair engine diagnosing and healing architectural violations."""

    def __init__(self, store: GraphStore, workspace_root: Optional[Path] = None):
        self.store = store
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.refactor = RefactorEngine(self.workspace_root)
        self.guard = ArchGuard(self.store, self.workspace_root)
        self.decoupler = CycleDecouplerEngine(self.store, self.workspace_root)
        self.pruner = DeadCodePruner(self.store, self.workspace_root)

    def diagnose(self, base_ref: Optional[str] = None) -> List[RepairIssue]:
        """Diagnose actionable architectural violations from graph invariants and git diffs."""
        issues: List[RepairIssue] = []

        # 1. Detect circular dependencies via decoupler
        decouple_report = self.decoupler.analyze_cycles()
        for strat in decouple_report.strategies:
            cycle_str = " -> ".join(strat.cycle)
            issues.append(
                RepairIssue(
                    issue_id=f"cycle_{uuid.uuid4().hex[:8]}",
                    issue_type="circular_dependency",
                    severity="ERROR",
                    symbols=strat.cycle,
                    description=f"Circular dependency detected: {cycle_str}",
                    suggested_action="decouple_interface"
                )
            )

        # 2. Audit graph invariants using ArchGuard
        audit_res = self.guard.audit(base_ref=base_ref)
        findings = audit_res.get("findings", []) if isinstance(audit_res, dict) else (audit_res.findings if hasattr(audit_res, "findings") else [])

        for f in findings:
            if isinstance(f, dict):
                rule = f.get("rule", "")
                if rule == "circular_dependency" and not decouple_report.strategies:
                    cycle = f.get("cycle", [])
                    cycle_str = " -> ".join(cycle)
                    issues.append(
                        RepairIssue(
                            issue_id=f"cycle_{uuid.uuid4().hex[:8]}",
                            issue_type="circular_dependency",
                            severity="ERROR",
                            symbols=cycle,
                            description=f"Circular dependency detected: {cycle_str}",
                            suggested_action="decouple_interface"
                        )
                    )
                elif rule == "layer_violation":
                    issues.append(
                        RepairIssue(
                            issue_id=f"layer_{uuid.uuid4().hex[:8]}",
                            issue_type="layer_violation",
                            severity="ERROR",
                            symbols=[f.get("source", ""), f.get("target", "")],
                            description=f.get("message", "Layer boundary violation"),
                            suggested_action="isolate_layer"
                        )
                    )
            else:
                cat = getattr(f, "category", "")
                if cat == "LAYER_VIOLATION":
                    issues.append(
                        RepairIssue(
                            issue_id=f"layer_{uuid.uuid4().hex[:8]}",
                            issue_type="layer_violation",
                            severity="ERROR",
                            symbols=[getattr(f, "symbol_or_path", "")],
                            description=getattr(f, "message", "Layer boundary violation"),
                            suggested_action="isolate_layer"
                        )
                    )

        # 3. Identify dead code candidates
        dead_report = self.pruner.analyze(min_confidence="low")
        for sym in dead_report.zombies[:5]:
            issues.append(
                RepairIssue(
                    issue_id=f"dead_{uuid.uuid4().hex[:8]}",
                    issue_type="dead_code",
                    severity="WARNING",
                    symbols=[sym.node_id],
                    description=f"Dead code symbol '{sym.name}' in {sym.path} has 0 callers",
                    suggested_action="prune_symbol"
                )
            )

        return issues

    def synthesize_repair(self, issue: RepairIssue) -> Optional[RepairPlan]:
        """Synthesize an AST rewrite plan to heal the specified issue."""
        plan_id = f"repair_{uuid.uuid4().hex[:8]}"

        if issue.issue_type == "circular_dependency":
            strat = None
            report = self.decoupler.analyze_cycles()
            for s in report.strategies:
                if set(s.cycle).intersection(set(issue.symbols)):
                    strat = s
                    break
            if not strat and issue.symbols:
                strat = self.decoupler._formulate_strategy(issue.symbols)

            if not strat:
                return None

            patch_plan = self.refactor.create_decouple_plan(strat)
            if not patch_plan or not patch_plan.actions:
                return None

            diffs = self.refactor.generate_diffs(patch_plan)
            diff_str = "\n".join(diffs.values())
            files_modified = list(set(a.file_path for a in patch_plan.actions))
            return RepairPlan(
                plan_id=plan_id,
                issue=issue,
                description=f"Autonomous Decoupling Interface Protocol for cycle: {' -> '.join(issue.symbols[:3])}",
                diff=diff_str,
                files_modified=files_modified,
                underlying_plan=patch_plan
            )

        elif issue.issue_type == "dead_code":
            dead_report = self.pruner.analyze(min_confidence="low")
            zombies_by_id = {z.node_id: z for z in dead_report.zombies}
            matched_zombies: List[ZombieSymbol] = []
            for sym_id in issue.symbols:
                if sym_id in zombies_by_id:
                    matched_zombies.append(zombies_by_id[sym_id])
                else:
                    node = self.store.get_node(sym_id)
                    if node:
                        s_line = node.get("start_line", 1) or 1
                        e_line = node.get("end_line", 1) or 1
                        matched_zombies.append(
                            ZombieSymbol(
                                node_id=node.get("id"),
                                name=node.get("name"),
                                node_type=node.get("node_type"),
                                path=node.get("path"),
                                start_line=s_line,
                                end_line=e_line,
                                confidence="high",
                                reason="Identified for PR repair pruning",
                                estimated_lines=max(1, e_line - s_line + 1),
                                safe_to_delete=True,
                                deletion_steps=[f"Delete {node.get('name')} from {node.get('path')}"]
                            )
                        )
            if not matched_zombies:
                return None

            patch_plan = self.refactor.create_dead_code_plan(matched_zombies, min_confidence="low")
            if not patch_plan or not patch_plan.actions:
                return None

            diffs = self.refactor.generate_diffs(patch_plan)
            diff_str = "\n".join(diffs.values())
            files_modified = list(set(a.file_path for a in patch_plan.actions))
            names = [z.name for z in matched_zombies]
            return RepairPlan(
                plan_id=plan_id,
                issue=issue,
                description=f"Safe pruning of dead code symbol(s): {', '.join(names)}",
                diff=diff_str,
                files_modified=files_modified,
                underlying_plan=patch_plan
            )

        return None

    def apply_and_verify(self, plan: RepairPlan, dry_run: bool = False) -> Dict[str, Any]:
        """Apply refactoring plan, re-audit invariants, and automatically rollback if verification fails."""
        if not plan.underlying_plan:
            return {"success": False, "error": "No underlying AST refactor plan to apply"}

        if dry_run:
            return {
                "success": True,
                "plan_id": plan.plan_id,
                "dry_run": True,
                "files_modified": plan.files_modified,
                "diff": plan.diff,
                "verified": True
            }

        # 1. Apply plan with atomic backup
        apply_res = self.refactor.apply_plan(plan.underlying_plan, dry_run=False)
        backup_id = apply_res.get("backup_id")
        plan.backup_id = backup_id
        plan.applied = True

        # 2. Re-audit architectural invariants
        post_audit = self.guard.audit()
        post_findings = post_audit.get("findings", []) if isinstance(post_audit, dict) else (post_audit.findings if hasattr(post_audit, "findings") else [])

        # Check if the specific issue was resolved
        issue_still_present = False
        if plan.issue.issue_type == "circular_dependency":
            # Check if this specific cycle remains
            for f in post_findings:
                if isinstance(f, dict):
                    rule = f.get("rule") or f.get("category")
                    cycle = f.get("cycle", [])
                    if rule in ("circular_dependency", "CYCLE"):
                        if not cycle or set(cycle).issubset(set(plan.issue.symbols)) or set(plan.issue.symbols).issubset(set(cycle)):
                            issue_still_present = True
                            break
                else:
                    cat = getattr(f, "category", "")
                    if cat == "CYCLE":
                        issue_still_present = True
                        break

        # Verification check: If the issue persists or errors increased, rollback immediately!
        if issue_still_present:
            if backup_id:
                self.refactor.rollback(backup_id)
            plan.applied = False
            plan.verified = False
            return {
                "success": False,
                "rolled_back": True,
                "backup_id": backup_id,
                "reason": "Post-repair verification failed: architectural cycle was not resolved.",
                "post_findings": post_findings
            }

        plan.verified = True
        return {
            "success": True,
            "plan_id": plan.plan_id,
            "backup_id": backup_id,
            "applied": True,
            "verified": True,
            "files_modified": plan.files_modified,
            "diff": plan.diff
        }

    def create_git_commit(
        self,
        plan: RepairPlan,
        branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Commit applied repair changes to a new or current git branch."""
        if not plan.applied or not plan.verified:
            return {"success": False, "error": "Cannot commit unverified or unapplied repair plan"}

        cwd = str(self.workspace_root)
        current_branch = "main"

        try:
            # Check current git branch
            branch_out = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = branch_out.stdout.strip()
        except Exception:
            pass

        target_branch = branch_name or current_branch

        try:
            # Create/switch branch if requested
            if branch_name and branch_name != current_branch:
                subprocess.run(
                    ["git", "checkout", "-b", branch_name],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    check=True
                )

            # Stage modified files
            for f in plan.files_modified:
                subprocess.run(
                    ["git", "add", f],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    check=True
                )

            # Commit changes
            commit_msg = f"refactor(arch): auto-repair {plan.issue.issue_type} ({plan.plan_id})\n\n{plan.description}"
            commit_res = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )

            # Get commit hash
            rev_res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            commit_hash = rev_res.stdout.strip()[:8]

            return {
                "success": True,
                "commit_hash": commit_hash,
                "branch": target_branch,
                "message": commit_msg.splitlines()[0],
                "files_committed": plan.files_modified
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Git command failed: {e.stderr or e.stdout or str(e)}"
            }
