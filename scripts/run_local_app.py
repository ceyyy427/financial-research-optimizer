#!/usr/bin/env python3
"""Launch the Finahinking offline-first local application."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finahinking.local_app import main

if __name__ == "__main__":
    main()
