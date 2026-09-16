"""File scanner with configurable exclusions, security sandboxing, and safety filters."""

import os
from pathlib import Path
from typing import List, Set

from agtoosa.core.security import is_safe_path, is_sensitive_filename, load_gitignore_patterns, matches_gitignore

DEFAULT_IGNORE_DIRS = {
    ".git",
    ".agtoosa",
    "node_modules",
    ".pnpm-store",
    ".yarn",
    "venv",
    ".venv",
    "env",
    ".env",
    "vendor",
    ".bundle",
    "Pods",
    "Carthage",
    ".gradle",
    ".build",
    "DerivedData",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "coverage",
    "htmlcov",
    ".nyc_output",
    ".tox",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".output",
    ".turbo",
    ".cache",
    ".parcel-cache",
    ".idea",
    ".vscode",
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
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".webp",
    ".avif",
    ".mp4",
    ".mov",
    ".webm",
    ".avi",
    ".mp3",
    ".wav",
    ".flac",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".parquet",
    ".avro",
    ".orc",
    ".dump",
    ".safetensors",
    ".pt",
    ".pth",
    ".onnx",
    ".tflite",
    ".ckpt",
    ".lock",
    ".map",
    ".code-workspace",
    ".pdf",
    ".key",
    ".pem",
    ".pfx",
    ".p12",
}

DEFAULT_IGNORE_FILENAMES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "poetry.lock",
    "pipfile.lock",
    "cargo.lock",
    "composer.lock",
    "gemfile.lock",
    "go.sum",
}

MAX_FILE_BYTES = 2 * 1024 * 1024  # 2MB


def scan_workspace(workspace_root: Path) -> List[Path]:
    """Scan workspace directory and return list of processable source files with security sandboxing."""
    valid_files: List[Path] = []
    gitignore_patterns = load_gitignore_patterns(workspace_root)

    for root_str, dirs, files in os.walk(workspace_root):
        root = Path(root_str)
        # Modify dirs in-place to prune ignored directories
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS and not d.startswith(".")]

        for file_name in files:
            if file_name.startswith("."):
                continue

            if file_name.lower() in DEFAULT_IGNORE_FILENAMES:
                continue

            file_path = root / file_name

            # 1. Zero-trust path sandboxing (prevent symlinks escaping workspace root)
            if not is_safe_path(file_path, workspace_root):
                continue

            # 2. Sensitive filename exclusion (API keys, private keys, .env credentials)
            if is_sensitive_filename(file_path):
                continue

            # 3. Extension exclusions
            if file_path.suffix.lower() in DEFAULT_IGNORE_EXTENSIONS:
                continue

            # 4. .gitignore pattern enforcement
            try:
                rel_path_str = str(file_path.relative_to(workspace_root))
                if gitignore_patterns and matches_gitignore(rel_path_str, gitignore_patterns):
                    continue
            except ValueError:
                continue

            try:
                stat = file_path.stat()
                if stat.st_size > MAX_FILE_BYTES or stat.st_size == 0:
                    continue
            except (OSError, PermissionError):
                continue

            valid_files.append(file_path)

    return sorted(valid_files)
