"""Package entrypoint allowing execution via `python3 -m agtoosa`."""

import sys
from agtoosa.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
