#!/usr/bin/env python3
"""Entry point the skill calls. Wires ``src/`` onto the path so a fresh clone
runs without a ``pip install``.

    python scripts/gatekeeper_check.py <resources.json> audit
    python scripts/gatekeeper_check.py <resources.json> whatif <policy-name>
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from gatekeeper_guard.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
