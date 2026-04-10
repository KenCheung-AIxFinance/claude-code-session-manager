"""Entry point for ccsm CLI."""

import sys
from ccsm.cli.commands import main

if __name__ == "__main__":
    sys.exit(main())