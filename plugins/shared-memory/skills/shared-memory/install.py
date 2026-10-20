#!/usr/bin/env python3
"""Run the bundled skill installer from a downloaded ZIP or Git checkout."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts'))
from install_skill import main

if __name__ == '__main__':
    sys.exit(main())
