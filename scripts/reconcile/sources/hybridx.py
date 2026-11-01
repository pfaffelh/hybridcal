"""HybridX source plugin.

hybridx.fit ist Next.js-SSR; der Saison-Kalender steht als <article>-Karten
im HTML der Startseite (Desktop- und Mobil-Variante → doppelt, per UUID
dedupliziert):

    <article>
      <img alt="Göteborg — Scandinavium" …>
      <span>Registration open</span>
      <span>24</span><span>JAN</span>  <div>Sunday · 2027</div>
      <div>Göteborg</div>  <div><svg…/>Scandinavium</div>
      <a href="/en/purchase/019eacfb-…">Register</a>   (bzw. "Get notified")

Stabile source_id = die Purchase-UUID; sie ist auch die event-spezifische
`url:`. "Register" → status confirmed, "Get notified" (Anmeldung noch zu)
→ tentative. Venue "TBD" = noch nicht bekannt.
"""
from __future__ import annotations

import html as _html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date

from .. import SourceRecord, slugify

URL = "https://hybridx.fit/en"
SITE = "https://hybridx.fit"
FORMAT_ID = "hybridx"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Bisher nur Schweden; Nachbarländer vorsorglich, falls die Serie wächst.
COUNTRY_TZ = {
    "SE": "Europe/Stockholm",
    "NO": "Europe/Oslo",
    "DK": "Europe/Copenhagen",
    "FI": "Europe/Helsinki",
}

DEFAULT_CATEGORIES = [
    "singles-open-men", "singles-open-women", "singles-pro-men", "singles-pro-women",
    "doubles-open-men", "doubles-open-women", "doubles-open-mixed",
    "doubles-pro-men", "doubles-pro-women",
]

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

_TBD_RE = re.compile(r"^(tbd|tba|tbc|to be (announced|confirmed))$", re.I)

_GEO_URL = "https://nominatim.openstreetmap.org/search"
_GEO_UA = "hybridcal-reconciler (https://hybridcal.com)"
_GEO_DELAY = 1.1
_GEO_RETRIES = 3
_geo_cache: dict[str, tuple[str, float, float] | None] = {}


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _geocode(query: str) -> tuple[str, float, float] | None:
    """Nominatim → (ISO-Land, lat, lon), auf COUNTRY_TZ beschränkt.
    Ein transienter Fehler wird NICHT als 'gibt es nicht' gecacht."""
    if not query:
        return None
    if query in _geo_cache:
        return _geo_cache[query]
    params = urllib.parse.urlencode({
        "q": query, "format": "json", "addressdetails": "1", "limit": "1",
        "countrycodes": ",".join(c.lower() for c in COUNTRY_TZ),
    })
    req = urllib.request.Request(f"{_GEO_URL}?{params}",
                                 headers={"User-Agent": _GEO_UA})
    for attempt in range(_GEO_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                hits = json.loads(r.read().decode("utf-8", errors="replace"))
            break
        except Exception:
            if attempt == _GEO_RETRIES - 1:
                return None  # nicht cachen
            time.sleep(2.0 * (attempt + 1))
    time.sleep(_GEO_DELAY)
    res = None
    for h in hits:
        cc = ((h.get("address") or {}).get("country_code") or "").upper()
        try:
            res = (cc, round(float(h["lat"]), 4), round(float(h["lon"]), 4))
        except (KeyError, TypeError, ValueError):
            continue
        break
    _geo_cache[query] = res
    return res


def parse_cards(body: str) -> list[dict]:
    """Rohdaten je Kalender-Karte (ohne Geocoding), dedupliziert per UUID."""
    seen: dict[str, dict] = {}
    for chunk in body.split("<article")[1:]:
        chunk = chunk.split("</article>", 1)[0]
        link = re.search(r'<a[^>]*href="(/[a-z]{2}/purchase/([0-9a-f-]{36}))"[^>]*>(.*?)</a>',
                         chunk, re.S)
        if not link:
            continue
        uuid = link.group(2)
        if uuid in seen:
            continue
        alt = re.search(r'<img[^>]*alt="([^"]*)"', chunk)
        city, venue = "", ""
        if alt:
            parts = re.split(r"\s+[—–-]\s+", _html.unescape(alt.group(1)), maxsplit=1)
            city = parts[0].strip()
            venue = parts[1].strip() if len(parts) > 1 else ""
        texts = [_text(t) for t in re.findall(r">([^<>]+)<", chunk)]
        texts = [t for t in texts if t]
        day = month = year = None
        for i, t in enumerate(texts):
            if re.fullmatch(r"\d{1,2}", t) and i + 1 < len(texts) \
                    and texts[i + 1].lower()[:3] in _MONTHS and day is None:
                day, month = int(t), _MONTHS[texts[i + 1].lower()[:3]]
            m = re.search(r"·\s*(\d{4})$", t)
            if m and year is None:
                year = int(m.group(1))
        seen[uuid] = {
            "uuid": uuid,
            "url": SITE + link.group(1),
            "city": city,
            "venue": venue,
            "date": date(year, month, day) if day and month and year else None,
            "ticketed": _text(link.group(3)).lower().startswith("register"),
        }
    if not seen:
        raise SystemExit("hybridx: keine Kalender-Karten gefunden — Layout geändert?")
    return list(seen.values())


def _record(card: dict) -> SourceRecord:
    city = card["city"]
    venue = None if (not card["venue"] or _TBD_RE.match(card["venue"])) else card["venue"]
    d = card["date"]

    country, lat, lon = "", None, None
    hit = _geocode(f"{venue}, {city}") if venue else None
    if hit:
        country, lat, lon = hit
    else:
        # Nur die Stadt: liefert das Land, aber keine Venue-Koordinaten vortäuschen.
        country = (_geocode(city) or ("", None, None))[0]

    skip = ""
    if not d:
        skip = f"hybridx `{card['uuid']}` ({city or '?'}): kein Datum parsebar — nicht angelegt."
    elif not city or not country:
        skip = (f"hybridx `{card['uuid']}` ({d}): Stadt/Land nicht bestimmbar "
                f"(\"{city}\") — nicht angelegt.")

    return SourceRecord(
        source_id=card["uuid"],
        format=FORMAT_ID,
        name=f"HybridX {city}" if city else "HybridX",
        date_start=d,
        date_end=d,  # HybridX-Rennen sind eintägig
        city=city,
        country=country,
        venue=venue,
        timezone=COUNTRY_TZ.get(country, ""),
        lat=lat,
        lon=lon,
        url=card["url"],
        categories=DEFAULT_CATEGORIES.copy(),
        suggested_slug=f"hybridx-{slugify(city) or 'tba'}-{d.strftime('%Y-%m') if d else 'tba'}",
        is_main_brand=not skip,
        skip_note=skip,
        status="confirmed" if card["ticketed"] else "tentative",
    )


def fetch() -> list[SourceRecord]:
    return [_record(c) for c in parse_cards(_http_get(URL))]
