"""File scanner with configurable exclusions, security sandboxing, and safety filters."""

import os
from pathlib import Path
from typing import List, Set

from agtoosa.core.security import is_safe_path, is_sensitive_filename, load_gitignore_patterns, matches_gitignore

DEFAULT_IGNORE_DIRS = {
    # Version control & IDE / environment state
    ".git",
    ".agtoosa",
    ".idea",
    ".vscode",
    ".DS_Store",
    # External package stores (Node, Python, Go, PHP, Ruby, Java, CocoaPods, Carthage)
    "node_modules",
    ".pnpm-store",
    ".yarn",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pypackages__",
    "vendor",
    ".bundle",
    "Pods",
    "pods",
    "Carthage",
    "carthage",
    ".gradle",
    ".m2",
    # Bundlers, compilers & build artifacts
    "dist",
    "build",
    "out",
    "target",
    ".build",
    "DerivedData",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".output",
    ".turbo",
    ".cache",
    ".parcel-cache",
    ".rollup.cache",
    ".swc",
    ".docusaurus",
    # Test & coverage artifacts
    "coverage",
    "htmlcov",
    ".nyc_output",
    ".tox",
    ".nox",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    # Codegen & snapshot directories
    "__generated__",
    "__snapshots__",
}

DEFAULT_IGNORE_DIRS_LOWER = {d.lower() for d in DEFAULT_IGNORE_DIRS}

DEFAULT_IGNORE_EXTENSIONS = {
    # Bytecode, compiled binaries & native libraries
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".bin",
    ".class",
    ".jar",
    ".war",
    ".ear",
    ".wasm",
    ".o",
    ".obj",
    ".a",
    ".lib",
    # Archives & compressed packages
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".zip",
    # Raster & vector graphics
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".webp",
    ".avif",
    ".bmp",
    ".tiff",
    ".tif",
    # Video & audio assets
    ".mp4",
    ".mov",
    ".webm",
    ".avi",
    ".mkv",
    ".mp3",
    ".wav",
    ".flac",
    ".aac",
    ".ogg",
    ".m4a",
    # Typography & web fonts
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    # Big Data & columnar storage / dumps
    ".parquet",
    ".avro",
    ".orc",
    ".dump",
    ".arrow",
    ".feather",
    # Machine Learning & Deep Learning weights & checkpoints
    ".safetensors",
    ".pt",
    ".pth",
    ".onnx",
    ".tflite",
    ".ckpt",
    ".h5",
    ".hdf5",
    ".pb",
    ".pkl",
    ".pickle",
    ".npy",
    ".npz",
    ".gguf",
    ".ggml",
    ".mlmodel",
    # Lockfiles, resolved manifests & dev maps
    ".lock",
    ".lockb",
    ".resolved",
    ".map",
    ".code-workspace",
    # Documents & office binaries
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    # Security keys, certificates & stores
    ".key",
    ".pem",
    ".pfx",
    ".p12",
}

DEFAULT_IGNORE_FILENAMES = {
    # Node & JavaScript ecosystems
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "bun.lock",
    "npm-shrinkwrap.json",
    # Python ecosystem
    "poetry.lock",
    "pipfile.lock",
    # Rust & Go ecosystems
    "cargo.lock",
    "go.sum",
    "go.work.sum",
    # PHP & Ruby ecosystems
    "composer.lock",
    "gemfile.lock",
    # Swift, CocoaPods & Carthage ecosystems
    "podfile.lock",
    "cartfile.resolved",
    "package.resolved",
    # Other package managers & build tools
    "pubspec.lock",
    "mix.lock",
    "flake.lock",
    "gradle.lockfile",
}

MAX_FILE_BYTES = 2 * 1024 * 1024  # 2MB


def scan_workspace(workspace_root: Path) -> List[Path]:
    """Scan workspace directory and return list of processable source files with security sandboxing."""
    valid_files: List[Path] = []
    gitignore_patterns = load_gitignore_patterns(workspace_root)

    for root_str, dirs, files in os.walk(workspace_root):
        root = Path(root_str)
        # Modify dirs in-place to prune ignored directories
        dirs[:] = [
            d for d in dirs
            if d not in DEFAULT_IGNORE_DIRS
            and d.lower() not in DEFAULT_IGNORE_DIRS_LOWER
            and not d.startswith(".")
        ]

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
