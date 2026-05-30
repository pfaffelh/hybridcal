"""ATHX (Hybrid Games) source plugin.

The /events page is Laravel + Inertia: the full future-events list is
embedded as JSON in `<div id="app" data-page="...">`. One HTTP call,
all 32 events with stable ULIDs, ISO country codes, and full venue data.
"""
from __future__ import annotations

import html as _html
import json
import re
import urllib.request
from datetime import date, datetime

from .. import SourceRecord, slugify

URL = "https://athxgames.com/events"
FORMAT_ID = "athx"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Venue-district → canonical city (where ATHX's venue.city is a district
# name like Ballsbridge/Laeken or a foreign-language spelling).
CITY_ALIAS = {
    "lisboa":      "Lisbon",
    "københavn":   "Copenhagen",
    "kobenhavn":   "Copenhagen",
}

# Country → IANA timezone for new-event YAMLs. Only countries ATHX
# currently visits are listed.
COUNTRY_TZ = {
    "AT": "Europe/Vienna",
    "BE": "Europe/Brussels",
    "CH": "Europe/Zurich",
    "DE": "Europe/Berlin",
    "DK": "Europe/Copenhagen",
    "ES": "Europe/Madrid",
    "FR": "Europe/Paris",
    "GB": "Europe/London",
    "IE": "Europe/Dublin",
    "IT": "Europe/Rome",
    "NL": "Europe/Amsterdam",
    "PT": "Europe/Lisbon",
    "US": "America/New_York",
}


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _parse_date(s: str) -> date | None:
    """ATHX uses 'DD Mon YYYY' (e.g. '30 May 2026')."""
    if not s:
        return None
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _city_from_name(name: str) -> str:
    """Names follow 'ATHX <CITY-IN-CAPS> <YEAR>' — extract the CITY.
    Returns empty string for non-canonical names like 'ATHX FINALS 2026'."""
    m = re.match(r"^ATHX\s+(.+?)\s+\d{4}\s*$", name.strip(), re.I)
    if not m:
        return ""
    title = m.group(1).strip()
    if title.lower() in {"finals"}:
        return ""
    return " ".join(w.capitalize() for w in title.split())


def fetch() -> list[SourceRecord]:
    body = _http_get(URL)
    m = re.search(r'<div id="app" data-page="([^"]+)"', body)
    if not m:
        raise SystemExit("athx: no Inertia data-page found — page layout changed?")
    page = json.loads(_html.unescape(m.group(1)))
    events = page.get("props", {}).get("future_events") or []

    records: list[SourceRecord] = []
    for e in events:
        eid = e.get("id") or ""
        if not eid:
            continue
        venue = e.get("venue") or {}
        country = ((e.get("country") or {}).get("code") or "").upper()
        date_start = _parse_date(e.get("start_date", ""))

        city = _city_from_name(e.get("name", ""))
        if not city:
            # Fallback for FINALS / unusual names: use venue.city.
            city = (venue.get("city") or "").strip()
        city = CITY_ALIAS.get(city.lower(), city)

        try:
            lat = float(venue.get("lat")) if venue.get("lat") else None
            lon = float(venue.get("lng")) if venue.get("lng") else None
        except (TypeError, ValueError):
            lat = lon = None

        records.append(SourceRecord(
            source_id=str(eid),
            format=FORMAT_ID,
            name=(e.get("name") or "").strip(),
            date_start=date_start,
            date_end=date_start,  # ATHX events are single-day
            city=city,
            country=country,
            venue=(venue.get("name") or "").strip() or None,
            timezone=COUNTRY_TZ.get(country, ""),
            lat=lat,
            lon=lon,
            url=f"https://athxgames.com/events/{eid}",
            categories=[],
            suggested_slug=(f"athx-{slugify(city)}-"
                            f"{date_start.strftime('%Y-%m') if date_start else 'tba'}"),
            is_main_brand=bool(country and date_start),
        ))
    return records
