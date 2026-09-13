"""Git hook installer and manager for automated continuous graph integrity."""

import os
from pathlib import Path
import stat
from typing import Dict

HOOK_SIGNATURE = "# Agtoosa Git Hook"

HOOK_SCRIPTS = {
    "pre-commit": f"""#!/bin/sh
{HOOK_SIGNATURE}: pre-commit
# Enforce graph invariants and catch architectural drift before commit
agtoosa review --strict
""",
    "pre-push": f"""#!/bin/sh
{HOOK_SIGNATURE}: pre-push
# Enforce zero circular dependencies and blast radius thresholds before push
agtoosa guard --strict
""",
    "post-merge": f"""#!/bin/sh
{HOOK_SIGNATURE}: post-merge
# Incrementally sync knowledge graph after branch merge or pull
agtoosa graph build
""",
    "post-checkout": f"""#!/bin/sh
{HOOK_SIGNATURE}: post-checkout
# Incrementally sync knowledge graph after switching branches
agtoosa graph build
"""
}


def _get_hooks_dir(workspace_root: Path) -> Path:
    return workspace_root / ".git" / "hooks"


def install_git_hooks(workspace_root: Path) -> Dict[str, bool]:
    """Install pre-commit, pre-push, post-merge, and post-checkout hooks into repository .git/hooks/."""
    hooks_dir = _get_hooks_dir(workspace_root)
    if not (workspace_root / ".git").is_dir():
        return {}

    hooks_dir.mkdir(parents=True, exist_ok=True)
    status: Dict[str, bool] = {}

    for hook_name, script_content in HOOK_SCRIPTS.items():
        hook_path = hooks_dir / hook_name
        try:
            hook_path.write_text(script_content, encoding="utf-8")
            # Make executable
            current_mode = hook_path.stat().st_mode
            hook_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            status[hook_name] = True
        except OSError:
            status[hook_name] = False

    return status


def remove_git_hooks(workspace_root: Path) -> Dict[str, bool]:
    """Safely remove Agtoosa hooks from .git/hooks/ without touching external hooks."""
    hooks_dir = _get_hooks_dir(workspace_root)
    if not hooks_dir.is_dir():
        return {}

    status: Dict[str, bool] = {}

    for hook_name in HOOK_SCRIPTS:
        hook_path = hooks_dir / hook_name
        if hook_path.is_file():
            try:
                content = hook_path.read_text(encoding="utf-8", errors="replace")
                if HOOK_SIGNATURE in content:
                    hook_path.unlink()
                    status[hook_name] = True
                else:
                    status[hook_name] = False  # Custom hook present, not unlinking
            except OSError:
                status[hook_name] = False
        else:
            status[hook_name] = False

    return status


def get_git_hooks_status(workspace_root: Path) -> Dict[str, bool]:
    """Check which Agtoosa hooks are currently installed and executable."""
    hooks_dir = _get_hooks_dir(workspace_root)
    status: Dict[str, bool] = {}

    for hook_name in HOOK_SCRIPTS:
        hook_path = hooks_dir / hook_name
        if hook_path.is_file():
            try:
                content = hook_path.read_text(encoding="utf-8", errors="replace")
                is_exec = os.access(hook_path, os.X_OK)
                status[hook_name] = HOOK_SIGNATURE in content and is_exec
            except OSError:
                status[hook_name] = False
        else:
            status[hook_name] = False

    return status
