#!/usr/bin/env python3
"""Geocode events that don't have lat/lon yet.

Uses Nominatim (OpenStreetMap) — free, but rate-limited by their
fair-use policy: max 1 request/second, custom User-Agent required.

Results are cached to data/geocode_cache.yml so subsequent runs only
query for new locations. Coordinates are written directly back into
the event YAML files, after the timezone line. Existing lat/lon is
preserved.

Run:
    python scripts/geocode.py
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import yaml
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

ROOT = Path(__file__).parent.parent
EVENTS_DIR = ROOT / "data" / "events"
CACHE_FILE = ROOT / "data" / "geocode_cache.yml"

USER_AGENT = "hybridcal-geocoder (https://hybridcal.com)"
NOMINATIM_DELAY = 1.1  # seconds, slight buffer above 1 req/s policy


def load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}


def save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w") as f:
        yaml.safe_dump(cache, f, allow_unicode=True, sort_keys=True)


def cache_key(loc: dict) -> str:
    parts = [loc.get("venue"), loc.get("city"), loc.get("country")]
    return ", ".join(p for p in parts if p)


def parse_location(yaml_text: str) -> dict:
    """Extract the location dict from a YAML text without round-tripping."""
    return yaml.safe_load(yaml_text).get("location", {})


def has_coords(yaml_text: str) -> bool:
    return bool(re.search(r"^\s+lat:\s*[-\d]", yaml_text, re.MULTILINE)) and \
           bool(re.search(r"^\s+lon:\s*[-\d]", yaml_text, re.MULTILINE))


def inject_coords(yaml_text: str, lat: float, lon: float) -> str:
    """Insert lat/lon lines after the location.timezone line, preserving format."""
    lines = yaml_text.splitlines(keepends=True)
    out: list[str] = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and re.match(r"^\s+timezone:", line):
            indent = re.match(r"^(\s+)", line).group(1)
            out.append(f"{indent}lat: {lat:.6f}\n")
            out.append(f"{indent}lon: {lon:.6f}\n")
            inserted = True
    if not inserted:
        raise ValueError("No timezone line found; cannot determine indent for coords")
    return "".join(out)


def geocode_one(geocoder: Nominatim, key: str):
    """Try the full key, then fall back to city+country if needed."""
    try:
        result = geocoder.geocode(key, timeout=10, language="en")
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"    geocoder error: {e}", file=sys.stderr)
        return None
    return result


def main() -> int:
    cache = load_cache()
    geocoder = Nominatim(user_agent=USER_AGENT)

    paths = sorted(EVENTS_DIR.rglob("*.yml"))
    counts = {"skip_has_coords": 0, "from_cache": 0, "queried": 0, "failed": 0}

    for path in paths:
        text = path.read_text()
        if has_coords(text):
            counts["skip_has_coords"] += 1
            continue

        loc = parse_location(text)
        key = cache_key(loc)
        if not key:
            print(f"  {path.name}: no location info", file=sys.stderr)
            counts["failed"] += 1
            continue

        if key in cache and "lat" in cache[key]:
            lat, lon = cache[key]["lat"], cache[key]["lon"]
            counts["from_cache"] += 1
            print(f"  {path.name}: cache  {lat:.4f}, {lon:.4f}")
        else:
            print(f"  {path.name}: query  '{key}'")
            result = geocode_one(geocoder, key)
            time.sleep(NOMINATIM_DELAY)
            if result is None:
                fallback = ", ".join(
                    p for p in [loc.get("city"), loc.get("country")] if p
                )
                if fallback and fallback != key:
                    print(f"    fallback '{fallback}'")
                    result = geocode_one(geocoder, fallback)
                    time.sleep(NOMINATIM_DELAY)
            if result is None:
                print(f"    FAILED: '{key}'", file=sys.stderr)
                counts["failed"] += 1
                continue
            lat = round(result.latitude, 6)
            lon = round(result.longitude, 6)
            cache[key] = {
                "lat": lat,
                "lon": lon,
                "display_name": result.address,
            }
            save_cache(cache)
            counts["queried"] += 1
            print(f"    -> {lat:.4f}, {lon:.4f}")

        new_text = inject_coords(text, lat, lon)
        path.write_text(new_text)

    print()
    print(f"Done. {counts['skip_has_coords']} already had coords, "
          f"{counts['from_cache']} from cache, "
          f"{counts['queried']} newly geocoded, "
          f"{counts['failed']} failed.")
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
