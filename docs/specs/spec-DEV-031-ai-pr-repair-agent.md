# Specification: DEV-031 AI Automated PR Repair & Code Review Agent

## Status
Implemented / Ready for Verification

## Priority Score
**79 / 100** (Milestone 13 — Autonomous Code Healing: Generates automated PR branch commits with refactor fixes directly resolving detected architectural drift, circular dependencies, dead code, and breaking schema changes).

## Problem Statement
While PR review bots (`DEV-029`) and pre-push daemons (`DEV-024`) detect architectural violations and blast radius regressions, developers still face the friction of manually designing interface protocols, unlinking cyclic dependencies, or safely deleting dead symbols without introducing runtime regressions.

## Objectives
1. **Autonomous Architectural Diagnostics (`PRAgentRepairEngine`)**:
   - Analyzes PR diffs or working tree against base ref.
   - Combines `ArchGuard` and `DeadCodePruner` to identify actionable architectural issues:
     - Circular dependency cycles ($A \rightarrow B \rightarrow A$).
     - Dead code symbols with zero callers.
     - Layer boundary leaks.
2. **Autonomous AST Healing & Patch Synthesis**:
   - Synthesizes decoupled interface protocols and dependency injection seams for circular dependencies using `DecouplerEngine`.
   - Synthesizes safe AST symbol deletions for dead code using `RefactorEngine`.
3. **Automated Post-Repair Verification & Atomic Rollback**:
   - Applies AST rewrites to workspace files.
   - Re-audits graph invariants immediately with `ArchGuard`.
   - If invariants pass, marks patch as verified.
   - If verification fails or regression occurs, triggers automatic atomic rollback (`RefactorEngine.rollback`) using the pre-repair snapshot!
4. **Git Commit & PR Branch Generation**:
   - Automatically creates conventional git commits: `refactor(arch): auto-repair <issue_type> in <symbols>`.
   - Supports creating dedicated fix branches (`--branch <name>`).
5. **Developer & Agent Surfaces**:
   - CLI: `agtoosa ci repair [--apply] [--dry-run] [--branch <name>] [--base <ref>] [--json]`.
   - MCP Tool: `agtoosa_auto_repair_pr` allowing AI coding agents to trigger automated autonomous code healing and preview verified patches.

## Architecture

```
[ PR Diff / Local Worktree ]
           │
           ▼
 [ PRAgentRepairEngine ]
 ├── 1. Diagnose: ArchGuard & DeadCodePruner
 ├── 2. Synthesize: RefactorEngine & DecouplerEngine
 └── 3. Apply with Atomic Backup Snapshot
           │
           ▼
[ Invariant Verification Gate ]
 ├── PASS ──► Commit to git / PR branch (refactor(arch): ...)
 └── FAIL ──► Atomic Rollback Snapshot (Restore pristine files)
```
