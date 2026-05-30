"""One-off bootstrap: assign source_id to existing YAMLs by matching them
against the source plugin's current output.

Usage:
    .venv/bin/python -m scripts.reconcile.bootstrap deadly-dozen [--dry-run]
    .venv/bin/python -m scripts.reconcile.bootstrap deka [--dry-run]

Matching is (deaccent(city), date_start ±2 days) restricted to events
without an existing source_id. Reports unmatched and ambiguous cases for
the human reviewer; it never overwrites an existing source_id and never
touches past events.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from datetime import date, timedelta

from . import (LocalEvent, deaccent, load_local_events, normalise_city,
                update_yaml_field)

FMT_PLUGIN = {
    "deadly-dozen": "scripts.reconcile.sources.deadly_dozen",
    "deka":         "scripts.reconcile.sources.deka",
    "hyrox":        "scripts.reconcile.sources.hyrox",
}


def _match(local: LocalEvent, records):
    """Return source records matching local by (city, date±2). If several
    rows match, only the closest-date ones are returned — exact-date hits
    beat ±1/±2 hits, so two events in the same city on consecutive days
    don't end up ambiguous.

    For TBA events (date_start is None on both sides) we match on city
    alone — there's nothing else to compare."""
    city_n = normalise_city(local.city or "")
    if not city_n:
        return []
    if local.date_start is None:
        return [r for r in records
                if r.date_start is None
                and normalise_city(r.city or "") == city_n]
    hits = []
    for r in records:
        if r.date_start is None:
            continue
        delta = abs((r.date_start - local.date_start).days)
        if delta > 2:
            continue
        if normalise_city(r.city or "") != city_n:
            continue
        hits.append((delta, r))
    if not hits:
        return []
    best = min(d for d, _ in hits)
    return [r for d, r in hits if d == best]


def _match_relaxed(local: LocalEvent, records):
    """Fallback: same country + same month (for venue-as-city cases like
    Lee Valley = London). Used only when the strict match found 0."""
    if local.date_start is None:
        return []
    country = (local.data.get("location") or {}).get("country", "")
    if not country:
        return []
    ym = (local.date_start.year, local.date_start.month)
    return [r for r in records
            if r.date_start
            and r.country == country
            and (r.date_start.year, r.date_start.month) == ym]


def run(fmt: str, dry_run: bool) -> int:
    mod_name = FMT_PLUGIN.get(fmt)
    if not mod_name:
        print(f"unknown format: {fmt}", file=sys.stderr)
        return 2
    mod = importlib.import_module(mod_name)
    records = mod.fetch()
    print(f"[{fmt}] source delivered {len(records)} records")

    locals_ = [le for le in load_local_events(fmt) if le.is_future]
    print(f"[{fmt}] {len(locals_)} local future events")

    assigned = 0
    skipped_has_id = 0
    unmatched: list[LocalEvent] = []
    ambiguous: list[tuple[LocalEvent, list]] = []
    relaxed_used: list[tuple[LocalEvent, list]] = []

    for le in locals_:
        if le.source_id:
            skipped_has_id += 1
            continue
        hits = _match(le, records)
        if not hits:
            hits = _match_relaxed(le, records)
            if hits:
                relaxed_used.append((le, hits))
        if len(hits) == 1:
            sid = hits[0].source_id
            if dry_run:
                print(f"  WOULD ASSIGN  {le.path.name:60s} → {sid}")
            else:
                update_yaml_field(le.path, "source_id", sid)
                print(f"  ASSIGNED      {le.path.name:60s} → {sid}")
            assigned += 1
        elif len(hits) == 0:
            unmatched.append(le)
        else:
            ambiguous.append((le, hits))

    # Inverse: which source records didn't bind to any local event?
    # In dry-run we use the would-be-assigned set; in apply mode we re-read
    # the YAMLs so freshly-written source_ids are picked up.
    assigned_ids: set[str] = set()
    if dry_run:
        for le in locals_:
            if le.source_id:
                assigned_ids.add(le.source_id)
        for le, _ in []:  # placeholder if we ever want to skip ambiguous
            pass
        # also count the bootstrap's own assignments (dry-run path)
        for le in locals_:
            if le.source_id:
                continue
            hits = _match(le, records)
            if not hits:
                hits = _match_relaxed(le, records)
            if len(hits) == 1:
                assigned_ids.add(hits[0].source_id)
    else:
        for le in load_local_events(fmt):
            if le.source_id:
                assigned_ids.add(le.source_id)
    unbound_sources = [r for r in records if r.source_id not in assigned_ids]

    print()
    print(f"[{fmt}] summary")
    print(f"  assigned      : {assigned}")
    print(f"  already-tagged: {skipped_has_id}")
    print(f"  unmatched     : {len(unmatched)}")
    print(f"  ambiguous     : {len(ambiguous)}")
    print(f"  relaxed-match : {len(relaxed_used)} (used country+month fallback)")
    print(f"  unbound source records (probably new events): {len(unbound_sources)}")

    if unmatched:
        print("\nunmatched local events (no source row found):")
        for le in unmatched:
            print(f"  - {le.path.name}  (city={le.city!r}, date={le.date_start})")
    if ambiguous:
        print("\nambiguous local events (multiple source rows matched):")
        for le, hits in ambiguous:
            print(f"  - {le.path.name}: matched {len(hits)} source rows")
            for r in hits:
                print(f"      · id={r.source_id} {r.city} {r.date_start} {r.url}")
    if relaxed_used:
        print("\nrelaxed matches (country+month — please double-check):")
        for le, _ in relaxed_used:
            print(f"  - {le.path.name}  (city={le.city!r}, date={le.date_start})")
    if unbound_sources:
        print("\nunbound source records (will become new event YAMLs in the next reconciler run):")
        for r in unbound_sources:
            print(f"  - id={r.source_id}  {r.city} {r.country} {r.date_start}  {r.url}")

    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("format", choices=sorted(FMT_PLUGIN.keys()))
    ap.add_argument("--dry-run", action="store_true",
                    help="do not write YAMLs, just report what would happen")
    args = ap.parse_args()
    sys.exit(run(args.format, args.dry_run))


if __name__ == "__main__":
    main()
