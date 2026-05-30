"""Wild Hybrid source plugin.

Veranstalter: Wild Deer Events (UK), Buchungsbackend eventrac. Die
Listing-Seite https://www.wildhybrid.co.uk/calendars/sport-events/ ist
Next.js-SSR — kein __NEXT_DATA__, aber jeder /e/<slug>-<id>-Link steht
inline im HTML, und jede Detailseite hat einen schema.org-Event-Block
als <script type="application/ld+json"> mit startDate, endDate, name,
url, location.address (mit Postcode) und ggf. location.geo.

Jede Veranstaltung ist zweimal gelistet (als '-pairs-<id>' UND
'-solos-<id>'); wir wählen pro Location einen kanonischen Eintrag —
'-pairs-and-solos-' wenn vorhanden, sonst '-solos-', sonst '-pairs-'.

Koordinaten: location.geo ist nur auf der kombinierten Seite gefüllt.
Sonst Postcode aus der streetAddress per https://api.postcodes.io
geocoden (frei, kein Key).
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import date, datetime

from .. import SourceRecord, slugify

LISTING_URL = "https://www.wildhybrid.co.uk/calendars/sport-events/"
SITE = "https://www.wildhybrid.co.uk"
POSTCODES_API = "https://api.postcodes.io/postcodes/"
FORMAT_ID = "wild-hybrid"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# All Wild Hybrid events offer all four entry types.
DEFAULT_CATEGORIES = ["solo-rx", "solo-scaled", "pairs-rx", "pairs-scaled"]

# UK postcode regex (matches inside the address string)
_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}[0-9][A-Z0-9]?)\s*([0-9][A-Z]{2})\b")


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _list_canonical_paths() -> list[tuple[str, str]]:
    """Return [(path, eventrac_id)] — one canonical entry per location.
    Variant preference: pairs-and-solos > solos > pairs."""
    html_doc = _http_get(LISTING_URL)
    paths = sorted(set(re.findall(r"/e/[a-z0-9-]+", html_doc)))
    by_loc: dict[str, list[tuple[int, str, str]]] = {}
    for p in paths:
        m = re.match(r"^(.*?)-(\d+)$", p)
        if not m:
            continue
        stem, eid = m.group(1), m.group(2)
        if "-pairs-and-solos" in stem:
            loc = stem.replace("-pairs-and-solos", "")
            rank = 0
        elif "-solos" in stem:
            loc = stem.replace("-solos", "")
            rank = 1
        elif "-pairs" in stem:
            loc = stem.replace("-pairs", "")
            rank = 2
        else:
            loc = stem
            rank = 3
        by_loc.setdefault(loc, []).append((rank, p, eid))
    out: list[tuple[str, str]] = []
    for items in by_loc.values():
        items.sort()
        _, path, eid = items[0]
        out.append((path, eid))
    return out


def _parse_jsonld(html_doc: str) -> dict | None:
    for m in re.finditer(
            r'<script\s+type="application/ld\+json">(.*?)</script>',
            html_doc, re.S):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Event":
            return data
    return None


def _parse_iso(s) -> date | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


def _city_from_name(name: str) -> str:
    """'WILD HYBRID <CITY> - <VENUE> [PAIRS|SOLOS|...]' → '<City>'."""
    m = re.match(r"WILD\s+HYBRID\s+(.+?)\s+-\s+", name, re.I)
    if not m:
        return ""
    return " ".join(w.capitalize() for w in m.group(1).strip().split())


def _postcode_from_address(addr: str) -> str:
    m = _POSTCODE_RE.search(addr or "")
    if not m:
        return ""
    return f"{m.group(1)} {m.group(2)}"


# Simple in-memory geocode cache (per reconcile run only)
_GEO_CACHE: dict[str, tuple[float | None, float | None]] = {}


def _geocode_postcode(postcode: str) -> tuple[float | None, float | None]:
    if not postcode:
        return None, None
    if postcode in _GEO_CACHE:
        return _GEO_CACHE[postcode]
    try:
        body = _http_get(POSTCODES_API + urllib.parse.quote(postcode))
        data = json.loads(body)
        r = data.get("result") or {}
        lat = float(r["latitude"]) if r.get("latitude") is not None else None
        lon = float(r["longitude"]) if r.get("longitude") is not None else None
    except Exception:
        lat = lon = None
    _GEO_CACHE[postcode] = (lat, lon)
    return lat, lon


# urllib.parse needed for _geocode_postcode
import urllib.parse  # noqa: E402  (late import keeps top tidy)


def fetch() -> list[SourceRecord]:
    out: list[SourceRecord] = []
    for path, eid in _list_canonical_paths():
        try:
            html_doc = _http_get(SITE + path)
        except Exception:
            continue
        data = _parse_jsonld(html_doc)
        if not data:
            continue

        date_start = _parse_iso(data.get("startDate"))
        date_end = _parse_iso(data.get("endDate")) or date_start
        name_raw = (data.get("name") or "").strip()
        url = (data.get("url") or (SITE + path)).strip()
        city = _city_from_name(name_raw)

        loc = data.get("location") or {}
        addr = loc.get("address") or {}
        venue_name = (loc.get("name") or "").strip() or None
        street = addr.get("streetAddress") or addr.get("name") or ""
        country_obj = addr.get("addressCountry") or {}
        if isinstance(country_obj, dict):
            country = (country_obj.get("name") or "").upper()
        else:
            country = str(country_obj).upper()

        geo = loc.get("geo") or {}
        try:
            lat = float(geo.get("latitude")) if geo.get("latitude") else None
            lon = float(geo.get("longitude")) if geo.get("longitude") else None
        except (TypeError, ValueError):
            lat = lon = None
        if lat is None or lon is None:
            lat, lon = _geocode_postcode(_postcode_from_address(street))

        # Strip 'SOLOS' / 'PAIRS' / 'PAIRS AND SOLOS' from the display name.
        clean_name = re.sub(
            r"\s+(SOLOS|PAIRS|PAIRS\s+AND\s+SOLOS)\s*$",
            "", name_raw, flags=re.I).strip()
        clean_name = " ".join(w.capitalize() for w in clean_name.split())
        clean_name = clean_name.replace(" Hybrid ", " Hybrid ")  # noop, kept for clarity

        out.append(SourceRecord(
            source_id=str(eid),
            format=FORMAT_ID,
            name=clean_name or name_raw,
            date_start=date_start,
            date_end=date_end,
            city=city,
            country=country,
            venue=venue_name,
            timezone="Europe/London",  # Wild Hybrid is UK-only
            lat=lat,
            lon=lon,
            url=url,
            categories=DEFAULT_CATEGORIES.copy(),
            suggested_slug=(f"wild-hybrid-{slugify(city)}-"
                            f"{date_start.strftime('%Y-%m') if date_start else 'tba'}"),
            is_main_brand=bool(country and date_start),
        ))
    return out
