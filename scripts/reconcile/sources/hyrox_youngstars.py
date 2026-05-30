"""HYROX Youngstars source plugin.

Reads the same find-my-race HTML as the Adult HYROX plugin and filters
for type-youngstars cards. Country isn't exposed in the HTML, so we
derive it from the sister Adult HYROX YAML at the same city — every
Youngstars venue is also an Adult-HYROX venue. If no Adult-HYROX YAML
covers the city, the record is is_main_brand=False (silently skipped).
"""
from __future__ import annotations

from datetime import date

from . import hyrox
from .. import SourceRecord, load_local_events, normalise_city, slugify

FORMAT_ID = "hyrox-youngstars"

# Default category list per Youngstars event: all four age groups run at
# every venue, so we pre-fill the YAML with all of them.
DEFAULT_CATEGORIES = [
    "youngstars-8-9",
    "youngstars-10-11",
    "youngstars-12-13",
    "youngstars-14-15",
]


def _city_info_map() -> dict[str, tuple[str, str]]:
    """Build {normalised-city: (country, timezone)} from existing Adult
    HYROX YAMLs. Pydantic's Location model requires both, so we can only
    auto-create a Youngstars YAML when its city has a sister Adult
    event we can copy these from."""
    out: dict[str, tuple[str, str]] = {}
    for le in load_local_events("hyrox"):
        loc = le.data.get("location") or {}
        city = loc.get("city", "")
        country = loc.get("country", "")
        tz = loc.get("timezone", "")
        if city and country and tz:
            out[normalise_city(city)] = (country, tz)
    return out


def fetch() -> list[SourceRecord]:
    cmap = _city_info_map()
    out: list[SourceRecord] = []
    for c in hyrox.parse_cards():
        if c["type_class"] != "type-youngstars":
            continue
        info = cmap.get(normalise_city(c["city"]))
        country, tz = info if info else ("", "")
        d = c["date_start"]
        slug = (f"hyrox-youngstars-{slugify(c['city'])}-"
                f"{d.strftime('%Y-%m') if d else 'tba'}")
        out.append(SourceRecord(
            source_id=c["post_id"],
            format=FORMAT_ID,
            name=f"HYROX Youngstars {c['city']}",
            date_start=d,
            date_end=c["date_end"],
            city=c["city"],
            country=country,
            timezone=tz,
            url=c["event_url"],
            categories=DEFAULT_CATEGORIES.copy(),
            suggested_slug=slug,
            is_main_brand=bool(country and tz),
        ))
    return out
