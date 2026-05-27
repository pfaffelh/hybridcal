#!/usr/bin/env python3
"""Two-stage DEKA event importer with manual review.

Stage 1 (default):
  python scripts/add_deka_2026.py
  → fetches upcoming DEKA events from the public Spartan API and writes
    scripts/_deka_candidates.yml with one block per event. Each block has
    `include: false` by default. Review the file by hand and flip the
    flag to `true` for the events you want in the calendar.

Stage 2:
  python scripts/add_deka_2026.py --apply
  → reads scripts/_deka_candidates.yml and writes one YAML file per
    `include: true` entry into data/events/<year>/. Skips entries whose
    slug already exists. Re-running stage 1 will not clobber include
    flags you've already set (existing flags are preserved).

API: api2.spartan.com/api/races/upcoming_past_planned (discovered by
sniffing XHRs on https://www.deka.fit/en/race/find-race).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).parent.parent
CANDIDATES = ROOT / "scripts" / "_deka_candidates.yml"
EVENTS_ROOT = ROOT / "data" / "events"

API_BASE = "https://api2.spartan.com/api/races/upcoming_past_planned"
IDENTIFIERS = ["dekafit", "dekafitultra", "dekastrong",
               "dekamile", "dekaroadshow"]

# Spartan API returns free-text country names. Map to ISO-3166-1 alpha-2.
COUNTRY_TO_ISO = {
    "USA": "US", "United States": "US", "United States of America": "US",
    "Canada": "CA", "Mexico": "MX",
    "UK": "GB", "United Kingdom": "GB",
    "Ireland": "IE",
    "Germany": "DE", "France": "FR", "Spain": "ES", "Italy": "IT",
    "Portugal": "PT", "Belgium": "BE", "Netherlands": "NL",
    "Switzerland": "CH", "Austria": "AT", "Czechia": "CZ",
    "Czech Republic": "CZ", "Poland": "PL", "Hungary": "HU",
    "Greece": "GR", "Sweden": "SE", "Norway": "NO", "Denmark": "DK",
    "Finland": "FI", "Iceland": "IS",
    "Australia": "AU", "New Zealand": "NZ",
    "Japan": "JP", "South Korea": "KR", "Korea": "KR",
    "China": "CN", "Hong Kong": "HK", "Taiwan": "TW",
    "Singapore": "SG", "Malaysia": "MY", "Thailand": "TH",
    "Philippines": "PH", "Indonesia": "ID", "Vietnam": "VN",
    "India": "IN",
    "UAE": "AE", "United Arab Emirates": "AE",
    "Saudi Arabia": "SA", "Israel": "IL",
    "Brazil": "BR", "Argentina": "AR", "Chile": "CL", "Colombia": "CO",
    "South Africa": "ZA",
}

# Map Spartan category_identifier → HybridCal categories.yml IDs.
CATEGORY_MAP = {
    "dekafit": ["deka-fit-singles", "deka-fit-pairs"],
    "dekafitultra": [],   # no matching cat yet; user can fill in
    "dekastrong": ["deka-strong-singles"],
    "dekamile": ["deka-mile"],
    "dekaroadshow": [],   # affiliate-gym roadshow; no canonical category
}


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def http_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def disambiguate_slugs(records: list[dict]) -> None:
    """If multiple records share the same slug, append `-DD` (start day)
    to each colliding entry so each event ends up with a unique file."""
    from collections import Counter
    counts = Counter(r["slug"] for r in records)
    for r in records:
        if counts[r["slug"]] > 1:
            day = r["date_start"][8:10] if len(r["date_start"]) >= 10 else "x"
            r["slug"] = f"{r['slug']}-{day}"


def fetch_races() -> list[dict]:
    qs = urllib.parse.urlencode(
        [
            ("new_api", "yes"),
            ("plimit", 0),
            ("ulimit", 500),
            ("prlimit", 0),
            ("units", "miles"),
            ("radius", 999999),
            ("country", ""),
        ]
        + [("identifiers[]", x) for x in IDENTIFIERS]
    )
    data = http_get(f"{API_BASE}?{qs}")
    return data.get("upcoming", [])


def normalise(race: dict) -> dict | None:
    """Turn one Spartan race entry into a HybridCal-shaped dict."""
    venue = race.get("venue") or {}
    sub_events = race.get("events") or []
    if not sub_events:
        return None

    country_raw = (venue.get("country") or "").strip()
    country = COUNTRY_TO_ISO.get(country_raw, "")
    city = (venue.get("city") or "").strip()
    timezone = (sub_events[0].get("timezone") or "").strip()

    start = race.get("start_date") or ""
    end = race.get("end_date") or start

    # Slug stem: prefer the API city; if missing, take the first word of
    # the venue name (e.g. "Manchester Convention Centre" → "manchester"),
    # then fall back to the Spartan race id.
    year_month = start[:7] if start else ""
    stem = slugify(city)
    if not stem and venue.get("name"):
        first = re.split(r"[\s,]+", venue["name"].strip())[0]
        stem = slugify(first)
    if not stem:
        stem = str(race.get("id"))

    slug = f"deka-{stem}-{year_month}" if year_month else f"deka-{stem}"

    # Collect distinct category identifiers across sub-events and map them.
    cat_ids = []
    seen_id = set()
    seen_sub = set()
    sub_summary = []
    for ev in sub_events:
        cat = (ev.get("category") or {}).get("category_identifier") or ""
        if cat and cat not in seen_sub:
            seen_sub.add(cat)
            sub_summary.append(cat)
        for hc in CATEGORY_MAP.get(cat, []):
            if hc not in seen_id:
                seen_id.add(hc)
                cat_ids.append(hc)

    # Public URL: prefer the first sub-event's registration link.
    url = (sub_events[0].get("registration_url_1")
           or race.get("registration_url_3")
           or f"https://www.spartan.com/en/race/detail/{race['id']}/overview")

    return {
        "slug": slug,
        "name": race.get("marketing_name") or race.get("name") or "",
        "format": "deka",
        "date_start": start,
        "date_end": end,
        "city": city,
        "country_raw": country_raw,
        "country": country,
        "venue": (venue.get("name") or "").strip(),
        "timezone": timezone,
        "lat": float(venue["latitude"]) if venue.get("latitude") else None,
        "lon": float(venue["longitude"]) if venue.get("longitude") else None,
        "url": url,
        "categories": cat_ids,
        "sub_events": sub_summary,
        "spartan_id": race.get("id"),
    }


def yaml_quote(s) -> str:
    if s is None:
        return '""'
    s = str(s)
    if any(ch in s for ch in ':#"\'\n') or s.strip() != s or not s:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def write_candidates(records: list[dict]) -> None:
    """Write candidates with `include:` flags, preserving any existing flags."""
    existing_flags = {}
    if CANDIDATES.exists():
        for block in re.split(r"\n(?=- )", CANDIDATES.read_text()):
            slug_m = re.search(r"slug:\s*(\S+)", block)
            inc_m = re.search(r"^  include:\s*(true|false)", block, re.M)
            if slug_m and inc_m:
                existing_flags[slug_m.group(1)] = inc_m.group(1) == "true"

    lines = [
        "# DEKA event candidates — review and flip `include: true` for events to keep.",
        "# Then run: python scripts/add_deka_2026.py --apply",
        "# Re-running the scraper preserves existing include flags.",
        "",
    ]
    for r in records:
        inc = "true" if existing_flags.get(r["slug"], False) else "false"
        sub = ", ".join(r["sub_events"]) or "—"
        lines.append(f"- slug: {r['slug']}")
        lines.append(f"  include: {inc}")
        lines.append(f"  name: {yaml_quote(r['name'])}")
        lines.append(f"  date_start: {r['date_start']}")
        lines.append(f"  date_end: {r['date_end']}")
        lines.append(f"  city: {yaml_quote(r['city'])}")
        country_field = r["country"] or f"??  # raw: {r['country_raw']!r}"
        lines.append(f"  country: {country_field}")
        if r["venue"]:
            lines.append(f"  venue: {yaml_quote(r['venue'])}")
        lines.append(f"  timezone: {r['timezone']}")
        if r["lat"] is not None:
            lines.append(f"  lat: {r['lat']}")
            lines.append(f"  lon: {r['lon']}")
        lines.append(f"  url: {yaml_quote(r['url'])}")
        if r["categories"]:
            lines.append("  categories:")
            for c in r["categories"]:
                lines.append(f"    - {c}")
        else:
            lines.append("  categories: []")
        lines.append(f"  # sub-events: {sub}")
        lines.append(f"  # spartan_id: {r['spartan_id']}")
        lines.append("")

    CANDIDATES.write_text("\n".join(lines))


def parse_candidate_block(block: str) -> dict | None:
    """Parse one `- slug: ...` block back into a dict (best-effort YAML)."""
    fields = {}
    cats = []
    in_cats = False
    for line in block.splitlines():
        if line.startswith("  categories:"):
            in_cats = True
            continue
        if in_cats:
            m = re.match(r"\s+-\s+(\S+)", line)
            if m:
                cats.append(m.group(1))
                continue
            in_cats = False
        m = re.match(r"-?\s*([a-z_]+):\s*(.*?)(\s+#.*)?$", line)
        if m:
            k = m.group(1)
            v = m.group(2).strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
            fields[k] = v
    fields["categories"] = cats
    return fields if fields.get("slug") else None


def write_event_yaml(c: dict) -> Path:
    year = c["date_start"][:4]
    out = EVENTS_ROOT / year / f"{c['slug']}.yml"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return out  # idempotent

    lines = [
        f"slug: {c['slug']}",
        f"name: {yaml_quote(c['name'])}",
        "format: deka",
        f"date_start: {c['date_start']}",
        f"date_end: {c['date_end']}",
        "location:",
        f"  city: {yaml_quote(c['city'])}",
        f'  country: "{c["country"]}"',
    ]
    if c.get("venue"):
        lines.append(f"  venue: {yaml_quote(c['venue'])}")
    lines.append(f"  timezone: {c['timezone']}")
    if c.get("lat"):
        lines.append(f"  lat: {c['lat']}")
        lines.append(f"  lon: {c['lon']}")
    lines.append(f"url: {yaml_quote(c['url'])}")
    lines.append("status: confirmed")
    lines.append("source: scraped")
    if c.get("categories"):
        lines.append("categories:")
        for cat in c["categories"]:
            lines.append(f"  - {cat}")
    else:
        lines.append("categories: []")
    out.write_text("\n".join(lines) + "\n")
    return out


def cmd_fetch() -> int:
    print(f"Fetching DEKA races from {API_BASE} …")
    races = fetch_races()
    records = [r for r in (normalise(x) for x in races) if r]
    disambiguate_slugs(records)
    print(f"  {len(records)} candidates")

    missing_iso = [r for r in records if not r["country"]]
    if missing_iso:
        print("  ⚠ unmapped country codes (set manually in candidates):")
        for r in missing_iso:
            print(f"    {r['country_raw']!r}  →  {r['slug']}")

    write_candidates(records)
    print(f"Wrote {CANDIDATES.relative_to(ROOT)}")
    print("Review the file, set `include: true` per event, then run:")
    print("  python scripts/add_deka_2026.py --apply")
    return 0


def cmd_apply() -> int:
    if not CANDIDATES.exists():
        print(f"No candidates file at {CANDIDATES}; run without --apply first.",
              file=sys.stderr)
        return 1

    blocks = re.split(r"\n(?=- slug:)", CANDIDATES.read_text())
    written, skipped, missing = 0, 0, 0
    for block in blocks:
        if "slug:" not in block:
            continue
        c = parse_candidate_block(block)
        if not c:
            continue
        if c.get("include") != "true":
            skipped += 1
            continue
        if not c.get("country") or c["country"] == "??":
            print(f"  skip {c['slug']}: country code missing")
            missing += 1
            continue
        path = write_event_yaml(c)
        print(f"  → {path.relative_to(ROOT)}")
        written += 1
    print(f"{written} written, {skipped} excluded, {missing} missing country.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="write event YAMLs for include:true entries")
    args = ap.parse_args()
    return cmd_apply() if args.apply else cmd_fetch()


if __name__ == "__main__":
    sys.exit(main())
