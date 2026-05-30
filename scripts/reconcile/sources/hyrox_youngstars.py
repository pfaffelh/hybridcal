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


def _city_info_map() -> dict[str, dict]:
    """Build {normalised-city: {country, timezone, venue, lat, lon}} from
    existing Adult HYROX YAMLs. Pydantic's Location model requires country
    and timezone, so we can only auto-create a Youngstars YAML when its
    city has a sister Adult event we can copy these from. venue/lat/lon
    are copied too so the new YAML lands on the map (Youngstars run at
    the same venue as the Adult race)."""
    out: dict[str, dict] = {}
    for le in load_local_events("hyrox"):
        loc = le.data.get("location") or {}
        city = loc.get("city", "")
        country = loc.get("country", "")
        tz = loc.get("timezone", "")
        if city and country and tz:
            out[normalise_city(city)] = {
                "country": country,
                "timezone": tz,
                "venue": loc.get("venue"),
                "lat": loc.get("lat"),
                "lon": loc.get("lon"),
            }
    return out


def fetch() -> list[SourceRecord]:
    cmap = _city_info_map()
    out: list[SourceRecord] = []
    for c in hyrox.parse_cards():
        if c["type_class"] != "type-youngstars":
            continue
        info = cmap.get(normalise_city(c["city"])) or {}
        country = info.get("country", "")
        tz = info.get("timezone", "")
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
            venue=info.get("venue"),
            timezone=tz,
            lat=info.get("lat"),
            lon=info.get("lon"),
            url=c["event_url"],
            categories=DEFAULT_CATEGORIES.copy(),
            suggested_slug=slug,
            is_main_brand=bool(country and tz),
        ))
    return out
