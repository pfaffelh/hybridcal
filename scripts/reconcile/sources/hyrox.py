"""HYROX source plugin.

No public JSON API — the find-my-race page (WordPress) renders all events
server-side. Every event card is an <article> with data-id (= WP post ID
→ stable source_id), the H2 link (= event URL), and discrete date spans.
Parsing the HTML is robust and avoids the Playwright/Vercel-checkpoint
dance.

Country isn't exposed at the card level (only continent), so for events
we don't know yet we open the event page and read its `en_event_address`
custom field, then geocode that via Nominatim to get the ISO country and
coordinates. The card's `continent-*` class validates the geocode: an
address without a country ("Metropolitan Expo, Athens International
Airport") otherwise resolves to Athens, Georgia.

Detail pages are only fetched for source_ids we don't have a YAML for —
existing events are kept in sync from the card alone (date/url), and
their curated location fields are never overwritten by the reconciler.
"""
from __future__ import annotations

import html as htmlmod
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date

from .. import SourceRecord, load_local_events, slugify

URL = "https://hyrox.com/find-my-race/"
FORMAT_ID = "hyrox"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# English month abbreviation → number. HYROX renders "22. May. 2026".
_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Sept": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

# URL-slug → our canonical city. Used when the source spelling differs
# from ours (Gent/Ghent, Tenerife/Santa Cruz de Tenerife) or when the
# slug carries a venue the city name shouldn't ('paris-grand-palais').
_CITY_ALIAS = {
    "gent": "Ghent",
    "tenerife": "Santa Cruz de Tenerife",
    "paris-grand-palais": "Paris",
}

# Matches an optional sponsor prefix of up to three tokens ('puma-',
# 'virgin-active-', 'all-inclusive-fitness-', 'factor_-') followed by
# 'hyrox-' and an optional 'youngstars-' / 'world-championships-'
# segment. Stripped before city extraction. Non-greedy so the shortest
# prefix that still leaves a literal 'hyrox-' wins.
_PREFIX_RE = re.compile(
    r"^(?:[a-z0-9_]+-){0,3}?hyrox-(?:youngstars-|world-championships-|championships-)?"
)

# Nominatim returns country_code 'cn' for Hong Kong addresses; ISO-3166-1
# alpha-2 (what our Location model wants) is HK.
_CC_FIX = {"Hong Kong": "HK"}

# Continent class on the card → plausible bbox (lat_min, lat_max,
# lon_min, lon_max). Used to reject a geocode that landed on the wrong
# continent, which is what happens for addresses that omit the country.
# Boxes are deliberately generous; they only have to separate the five
# HYROX continent buckets from each other.
_CONTINENT_BBOX = {
    "europe":        (27.0, 72.0, -32.0, 45.0),   # incl. Canary Islands
    "north-america": (7.0, 84.0, -170.0, -50.0),
    "south-america": (-56.0, 13.0, -82.0, -34.0),
    "africa":        (-35.0, 38.0, -26.0, 52.0),
    "asia-pacific":  (-50.0, 60.0, 25.0, 180.0),
}

# ISO country → IANA timezone, for countries with a single zone.
# timezone is a required field on our Location model, so an event whose
# zone we can't determine is not auto-created (is_main_brand=False).
_COUNTRY_TZ = {
    "AE": "Asia/Dubai",
    "AR": "America/Argentina/Buenos_Aires",
    "AT": "Europe/Vienna",
    "BE": "Europe/Brussels",
    "CH": "Europe/Zurich",
    "CN": "Asia/Shanghai",
    "CZ": "Europe/Prague",
    "DE": "Europe/Berlin",
    "DK": "Europe/Copenhagen",
    "EG": "Africa/Cairo",
    "ES": "Europe/Madrid",
    "FI": "Europe/Helsinki",
    "FR": "Europe/Paris",
    "GB": "Europe/London",
    "GR": "Europe/Athens",
    "HK": "Asia/Hong_Kong",
    "HU": "Europe/Budapest",
    "IE": "Europe/Dublin",
    "IN": "Asia/Kolkata",
    "IT": "Europe/Rome",
    "JP": "Asia/Tokyo",
    "KR": "Asia/Seoul",
    "LV": "Europe/Riga",
    "MY": "Asia/Kuala_Lumpur",
    "NL": "Europe/Amsterdam",
    "NO": "Europe/Oslo",
    "NZ": "Pacific/Auckland",
    "PL": "Europe/Warsaw",
    "PT": "Europe/Lisbon",
    "SE": "Europe/Stockholm",
    "SG": "Asia/Singapore",
    "TH": "Asia/Bangkok",
    "TR": "Europe/Istanbul",
    "TW": "Asia/Taipei",
    "ZA": "Africa/Johannesburg",
}

# Countries spanning several zones need the city to pin the zone down.
# Keyed by our canonical city spelling (see _extract_city).
_CITY_TZ = {
    # United States
    "Atlanta": "America/New_York",
    "Chicago": "America/Chicago",
    "Dallas": "America/Chicago",
    "Houston": "America/Chicago",
    "Las Vegas": "America/Los_Angeles",
    "Los Angeles": "America/Los_Angeles",
    "Miami": "America/New_York",
    "Miami Beach": "America/New_York",
    "New York": "America/New_York",
    "Phoenix": "America/Phoenix",
    "Portland": "America/Los_Angeles",
    "San Diego": "America/Los_Angeles",
    "San Francisco": "America/Los_Angeles",
    "Salt Lake City": "America/Denver",
    "Seattle": "America/Los_Angeles",
    "Washington D C": "America/New_York",
    # Canada
    "Ottawa": "America/Toronto",
    "Toronto": "America/Toronto",
    "Vancouver": "America/Vancouver",
    # Mexico
    "Cancun": "America/Cancun",
    "Guadalajara": "America/Mexico_City",
    "Monterrey": "America/Monterrey",
    "Mexico City": "America/Mexico_City",
    # Brazil
    "Sao Paulo": "America/Sao_Paulo",
    "Rio De Janeiro": "America/Sao_Paulo",
    # Australia
    "Brisbane": "Australia/Brisbane",
    "Melbourne": "Australia/Melbourne",
    "Perth": "Australia/Perth",
    "Sydney": "Australia/Sydney",
    # Spain — mainland is Europe/Madrid, the Canaries are not.
    "Santa Cruz de Tenerife": "Atlantic/Canary",
}

# Trailing season/instance markers: -25-26, -s26-27, -2, -2026
_SEASON_RE = re.compile(r"-(?:s?\d{2}-\d{2}|20\d{2}|\d+)$")

# Trailing venue tokens we drop so the city remains clean.
_VENUE_SUFFIXES = ("-arena", "-excel", "-convention-center", "-event-center")


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _parse_date(s: str) -> date | None:
    """Parse 'DD. Mon. YYYY' → date."""
    m = re.match(r"(\d{1,2})\.\s*([A-Za-z]+)\.?\s*(\d{4})", s.strip())
    if not m:
        return None
    day = int(m.group(1))
    mon = _MONTHS.get(m.group(2).title())
    year = int(m.group(3))
    if not mon:
        return None
    try:
        return date(year, mon, day)
    except ValueError:
        return None


def _extract_city(event_url: str, title: str = "") -> str:
    """Derive the city from the event URL slug. More robust than parsing
    the marketing title because slugs are normalised by WordPress:
      hyrox-salt-lake-city-26-27 → 'Salt Lake City'
      virgin-active-hyrox-cape-town-26-27 → 'Cape Town'
      hyrox-washington-d-c-26-27 → 'Washington D C'
      hyrox-london-excel → 'London' (venue suffix stripped)
      hyrox-bordeaux-s26-27 → 'Bordeaux' (s-prefixed season suffix)
      puma-hyrox-world-championships-stockholm → 'Stockholm'
      hyrox-gent → 'Ghent' (alias to our canonical spelling)

    For numeric slugs (the WP-numeric form, e.g. /event/30454/) the URL
    carries no city info — we fall back to the marketing title's last
    token after HYROX.
    """
    m = re.search(r"/event/([^/?#]+)", event_url)
    if not m:
        return _city_from_title(title)
    slug = m.group(1).strip("/").lower()
    if re.fullmatch(r"\d+", slug):
        return _city_from_title(title)
    slug = _PREFIX_RE.sub("", slug)
    slug = _SEASON_RE.sub("", slug)
    for venue in _VENUE_SUFFIXES:
        if slug.endswith(venue):
            slug = slug[:-len(venue)]
            break
    if not slug:
        return _city_from_title(title)
    alias = _CITY_ALIAS.get(slug)
    if alias:
        return alias
    return " ".join(p.capitalize() for p in slug.split("-"))


def _city_from_title(title: str) -> str:
    """Last word after 'HYROX' in the marketing title; only used when the
    URL slug yields no useful info (e.g. /event/30454/ for HYROX Sanya)."""
    if not title:
        return ""
    parts = re.split(r"\bHYROX\b", title, flags=re.IGNORECASE)
    tail = (parts[-1] if parts else title).strip()
    if not tail:
        return ""
    tail = re.sub(r"\s+(s?\d{2}-\d{2}|20\d{2}|\d+)\s*$", "", tail).strip()
    last = tail.split()[-1] if tail.split() else ""
    return last.title()


# Pre-compiled patterns
_ARTICLE_RE = re.compile(
    r'<article\s+class="w-grid-item[^"]*post-(\d+)\s+event[^"]*?'
    r'(continent-[a-z-]+)[^"]*?(type-[a-z]+)[^"]*"',
    re.S,
)
_H2_RE = re.compile(
    r'<h2[^>]*class="[^"]*post_title[^"]*"[^>]*>\s*'
    r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>',
    re.S,
)
_DATE1_RE = re.compile(
    r'event_date_1[^"]*"[^>]*>\s*<span[^>]*w-post-elm-value[^>]*>([^<]+)<',
    re.S,
)
_DATE3_RE = re.compile(
    r'event_date_3[^"]*"[^>]*>.*?<span[^>]*w-post-elm-value[^>]*>([^<]+)<',
    re.S,
)


_HTML_CACHE: str | None = None


def _get_html() -> str:
    """Module-level HTTP cache so the Adult and Youngstars plugins share
    a single fetch per reconciler run."""
    global _HTML_CACHE
    if _HTML_CACHE is None:
        _HTML_CACHE = _http_get(URL)
    return _HTML_CACHE


def parse_cards() -> list[dict]:
    """Parse find-my-race into raw card dicts (format-agnostic).

    Each dict has: post_id, type_class (type-adults / type-youngstars),
    continent (europe / north-america / asia-pacific / south-america /
    africa), event_url, title, date_start, date_end, city. Both Adult and
    Youngstars plugins consume this and filter by type_class.
    """
    html = _get_html()
    cards: list[dict] = []
    chunks = html.split("<article")
    for chunk in chunks[1:]:
        head_m = _ARTICLE_RE.match("<article" + chunk[:600])
        if not head_m:
            continue
        end = chunk.find("</article>")
        if end < 0:
            continue
        body = chunk[:end]

        h2_m = _H2_RE.search(body)
        if not h2_m:
            continue
        event_url = h2_m.group(1).strip()
        title = re.sub(r"<[^>]+>", "", h2_m.group(2)).strip()
        # WordPress curls the apostrophe in names like 'Masters&#8217; Union
        # HYROX Delhi'; the entity must not reach the YAML.
        title = re.sub(r"\s+", " ", htmlmod.unescape(title))

        d1_m = _DATE1_RE.search(body)
        d3_m = _DATE3_RE.search(body)
        date_start = _parse_date(d1_m.group(1)) if d1_m else None
        date_end = _parse_date(d3_m.group(1)) if d3_m else date_start

        cards.append({
            "post_id": head_m.group(1),
            "type_class": head_m.group(3),  # type-adults / type-youngstars
            "continent": head_m.group(2).replace("continent-", ""),
            "event_url": event_url,
            "title": title,
            "date_start": date_start,
            "date_end": date_end or date_start,
            "city": _extract_city(event_url, title),
        })
    return cards


# Event page: 'Event Location:' custom field. Holds a full postal address
# for confirmed venues and a placeholder while the venue is unannounced.
_ADDRESS_RE = re.compile(
    r'en_event_address[^"]*"[^>]*>.*?<span class="w-post-elm-value">([^<]+)<',
    re.S,
)
_ADDRESS_TBA_RE = re.compile(r"to be announced|^tba\b|coming soon|^-*$", re.I)

_GEO_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim's fair-use policy: max 1 req/s, identifying User-Agent.
_GEO_UA = "hybridcal-reconciler (https://hybridcal.com)"
_GEO_DELAY = 1.1
_GEO_RETRIES = 3
_GEO_BACKOFF = 2.0

_geo_cache: dict[str, list] = {}


def _detail_address(event_url: str) -> str:
    """'Event Location:' from the event page, '' if absent/unreachable."""
    try:
        page = _http_get(event_url)
    except Exception:
        return ""
    m = _ADDRESS_RE.search(page)
    if not m:
        return ""
    return re.sub(r"\s+", " ", htmlmod.unescape(m.group(1))).strip()


def _in_continent(lat: float, lon: float, continent: str) -> bool:
    """Sanity-check a geocode against the card's continent bucket. An
    unknown continent can't falsify anything, so it passes."""
    box = _CONTINENT_BBOX.get(continent)
    if not box:
        return True
    lat_min, lat_max, lon_min, lon_max = box
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def _geocode(query: str, continent: str) -> tuple[str, float, float] | None:
    """Nominatim lookup → (ISO country, lat, lon) for the best-ranked hit
    inside `continent`, or None if nothing plausible comes back.

    We ask for several candidates rather than one: bare city names are
    ambiguous across continents — 'Athens' ranks Athens, Georgia above
    the Greek one — and the continent filter resolves that ambiguity
    instead of tripping over it.
    """
    if not query:
        return None
    key = f"{query}|{continent}"
    if key not in _geo_cache:
        q = {"q": query, "format": "json", "addressdetails": "1", "limit": "5"}
        box = _CONTINENT_BBOX.get(continent)
        if box:
            # Restrict the search to the continent instead of merely
            # filtering afterwards: 'Athens' has no Greek hit in its top 5
            # at all, so a post-filter alone would just discard the lot.
            lat_min, lat_max, lon_min, lon_max = box
            q["viewbox"] = f"{lon_min},{lat_max},{lon_max},{lat_min}"
            q["bounded"] = "1"
        params = urllib.parse.urlencode(q)
        req = urllib.request.Request(
            f"{_GEO_URL}?{params}",
            headers={"User-Agent": _GEO_UA, "Accept": "application/json"},
        )
        # Nominatim throttles bursts; a transient failure must not be
        # cached as 'no such place' or we silently drop a real event.
        for attempt in range(_GEO_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    _geo_cache[key] = json.loads(
                        r.read().decode("utf-8", errors="replace"))
                break
            except Exception:
                if attempt == _GEO_RETRIES - 1:
                    _geo_cache[key] = []
                else:
                    time.sleep(_GEO_BACKOFF * (attempt + 1))
        time.sleep(_GEO_DELAY)

    for hit in _geo_cache[key] or []:
        try:
            lat, lon = float(hit["lat"]), float(hit["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        if not _in_continent(lat, lon, continent):
            continue
        cc = ((hit.get("address") or {}).get("country_code") or "").upper()
        if cc:
            return cc, lat, lon
    return None


def _locate(card: dict) -> tuple[str, float | None, float | None]:
    """Resolve a card to (ISO country, lat, lon).

    The event page's address is the better geocode input, but it may be a
    'venue TBA' placeholder, and even a real one can omit the country and
    resolve to the wrong continent. Either way we retry with the bare
    city, which is also the precision our existing YAMLs carry
    (city-centre coordinates).
    """
    addr = _detail_address(card["event_url"])
    continent = card["continent"]
    if addr and not _ADDRESS_TBA_RE.search(addr):
        hit = _geocode(addr, continent)
        if hit:
            cc, lat, lon = hit
            return _CC_FIX.get(card["city"], cc), lat, lon
    hit = _geocode(card["city"], continent)
    if hit:
        cc, lat, lon = hit
        return _CC_FIX.get(card["city"], cc), lat, lon
    return "", None, None


# Every HYROX event runs the same category set (verified across all 68
# existing YAMLs), so new events can be seeded with it.
DEFAULT_CATEGORIES = [
    "singles-pro-men", "singles-pro-women",
    "singles-open-men", "singles-open-women",
    "doubles-men", "doubles-women", "doubles-mixed",
    "relay-mixed",
]


def fetch() -> list[SourceRecord]:
    """Adult HYROX events.

    Events we already have a YAML for are returned from the card alone —
    that carries date/url (the only fields the reconciler syncs onto
    existing events) and spares us ~70 detail fetches plus geocodes per
    run. Unknown events get their event page read and geocoded so they
    can be auto-created with country/timezone/coordinates.
    """
    known = {le.source_id for le in load_local_events(FORMAT_ID) if le.source_id}
    today = date.today()
    out: list[SourceRecord] = []
    for c in parse_cards():
        if c["type_class"] != "type-adults":
            continue

        country, lat, lon, tz, note = "", None, None, "", ""
        is_new = c["post_id"] not in known
        # Only unknown, dated, future events are worth resolving: past and
        # date-TBA rows are never auto-created anyway (run.py), and known
        # ones have curated location fields we must not overwrite.
        if is_new and c["date_start"] and c["date_start"] >= today:
            country, lat, lon = _locate(c)
            tz = _CITY_TZ.get(c["city"]) or _COUNTRY_TZ.get(country, "")
            if not country:
                note = (f"`{c['title']}` ({c['date_start']}) nicht angelegt: "
                        f"Ort '{c['city']}' liess sich nicht geocoden — "
                        f"manuell pruefen: {c['event_url']}")
            elif not tz:
                note = (f"`{c['title']}` ({c['date_start']}) nicht angelegt: "
                        f"keine Zeitzone fuer Land {country} hinterlegt — "
                        f"_COUNTRY_TZ/_CITY_TZ in sources/hyrox.py ergaenzen")
        elif is_new and not c["date_start"]:
            note = (f"`{c['title']}` nicht angelegt: Quelle nennt noch kein "
                    f"Datum (TBA) — {c['event_url']}")

        out.append(SourceRecord(
            source_id=c["post_id"],
            format=FORMAT_ID,
            name=c["title"],
            date_start=c["date_start"],
            date_end=c["date_end"],
            city=c["city"],
            country=country,
            timezone=tz,
            lat=lat,
            lon=lon,
            url=c["event_url"],
            categories=DEFAULT_CATEGORIES.copy(),
            suggested_slug=f"hyrox-{slugify(c['city'])}-{c['date_start'].strftime('%Y-%m') if c['date_start'] else 'tba'}",
            # timezone is required by our Location model and country must
            # be ISO-2 — without both, creating a YAML would break the
            # build, so leave it for a human.
            is_main_brand=bool(country and tz and c["date_start"]),
            skip_note=note,
        ))
    return out
