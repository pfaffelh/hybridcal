#!/usr/bin/env python3
"""Build the HybridCal static site."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, date
from pathlib import Path

from hybridcal.loader import (
    load_events,
    load_formats,
    load_categories,
    load_site,
    load_regions,
    load_translations,
    validate_cross_references,
)
from hybridcal.renderer import render_site
from hybridcal.feeds import write_ics, write_rss


ROOT = Path(__file__).parent
DATA = ROOT / "data"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DIST = ROOT / "dist"


def last_data_update_date() -> date | None:
    """Date of the most recent commit that touched data/events/.

    Returns None in environments without git history (e.g. fresh tarball).
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", "data/events/"],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        )
        timestamp = result.stdout.strip()
        if not timestamp:
            return None
        return datetime.fromisoformat(timestamp).date()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def main() -> int:
    print("Loading data...")
    site = load_site(DATA)
    regions = load_regions(DATA)
    formats = load_formats(DATA)
    categories = load_categories(DATA)
    events = load_events(DATA)
    translations = load_translations(DATA)
    print(
        f"  {len(events)} events, {len(formats)} formats, "
        f"{len(regions)} regions, "
        f"{len(translations)} languages ({', '.join(translations.keys())})"
    )

    print("Validating cross-references...")
    errors = validate_cross_references(events, formats, categories)
    if errors:
        for err in errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        return 1
    print("  ok")

    last_update = last_data_update_date()
    if last_update:
        print(f"  last event data update: {last_update}")

    print("Rendering site...")
    render_site(
        events, formats, categories, translations, site, regions,
        DIST, TEMPLATES, STATIC,
        last_data_update=last_update,
    )

    print("Writing feeds...")
    write_ics(events, DIST / "feed.ics", site.url)
    write_rss(events, DIST / "feed.rss", site.url)

    print(f"Built to {DIST}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
