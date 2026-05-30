"""HYROX source plugin.

No public JSON API — the find-my-race page (WordPress) renders all events
server-side. Every event card is an <article> with data-id (= WP post ID
→ stable source_id), the H2 link (= event URL), and discrete date spans.
Parsing the HTML is robust and avoids the Playwright/Vercel-checkpoint
dance.

Country isn't exposed at the card level (only continent). New events
without a known country are surfaced as `ambiguous` in the reconcile
report and not auto-written.
"""
from __future__ import annotations

import re
import urllib.request
from datetime import date

from .. import SourceRecord, slugify

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
# from ours (Gent/Ghent, Tenerife/Santa Cruz de Tenerife).
_CITY_ALIAS = {
    "gent": "Ghent",
    "tenerife": "Santa Cruz de Tenerife",
}

# Matches any optional sponsor prefix (one or two words like 'puma-' or
# 'virgin-active-') followed by 'hyrox-' and an optional 'youngstars-'
# or 'world-championships-' segment. Stripped before city extraction.
_PREFIX_RE = re.compile(
    r"^(?:[a-z]+(?:-[a-z]+)?-)?hyrox-(?:youngstars-|world-championships-|championships-)?"
)

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
    event_url, title, date_start, date_end, city. Both Adult and
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
        title = re.sub(r"\s+", " ", title)

        d1_m = _DATE1_RE.search(body)
        d3_m = _DATE3_RE.search(body)
        date_start = _parse_date(d1_m.group(1)) if d1_m else None
        date_end = _parse_date(d3_m.group(1)) if d3_m else date_start

        cards.append({
            "post_id": head_m.group(1),
            "type_class": head_m.group(3),  # type-adults / type-youngstars
            "event_url": event_url,
            "title": title,
            "date_start": date_start,
            "date_end": date_end or date_start,
            "city": _extract_city(event_url, title),
        })
    return cards


def fetch() -> list[SourceRecord]:
    """Adult HYROX events only. Country isn't in the HTML, so we don't
    auto-create new YAMLs (is_main_brand=False) — the reconciler keeps
    existing 66 adult YAMLs in sync but won't invent new ones."""
    out: list[SourceRecord] = []
    for c in parse_cards():
        if c["type_class"] != "type-adults":
            continue
        out.append(SourceRecord(
            source_id=c["post_id"],
            format=FORMAT_ID,
            name=c["title"],
            date_start=c["date_start"],
            date_end=c["date_end"],
            city=c["city"],
            country="",
            url=c["event_url"],
            suggested_slug=f"hyrox-{slugify(c['city'])}-{c['date_start'].strftime('%Y-%m') if c['date_start'] else 'tba'}",
            is_main_brand=False,
        ))
    return out
