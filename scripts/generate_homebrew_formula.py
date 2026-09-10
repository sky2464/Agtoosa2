#!/usr/bin/env python3
"""Generate or update Homebrew formula with release checksums."""

import argparse
from pathlib import Path
import re
import sys
from typing import Dict, Optional

FORMULA_TEMPLATE = """# typed: false
# frozen_string_literal: true

class Agtoosa < Formula
  desc "Unified Graph-Native Engineering Operating System"
  homepage "https://github.com/sky2464/Agtoosa2"
  version "{version}"
  license "MIT"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/sky2464/Agtoosa2/releases/download/v#{{version}}/agtoosa-v#{{version}}-darwin-arm64.tar.gz"
      sha256 "{darwin_arm64_sha}"
    else
      url "https://github.com/sky2464/Agtoosa2/releases/download/v#{{version}}/agtoosa-v#{{version}}-darwin-x86_64.tar.gz"
      sha256 "{darwin_x86_64_sha}"
    end
  end

  on_linux do
    if Hardware::CPU.intel?
      url "https://github.com/sky2464/Agtoosa2/releases/download/v#{{version}}/agtoosa-v#{{version}}-linux-x86_64.tar.gz"
      sha256 "{linux_x86_64_sha}"
    end
  end

  def install
    bin.install "agtoosa"
  end

  test do
    assert_match "Agtoosa2", shell_output("#{{bin}}/agtoosa version")
  end
end
"""


def parse_checksums_from_dir(dist_dir: Path) -> Dict[str, str]:
    """Scan dist directory for *.sha256 files and extract platform hashes."""
    checksums = {}
    for sha_file in dist_dir.glob("*.sha256"):
        content = sha_file.read_text(encoding="utf-8").strip()
        parts = content.split()
        if not parts:
            continue
        h = parts[0]
        fname = sha_file.stem  # e.g. agtoosa-v0.2.1-darwin-arm64.tar
        if "darwin-arm64" in fname:
            checksums["darwin_arm64"] = h
        elif "darwin-x86_64" in fname:
            checksums["darwin_x86_64"] = h
        elif "linux-x86_64" in fname:
            checksums["linux_x86_64"] = h
    return checksums


def generate_formula(
    version: str,
    darwin_arm64_sha: str = "PLACEHOLDER_DARWIN_ARM64_SHA256",
    darwin_x86_64_sha: str = "PLACEHOLDER_DARWIN_X86_64_SHA256",
    linux_x86_64_sha: str = "PLACEHOLDER_LINUX_X86_64_SHA256"
) -> str:
    """Render Ruby Homebrew formula content."""
    clean_version = version.lstrip("v")
    return FORMULA_TEMPLATE.format(
        version=clean_version,
        darwin_arm64_sha=darwin_arm64_sha,
        darwin_x86_64_sha=darwin_x86_64_sha,
        linux_x86_64_sha=linux_x86_64_sha,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Homebrew formula for Agtoosa")
    parser.add_argument("--version", type=str, default="0.2.1", help="Target release version")
    parser.add_argument("--output", type=str, default="Formula/agtoosa.rb", help="Output formula file")
    parser.add_argument("--dist-dir", type=str, help="Directory containing .sha256 files to parse")
    parser.add_argument("--darwin-arm64-sha", type=str, default="PLACEHOLDER_DARWIN_ARM64_SHA256")
    parser.add_argument("--darwin-x86-sha", type=str, default="PLACEHOLDER_DARWIN_X86_64_SHA256")
    parser.add_argument("--linux-x86-sha", type=str, default="PLACEHOLDER_LINUX_X86_64_SHA256")

    args = parser.parse_args()

    arm64_sha = args.darwin_arm64_sha
    x86_sha = args.darwin_x86_sha
    linux_sha = args.linux_x86_sha

    if args.dist_dir:
        dpath = Path(args.dist_dir)
        if dpath.is_dir():
            extracted = parse_checksums_from_dir(dpath)
            arm64_sha = extracted.get("darwin_arm64", arm64_sha)
            x86_sha = extracted.get("darwin_x86_64", x86_sha)
            linux_sha = extracted.get("linux_x86_64", linux_sha)

    formula_str = generate_formula(
        version=args.version,
        darwin_arm64_sha=arm64_sha,
        darwin_x86_64_sha=x86_sha,
        linux_x86_64_sha=linux_sha
    )

    out_p = Path(args.output)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(formula_str, encoding="utf-8")
    print(f"🍺 Homebrew formula written to {out_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
