"""File scanner with configurable exclusions and safety filters."""

import os
from pathlib import Path
from typing import List, Set

DEFAULT_IGNORE_DIRS = {
    ".git",
    ".agtoosa",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    "target",
    ".DS_Store",
}

DEFAULT_IGNORE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".bin",
    ".tar",
    ".gz",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".key",
    ".pem",
}

MAX_FILE_BYTES = 2 * 1024 * 1024  # 2MB


def scan_workspace(workspace_root: Path) -> List[Path]:
    """Scan workspace directory and return list of processable source files."""
    valid_files: List[Path] = []

    for root_str, dirs, files in os.walk(workspace_root):
        root = Path(root_str)
        # Modify dirs in-place to prune ignored directories
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS and not d.startswith(".")]

        for file_name in files:
            if file_name.startswith(".") and file_name != ".gitignore":
                continue

            file_path = root / file_name
            if file_path.suffix.lower() in DEFAULT_IGNORE_EXTENSIONS:
                continue

            try:
                stat = file_path.stat()
                if stat.st_size > MAX_FILE_BYTES or stat.st_size == 0:
                    continue
            except (OSError, PermissionError):
                continue

            valid_files.append(file_path)

    return sorted(valid_files)
