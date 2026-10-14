# DEV-060: Zero-Friction Autopilot Governance

> **Cycle:** DEV-060
> **Milestone:** Milestone 19 (v0.9.10)
> **Status:** Completed (shipped in `85e8d93`; this spec backfills spec-driven governance)
> **Type:** CLI / Agent Governance / Git Hooks
> **Issue:** [#8](https://github.com/sky2464/Agtoosa2/issues/8) — spec drift for shipped `autopilot` command

---

## 1. Problem Statement

Commit `85e8d93` ("feat(autopilot): introduce zero-friction autopilot command and effortless agent governance (v0.9.10)") shipped the `agtoosa autopilot` command to `main` without an approved specification or Master-Plan registration: a spec-driven governance violation. This spec retroactively defines the contract the implementation must (and does) satisfy, so future changes to the command are reviewable against written acceptance criteria.

The command's purpose is **zero-friction agent governance**: a single invocation that (a) non-destructively installs Agtoosa's architectural guardrail instructions into every supported AI-agent rule surface of a workspace, and (b) optionally installs git hooks that enforce graph invariants automatically, so agents and hooks do the right thing without the developer running further commands.

## 2. Acceptance Criteria

- **AC-1 (Command aliases & dispatch)**: The CLI SHALL expose `agtoosa autopilot` as an alias of `agtoosa agent-init` (with `setup` as a third alias). All three commands SHALL dispatch to `cmd_agent_init` in `agtoosa/cli/lifecycle_cmd.py` and return exit code `0` on success.
- **AC-2 (CLI options)**: `autopilot` SHALL accept `-t/--target` with choices `all | agents | claude | cursor | windsurf | copilot` (default `all`), `--no-git-hooks` (skip git hook installation), and `--json` (emit the result dict as JSON instead of the human report). Verified: `tests/test_agent_rules.py::test_cli_agent_init_command`.
- **AC-3 (Non-destructive multi-target rule injection)**: `AgentWorkflowEnforcer.install_all` in `agtoosa/core/agent_rules.py` SHALL install/update the delimited rules block (`<!-- AGTOOSA_AGENT_RULES_START -->` … `<!-- AGTOOSA_AGENT_RULES_END -->`) in up to five targets:
  1. `AGENTS.md` (universal: Antigravity, Gemini CLI, Codex, Cursor),
  2. `CLAUDE.md` (Claude Code),
  3. `.cursor/rules/agtoosa.mdc` (Cursor, with `globs: *` front-matter),
  4. `.windsurfrules` (Windsurf),
  5. `.github/copilot-instructions.md` (GitHub Copilot).
  Injection MUST be non-destructive: pre-existing user content outside the delimiters is preserved verbatim, and re-running replaces the block in place without duplicating it (exactly one START/END tag pair after two consecutive runs). Verified: `tests/test_agent_rules.py::test_fresh_installation_all_targets`, `::test_non_destructive_preservation_of_existing_instructions`.
- **AC-4 (Enforcement status)**: `is_enforced()` SHALL return `True` when at least one primary rule file (`AGENTS.md`, `CLAUDE.md`, `.cursor/rules/agtoosa.mdc`) contains the rules block. `get_status()` SHALL report per-target enforcement. The JSON output of `autopilot --json` SHALL include `installed_files`, `is_enforced`, and `workspace`.
- **AC-5 (Git hook installation)**: Git hook installation SHALL be handled by `agtoosa/watcher/hooks.py::install_git_hooks`, writing exactly four signature-tagged hooks (`# Agtoosa Git Hook`) into `<workspace>/.git/hooks/`:
  - `pre-commit` → `agtoosa review --strict` (architectural drift before commit),
  - `pre-push` → `agtoosa guard --strict` (zero circular dependencies before push),
  - `post-merge` → `agtoosa graph build` (re-sync knowledge graph after merge/pull),
  - `post-checkout` → `agtoosa graph build` (re-sync after branch switch).
  Installation MUST be executable-bit safe and MUST refuse to overwrite foreign (non-Agtoosa-signatured) hooks on removal (`remove_git_hooks` only unlinks files carrying the signature). No-op (empty result) when the workspace has no `.git` directory.

## 3. Known Deviations (documented drift, not yet remediated)

- **D-1 — CLI never installs git hooks.** `cmd_agent_init` reads `--no-git-hooks` but `AgentWorkflowEnforcer.install_all` ignores `with_git_hooks`: the CLI path returns no `git_hooks_installed` key, so the "Git Pre-Push & Review Hooks" report block never prints. Hook installation currently happens only through the Studio web endpoint `POST /api/agent/enforce` (`agtoosa/graph/server.py`), which calls `install_git_hooks` when `with_git_hooks` is true. The `--no-git-hooks` CLI flag is therefore a no-op today. Follow-up: wire `install_git_hooks` into `cmd_agent_init` so the CLI honors the flag and prints the hook report.
- **D-2 — No automatic graph indexing or cycle-detection thresholds.** The original feature commit message described "automatic graph indexing, cycle detection thresholds, or multi-agent configuration updates"; the shipped implementation performs neither — indexing is `agtoosa graph build`, cycle detection is `agtoosa review`/`agtoosa guard`, invoked by hooks, not by autopilot itself. This spec binds the command to its actual contract (rule-file injection + hooks); any future auto-indexing behavior needs its own AC.

## 4. Tasks & Deliverables

- [x] **Task 60.1**: `agtoosa autopilot` (alias of `agent-init`/`setup`) parser + dispatch in `agtoosa/cli/main.py` → `cmd_agent_init` (`agtoosa/cli/lifecycle_cmd.py`), incl. `-t/--target`, `--no-git-hooks`, `--json`.
- [x] **Task 60.2**: `AgentWorkflowEnforcer` (`agtoosa/core/agent_rules.py`): `install_all`, `inject_or_update`, `is_enforced`, `get_status` with delimited non-destructive injection across the five agent targets.
- [x] **Task 60.3**: `agtoosa/watcher/hooks.py`: `install_git_hooks` / `remove_git_hooks` / `get_git_hooks_status` for the four signature-tagged hooks.
- [x] **Task 60.4**: `POST /api/agent/enforce` in `agtoosa/graph/server.py` wiring enforcer + hook installer for the Studio 1-click path.
- [x] **Task 60.5**: Test coverage in `tests/test_agent_rules.py` (fresh install, non-destructive re-run, CLI dispatch for all three aliases).
- [x] **Task 60.6**: Backfill this spec (`docs/specs/spec-DEV-060-zero-friction-autopilot-governance.md`) and register DEV-060 in `docs/Master-Plan.md` (closes #8's autopilot drift item).
- [ ] **Task 60.7 (follow-up)**: Wire `install_git_hooks` into `cmd_agent_init` so the CLI honors `--no-git-hooks` and reports hook status (D-1).

## 5. Verification

- `python -m unittest tests.test_agent_rules` — green (fresh install, idempotent re-run, alias dispatch).
- `python -m unittest tests.test_cli` — green (parser registration for `update`/`upgrade` unaffected).
