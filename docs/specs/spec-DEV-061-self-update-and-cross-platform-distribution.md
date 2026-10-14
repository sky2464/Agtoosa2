# DEV-061: Self-Update CLI & Cross-Platform Distribution

> **Cycle:** DEV-061
> **Milestone:** Milestone 19 (v0.9.11)
> **Status:** Completed (shipped in `65ad66b`/`530209e`/`0eb86bc`; this spec backfills spec-driven governance)
> **Type:** CLI / Distribution / Installers
> **Issue:** [#8](https://github.com/sky2464/Agtoosa2/issues/8) — spec drift for shipped self-update CLI and Windows installer

---

## 1. Problem Statement

Two user-facing distribution mechanisms shipped to `main` without specification backing or Master-Plan synchronization:

1. **Self-update commands** — commits `65ad66b` ("feat(cli): add agtoosa update and upgrade commands to self-update from GitHub") and `530209e` ("fix(cli): prioritize tool env detection in agtoosa update") added `agtoosa update` / `agtoosa upgrade` to `agtoosa/cli/main.py`, with no spec defining the environment-resolution protocol or its boundary behavior.
2. **Windows PowerShell installer parity** — commit `0eb86bc` ("docs: add first-class Windows installation guide and install.ps1 PowerShell installer") added `install.ps1` (root) alongside the POSIX `install.sh`, establishing cross-platform install parity with no architectural contract.

This spec retroactively defines both contracts as implemented, so the update path and the two installers can be audited, tested, and evolved against written criteria.

## 2. Acceptance Criteria

### 2.1 Self-update CLI (`cmd_update`, `agtoosa/cli/main.py`)

- **AC-1 (Command surface)**: The CLI SHALL expose both `agtoosa update` and `agtoosa upgrade` as aliases dispatching to `cmd_update`. `update --help` and `upgrade --help` MUST both succeed (exit 0). Verified: `tests/test_cli.py::test_cli_update_command_dispatch`.
- **AC-2 (Environment resolution order)**: `cmd_update` SHALL attempt update strategies in this fixed priority order, proceeding to the next step when the current one does not apply or returns non-zero:
  1. **uv tool environment** — if `sys.executable`/`sys.prefix` contains `uv/tools` and `uv` is on PATH → `uv tool install --force git+https://github.com/sky2464/Agtoosa2.git`;
  2. **pipx environment** — if the paths contain `pipx` and `pipx` is on PATH → `pipx install --force <repo_url>`;
  3. **local git repository** — if `<workspace>/pyproject.toml` exists and declares `name = "agtoosa"` → `git pull` in the workspace, then editable reinstall (`uv pip install -e .[full]` if `uv` exists, else `pip install -e .[full]`);
  4. **uv available** → `uv tool install --force <repo_url>`;
  5. **pipx available** → `pipx install --force <repo_url>`;
  6. **pip fallback** → `sys.executable -m pip install --upgrade <repo_url>`;
  7. **universal installer** — `powershell … irm <install.ps1> | iex` on `win32`, otherwise `curl -fsSL <install.sh> | bash`; return its exit code.
- **AC-3 (Source of truth)**: All remote steps SHALL target `git+https://github.com/sky2464/Agtoosa2.git` (latest main) and the raw installers on the `main` branch. There is no release-tag pinning and no network timeout: subprocess failures propagate as non-zero exit codes.
- **AC-4 (Boundary)**: `cmd_update` MUST NOT modify any file outside the Python environment/installer it drives; it performs no version comparison and no rollback — a failed update simply reports the failing step's exit code.

### 2.2 Cross-platform installers (`install.sh`, `install.ps1`)

- **AC-5 (Parity contract)**: `install.sh` (POSIX) and `install.ps1` (Windows) SHALL implement the same three-phase contract:
  1. **Runtime detection** — locate a compatible Python (`>= 3.11`; `install.sh` tries `python3 python python3.13 python3.12 python3.11`, `install.ps1` tries `py python python3`) and exit non-zero with install guidance when absent;
  2. **Tool-ordered install** — `uv` → `pipx` → isolated user venv (`~/.agtoosa/venv` via `python -m venv`), installing from the local repo when `pyproject.toml` declares `name = "agtoosa"`, else from `git+https://github.com/sky2464/Agtoosa2.git`. `install.ps1` additionally writes a `~/.local/bin/agtoosa.cmd` wrapper for the venv path;
  3. **PATH verification** — warn (not fail) with platform-specific remediation when `~/.local/bin` is not on `PATH`.
- **AC-6 (Zero dependency conflicts)**: Both installers MUST prefer isolated installation targets (`uv tool` / `pipx` / dedicated venv) and MUST NOT install into the system Python.

## 3. Known Deviations (documented drift, not yet remediated)

- **D-1 — No `docs/INSTALL_WINDOWS.md`.** The original installer commit message references a Windows install guide, but no such file exists in the tree (verified on `main`); Windows install documentation lives in `README.md` instead. Follow-up: either restore the guide or correct the historical reference; this spec does not invent the missing file.
- **D-2 — No release-tag resolution or network timeouts.** Self-update always tracks latest `main` with unbounded subprocess calls. Any future "update to version X" or offline-timeout behavior needs its own AC and tests.

## 4. Tasks & Deliverables

- [x] **Task 61.1**: `cmd_update` in `agtoosa/cli/main.py` with the 7-step resolution ladder (`65ad66b`), plus tool-env detection priority fix (`530209e`).
- [x] **Task 61.2**: `install.ps1` root installer (Windows parity with `install.sh`): Python ≥ 3.11 detection, uv → pipx → venv ordering, `agtoosa.cmd` wrapper, PATH check (`0eb86bc`, also mirrored under `scripts/install.ps1`).
- [x] **Task 61.3**: Parser registration tests in `tests/test_cli.py::test_cli_update_command_dispatch`.
- [x] **Task 61.4**: Backfill this spec (`docs/specs/spec-DEV-061-self-update-and-cross-platform-distribution.md`) and register DEV-061 in `docs/Master-Plan.md` (closes #8's self-update/installer drift items).

## 5. Verification

- `python -m unittest tests.test_cli` — green (update/upgrade parser registration).
- `python -m unittest tests.test_distribution` — green (distribution/formula/version checks unaffected).
- Installers are exercised manually per platform (CI does not execute them); parity is reviewed by reading both scripts against AC-5.
