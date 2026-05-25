#!/usr/bin/env python3
"""Validate event YAML files (run by CI on PRs)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from hybridcal.loader import (
    load_events,
    load_formats,
    load_categories,
    validate_cross_references,
)


def main() -> int:
    DATA = ROOT / "data"
    print("Validating data...")
    try:
        formats = load_formats(DATA)
        categories = load_categories(DATA)
        events = load_events(DATA)
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return 1

    errors = validate_cross_references(events, formats, categories)
    if errors:
        for err in errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        return 1

    print(f"  {len(events)} events valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
