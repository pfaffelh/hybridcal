"""Deadly Dozen source plugin.

Fetches all live, non-cancelled future events from the Deadly Dozen
Supabase REST endpoint and groups Supabase rows into one SourceRecord per
(city, date_start) tuple — which is how we already model DD events
locally (one YAML per venue+date with multiple sub-categories).

Reads the anon key from env var HYBRIDCAL_DD_SUPABASE_ANON_KEY.
The key is a long JWT — see CLAUDE.md for how to harvest it from the
embed's XHR headers if it rotates.
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.parse
from collections import defaultdict
from datetime import date, datetime
from zoneinfo import available_timezones, ZoneInfo

from .. import SourceRecord, deaccent, slugify

SUPABASE_BASE = "https://xeltdycwgunxzjrzinxv.supabase.co/rest/v1/events"
ANON_KEY_ENV = "HYBRIDCAL_DD_SUPABASE_ANON_KEY"
FORMAT_ID = "deadly-dozen"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 hybridcal-reconciler"

# Hand-rolled country→timezone mapping for the countries DD actually visits.
# Reconciler only writes timezone for new YAMLs; existing YAMLs keep theirs.
COUNTRY_TZ = {
    "AT": "Europe/Vienna",
    "AU": "Australia/Sydney",
    "BE": "Europe/Brussels",
    "CH": "Europe/Zurich",
    "DE": "Europe/Berlin",
    "DK": "Europe/Copenhagen",
    "ES": "Europe/Madrid",
    "FR": "Europe/Paris",
    "GB": "Europe/London",
    "IE": "Europe/Dublin",
    "IT": "Europe/Rome",
    "MT": "Europe/Malta",
    "NL": "Europe/Amsterdam",
    "PL": "Europe/Warsaw",
    "PT": "Europe/Lisbon",
    "SE": "Europe/Stockholm",
    "ZA": "Africa/Johannesburg",
    "AE": "Asia/Dubai",
    "US": "America/New_York",
    "CA": "America/Toronto",
    "NZ": "Pacific/Auckland",
}


def _fetch_raw() -> list[dict]:
    key = os.environ.get(ANON_KEY_ENV)
    if not key:
        raise SystemExit(
            f"missing env var {ANON_KEY_ENV} — see CLAUDE.md "
            "(harvest the anon JWT from the embed's XHR headers)"
        )
    today_iso = date.today().isoformat()
    q = urllib.parse.urlencode({
        "select": "*",
        "is_live": "eq.true",
        "is_cancelled": "eq.false",
        "race_date": f"gte.{today_iso}",
        "order": "race_date.asc",
    })
    req = urllib.request.Request(
        f"{SUPABASE_BASE}?{q}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "User-Agent": UA,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _parse_date(s) -> date | None:
    if not s:
        return None
    s = str(s)
    # Supabase returns ISO date or full timestamp
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _row_city(row: dict) -> str:
    """Title-case the city. Supabase stores 'STRASBOURG' / 'NURNBURG'."""
    raw = (row.get("venue_city") or "").strip()
    if not raw:
        return ""
    # Title-case each whitespace-separated chunk, preserving hyphens.
    return " ".join(part.title() for part in raw.split())


def _row_country(row: dict) -> str:
    cc = (row.get("country_code") or "").strip().upper()
    return cc[:2] if cc else ""


def _row_url(row: dict) -> str:
    return (row.get("ticket_url") or "").strip()


def _row_id(row: dict) -> str:
    return str(row.get("id") or row.get("uuid") or "")


def fetch() -> list[SourceRecord]:
    """Return one SourceRecord per (city, date) group of Supabase rows."""
    rows = _fetch_raw()
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        d = _parse_date(row.get("race_date"))
        if d is None:
            continue
        city = _row_city(row)
        country = _row_country(row)
        if not city or not country:
            continue
        key = (deaccent(city).lower(), d, country)
        groups[key].append(row)

    records: list[SourceRecord] = []
    for (_city_norm, d, country), rs in sorted(groups.items()):
        # canonical row: prefer race_type=TRACK; else first by id
        rs_sorted = sorted(rs, key=lambda r: (r.get("race_type") != "TRACK", _row_id(r)))
        canon = rs_sorted[0]
        city = _row_city(canon)
        lat = canon.get("latitude")
        lon = canon.get("longitude")
        try:
            lat = float(lat) if lat is not None else None
            lon = float(lon) if lon is not None else None
        except (TypeError, ValueError):
            lat = lon = None
        url = _row_url(canon) or next((_row_url(r) for r in rs_sorted if _row_url(r)), "")
        tz = COUNTRY_TZ.get(country, "")
        records.append(SourceRecord(
            source_id=_row_id(canon),
            format=FORMAT_ID,
            name=f"Deadly Dozen {country}: {city}",
            date_start=d,
            date_end=d,
            city=city,
            country=country,
            venue=None,  # Supabase doesn't always carry a clean venue string
            timezone=tz,
            lat=lat,
            lon=lon,
            url=url,
            categories=[],  # filled in PR review; we don't auto-edit categories
            suggested_slug=f"deadly-dozen-{slugify(city)}-{d.strftime('%Y-%m')}",
        ))
    return records
