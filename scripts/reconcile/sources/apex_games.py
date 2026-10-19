"""Apex Games source plugin.

apexgames.fit ist WordPress (Divi); der Saison-Kalender steht als
statisches HTML auf der Startseite:

    <section class="apex-season-events">
      <span class="apex-season-events-label">Season 2</span>
      <div class="apex-season-card">
        <span class="apex-season-number">Event #1</span>
        <div class="apex-season-date"> 14–15 <span>November 2026</span> </div>
        <h3 class="apex-season-title"> Abu Dhabi </h3>
        <div class="apex-season-meta"> <svg…/> <span>321 Sports, …</span> </div>
        <a class="apex-season-button" href="https://tickets.trumin.com/…">

Es gibt keine Event-IDs. Stabile source_id = '<saison>-<nummer>' (z.B.
's2-e1') — die Karten sind fest durchnummeriert, und Stadt/Datum stehen
anfangs oft nur als Platzhalter da ("Venue announcing soon", "End March").

Noch nicht buchbare Events haben statt Link ein
`apex-season-button-disabled` → url = /events/, status = tentative.
Sobald der Trumin-Link auftaucht, schaltet der Reconciler url und status um.
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

URL = "https://apexgames.fit/"
EVENTS_URL = "https://apexgames.fit/events/"
FORMAT_ID = "apex-games"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Apex läuft im MENA-Raum (Ranking heißt "MENA leaderboard").
COUNTRY_TZ = {
    "AE": "Asia/Dubai",
    "BH": "Asia/Bahrain",
    "EG": "Africa/Cairo",
    "JO": "Asia/Amman",
    "KW": "Asia/Kuwait",
    "OM": "Asia/Muscat",
    "QA": "Asia/Qatar",
    "SA": "Asia/Riyadh",
}

DEFAULT_CATEGORIES = [
    "solo-pro-men", "solo-pro-women", "solo-open-men", "solo-open-women",
    "doubles-pro-men", "doubles-pro-women",
    "doubles-open-men", "doubles-open-women", "doubles-open-mixed",
    "team-of-3", "six-pack", "junior-doubles",
]

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}

# Platzhalter-Texte in Titel/Meta der Karten
_PLACEHOLDER_RE = re.compile(
    r"announc|coming soon|details|tba|tbc|to be confirmed|culmination", re.I)

_GEO_URL = "https://nominatim.openstreetmap.org/search"
_GEO_UA = "hybridcal-reconciler (https://hybridcal.de)"
_GEO_DELAY = 1.1
_GEO_RETRIES = 3
_geo_cache: dict[str, tuple[str, float, float] | None] = {}


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _month(s: str) -> int | None:
    return _MONTHS.get(s.strip().lower())


def _parse_dates(s: str) -> tuple[date | None, date | None]:
    """'14–15 November 2026', '30 April – 1 May 2027', '6 June 2026'.
    Unscharfe Angaben ('End March 2027', 'Late May / Early June 2027')
    → (None, None) = TBA."""
    s = s.replace("–", "-").replace("—", "-")
    try:
        m = re.fullmatch(r"(\d{1,2})\s*-\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
        if m and _month(m.group(3)):
            mo, y = _month(m.group(3)), int(m.group(4))
            return date(y, mo, int(m.group(1))), date(y, mo, int(m.group(2)))
        m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s*-\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
        if m and _month(m.group(2)) and _month(m.group(4)):
            y = int(m.group(5))
            start = date(y, _month(m.group(2)), int(m.group(1)))
            end = date(y, _month(m.group(4)), int(m.group(3)))
            if end < start:  # Dez–Jan über den Jahreswechsel
                start = start.replace(year=y - 1)
            return start, end
        m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
        if m and _month(m.group(2)):
            d = date(int(m.group(3)), _month(m.group(2)), int(m.group(1)))
            return d, d
    except ValueError:
        pass
    return None, None


def _geocode(query: str) -> tuple[str, float, float] | None:
    """Nominatim → (ISO-Land, lat, lon), auf die MENA-Länder beschränkt.
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
    """Rohdaten je Saison-Karte (ohne Geocoding)."""
    m = re.search(r'apex-season-events-label">\s*Season\s+(\d+)', body)
    if not m:
        raise SystemExit("apex-games: kein Saison-Kalender gefunden — Layout geändert?")
    season = int(m.group(1))
    out = []
    for chunk in body.split('<div class="apex-season-card">')[1:]:
        num = re.search(r'apex-season-number">\s*Event\s*#\s*(\d+)', chunk)
        if not num:
            continue
        date_txt = re.search(r'apex-season-date">(.*?)</div>', chunk, re.S)
        title = re.search(r'apex-season-title">(.*?)</h3>', chunk, re.S)
        meta = re.search(r'apex-season-meta">.*?<span>(.*?)</span>', chunk, re.S)
        href = re.search(r'<a class="apex-season-button"[^>]*href="([^"]+)"', chunk)
        out.append({
            "season": season,
            "number": int(num.group(1)),
            "date": _text(date_txt.group(1)) if date_txt else "",
            "title": _text(title.group(1)) if title else "",
            "meta": _text(meta.group(1)) if meta else "",
            "url": _html.unescape(href.group(1)) if href else "",
        })
    return out


def _record(card: dict) -> SourceRecord:
    sid = f"s{card['season']}-e{card['number']}"
    date_start, date_end = _parse_dates(card["date"])
    title, meta = card["title"], card["meta"]
    is_final = bool(re.search(r"final", title, re.I))

    city = "" if (is_final or _PLACEHOLDER_RE.search(title)) else title
    venue = None
    if meta and not _PLACEHOLDER_RE.search(meta):
        venue = re.sub(rf",\s*{re.escape(city)}$", "", meta).strip() if city else meta

    country, lat, lon = "", None, None
    if city:
        # Volle Venue, dann nur der Venue-Name ('321 Sports') — Nominatim
        # kennt Zusätze wie 'Hudayriyat Island' oft nicht in dieser Form.
        hit = None
        if venue:
            hit = _geocode(f"{venue}, {city}") or _geocode(f"{venue.split(',')[0]}, {city}")
        if hit:
            country, lat, lon = hit
        else:
            # Nur die Stadt: liefert das Land, aber keine Venue-Koordinaten
            # vortäuschen.
            country = (_geocode(city) or ("", None, None))[0]

    name = "Apex Games Championship Final" if is_final else (
        f"Apex Games {city}" if city else f"Apex Games – Saison {card['season']}, Event {card['number']}")
    ticketed = bool(card["url"])
    if is_final:
        slug = f"apex-games-championship-final-{date_start.year if date_start else 'tba'}"
    else:
        slug = (f"apex-games-{slugify(city) or 'tba'}-"
                f"{date_start.strftime('%Y-%m') if date_start else 'tba'}")

    skip = ""
    if not date_start:
        skip = (f"apex-games `{sid}` ({title or '?'}, \"{card['date']}\"): "
                f"noch kein genaues Datum — nicht automatisch angelegt.")
    elif not city or not country:
        skip = (f"apex-games `{sid}` ({card['date']}): Stadt/Land noch nicht "
                f"bestimmbar (\"{title}\") — nicht automatisch angelegt.")

    return SourceRecord(
        source_id=sid,
        format=FORMAT_ID,
        name=name,
        date_start=date_start,
        date_end=date_end,
        city=city,
        country=country,
        venue=venue,
        timezone=COUNTRY_TZ.get(country, ""),
        lat=lat,
        lon=lon,
        url=card["url"] or EVENTS_URL,
        categories=DEFAULT_CATEGORIES.copy(),
        suggested_slug=slug,
        is_main_brand=not skip,
        skip_note=skip,
        status="confirmed" if ticketed and date_start else "tentative",
    )


def fetch() -> list[SourceRecord]:
    return [_record(c) for c in parse_cards(_http_get(URL))]
