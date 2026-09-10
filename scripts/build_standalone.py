#!/usr/bin/env python3
"""Build and package standalone Agtoosa binary for multi-platform distribution."""

import argparse
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from typing import Optional, Tuple

# Try to import agtoosa version, or fallback if run standalone
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from agtoosa import __version__ as AGTOOSA_VERSION
except ImportError:
    AGTOOSA_VERSION = "0.2.1-dev"


def detect_target_platform() -> Tuple[str, str]:
    """Detect normalized OS and CPU architecture for binary naming."""
    system = sys.platform.lower()
    if system.startswith("darwin"):
        os_name = "darwin"
    elif system.startswith("linux"):
        os_name = "linux"
    elif system.startswith("win"):
        os_name = "windows"
    else:
        os_name = system

    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        arch_name = "arm64"
    elif machine in ("x86_64", "amd64", "x64"):
        arch_name = "x86_64"
    else:
        arch_name = machine

    return os_name, arch_name


def get_archive_name(version: str, os_name: str, arch_name: str) -> str:
    """Generate standardized release archive filename."""
    ext = "zip" if os_name == "windows" else "tar.gz"
    clean_version = version.lstrip("v")
    return f"agtoosa-v{clean_version}-{os_name}-{arch_name}.{ext}"


def compute_sha256(filepath: Path) -> str:
    """Calculate hex-encoded SHA-256 checksum of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def create_release_archive(
    binary_path: Path,
    output_dir: Path,
    archive_name: str
) -> Tuple[Path, str]:
    """Package binary along with LICENSE and README into release archive."""
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / archive_name

    extra_files = []
    license_file = REPO_ROOT / "LICENSE"
    if license_file.is_file():
        extra_files.append(license_file)
    readme_file = REPO_ROOT / "README.md"
    if readme_file.is_file():
        extra_files.append(readme_file)

    if archive_name.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(binary_path, arcname=binary_path.name)
            for extra in extra_files:
                zf.write(extra, arcname=extra.name)
    else:
        with tarfile.open(archive_path, "w:gz") as tf:
            tf.add(binary_path, arcname=binary_path.name)
            for extra in extra_files:
                tf.add(extra, arcname=extra.name)

    # Compute checksum
    digest = compute_sha256(archive_path)
    checksum_path = Path(str(archive_path) + ".sha256")
    checksum_path.write_text(f"{digest}  {archive_name}\n", encoding="utf-8")

    return archive_path, digest


def run_pyinstaller_build(spec_path: Path, dist_dir: Path) -> Path:
    """Execute PyInstaller build process."""
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--distpath",
        str(dist_dir),
        str(spec_path),
    ]
    print(f"🔨 Running PyInstaller: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)

    binary_name = "agtoosa.exe" if sys.platform.startswith("win") else "agtoosa"
    binary_path = dist_dir / binary_name
    if not binary_path.exists():
        raise FileNotFoundError(f"Expected compiled binary at {binary_path} was not created.")
    return binary_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and package standalone Agtoosa binary")
    parser.add_argument("--version", type=str, default=AGTOOSA_VERSION, help="Release version string")
    parser.add_argument("--dist-dir", type=str, default="dist", help="Output distribution directory")
    parser.add_argument("--skip-build", action="store_true", help="Skip PyInstaller and package existing binary")
    parser.add_argument("--check-only", action="store_true", help="Verify platform and environment without building")

    args = parser.parse_args()
    os_name, arch_name = detect_target_platform()
    archive_name = get_archive_name(args.version, os_name, arch_name)

    print(f"📦 Agtoosa Distribution Builder")
    print(f"   • Version:      {args.version}")
    print(f"   • Platform:     {os_name} ({platform.system()})")
    print(f"   • Architecture: {arch_name} ({platform.machine()})")
    print(f"   • Target Name:  {archive_name}")

    if args.check_only:
        print("✅ Check completed successfully.")
        return 0

    dist_dir = REPO_ROOT / args.dist_dir
    dist_dir.mkdir(parents=True, exist_ok=True)
    binary_name = "agtoosa.exe" if os_name == "windows" else "agtoosa"
    binary_path = dist_dir / binary_name

    if not args.skip_build:
        spec_path = REPO_ROOT / "scripts" / "agtoosa.spec"
        if not spec_path.exists():
            print(f"❌ PyInstaller spec not found: {spec_path}")
            return 1
        binary_path = run_pyinstaller_build(spec_path, dist_dir)
    else:
        if not binary_path.exists():
            print(f"❌ Existing binary not found at {binary_path}. Run without --skip-build.")
            return 1

    archive_path, digest = create_release_archive(binary_path, dist_dir, archive_name)
    print(f"\n🎉 Package created successfully!")
    print(f"   • Archive:  {archive_path} ({archive_path.stat().st_size} bytes)")
    print(f"   • SHA-256:  {digest}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
