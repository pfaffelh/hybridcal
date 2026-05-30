"""DEKA / Spartan source plugin.

Wraps the public Spartan API at api2.spartan.com (discovered by sniffing
XHRs on deka.fit/en/race/find-race) and returns one SourceRecord per
upcoming race. source_id = the Spartan race id (numeric, string-encoded).

The two-stage manual-review importer in scripts/add_deka_2026.py still
exists for ad-hoc bulk imports. The reconciler uses this plugin instead
because it needs structured records, not a candidates file.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import date

from .. import SourceRecord, slugify

API_BASE = "https://api2.spartan.com/api/races/upcoming_past_planned"
IDENTIFIERS = ["dekafit", "dekafitultra", "dekastrong", "dekamile", "dekaroadshow"]
FORMAT_ID = "deka"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 hybridcal-reconciler"

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

CATEGORY_MAP = {
    "dekafit": ["deka-fit-singles", "deka-fit-pairs"],
    "dekafitultra": [],
    "dekastrong": ["deka-strong-singles"],
    "dekamile": ["deka-mile"],
    "dekaroadshow": [],
}


def _fetch_raw() -> list[dict]:
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
    req = urllib.request.Request(f"{API_BASE}?{qs}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    return data.get("upcoming", [])


def _parse_date(s) -> date | None:
    if not s:
        return None
    s = str(s)
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _normalise(race: dict) -> SourceRecord | None:
    venue = race.get("venue") or {}
    sub_events = race.get("events") or []
    if not sub_events:
        return None

    country = COUNTRY_TO_ISO.get((venue.get("country") or "").strip(), "")
    city = (venue.get("city") or "").strip()
    timezone = (sub_events[0].get("timezone") or "").strip()

    start = _parse_date(race.get("start_date"))
    end = _parse_date(race.get("end_date")) or start

    # Slug stem prefers city; fallback to first word of venue name.
    stem = slugify(city)
    if not stem and venue.get("name"):
        first = re.split(r"[\s,]+", venue["name"].strip())[0]
        stem = slugify(first)
    if not stem:
        stem = str(race.get("id"))

    year_month = start.strftime("%Y-%m") if start else ""
    slug = f"deka-{stem}-{year_month}" if year_month else f"deka-{stem}"

    cat_ids: list[str] = []
    for ev in sub_events:
        cat = (ev.get("category") or {}).get("category_identifier") or ""
        for hc in CATEGORY_MAP.get(cat, []):
            if hc not in cat_ids:
                cat_ids.append(hc)

    url = (sub_events[0].get("registration_url_1")
           or race.get("registration_url_3")
           or f"https://www.spartan.com/en/race/detail/{race['id']}/overview")

    try:
        lat = float(venue["latitude"]) if venue.get("latitude") else None
        lon = float(venue["longitude"]) if venue.get("longitude") else None
    except (TypeError, ValueError):
        lat = lon = None

    return SourceRecord(
        source_id=str(race.get("id") or ""),
        format=FORMAT_ID,
        name=race.get("marketing_name") or race.get("name") or city,
        date_start=start,
        date_end=end,
        city=city,
        country=country,
        venue=(venue.get("name") or "").strip() or None,
        timezone=timezone,
        lat=lat,
        lon=lon,
        url=url,
        categories=cat_ids,
        suggested_slug=slug,
    )


def fetch() -> list[SourceRecord]:
    return [r for r in (_normalise(x) for x in _fetch_raw()) if r and r.source_id]
