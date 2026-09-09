"""Package entrypoint allowing execution via `python3 -m agtoosa` or direct script execution."""

import sys
from pathlib import Path

# Python version guard
if sys.version_info < (3, 11):
    sys.exit(f"Error: Agtoosa2 requires Python 3.11 or newer (currently running on Python {sys.version.split()[0]}).")

# Ensure repository root is on sys.path if run directly as a script
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agtoosa.cli.main import main

if __name__ == "__main__":
    # If invoked directly with no CLI arguments, default to showing help
    argv = sys.argv[1:] if len(sys.argv) > 1 else ["--help"]
    sys.exit(main(argv))
