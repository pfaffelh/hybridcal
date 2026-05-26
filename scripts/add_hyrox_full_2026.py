#!/usr/bin/env python3
"""Add HYROX events from hyroxdach.com/find-your-race/.

Source date: 2026-05-26. Adds events not already present in
data/events/2026/. Run once; subsequent runs are idempotent
(skips files that already exist).

Edge cases included:
  - Multi-day events spanning month boundaries (Oct 28 – Nov 1)
  - Tenerife in Atlantic/Canary timezone (different from Europe/Madrid)
  - Non-European events: Africa, Americas, Asia, Oceania
  - "Youngstars" variants as separate events (HYROX youth format)

TBA events (Abu Dhabi, Stockholm Intersport, Melbourne) are
intentionally skipped — schema requires concrete dates.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "data" / "events" / "2026"


def _q(s: str) -> str:
    return '"' + s.replace('"', '""') + '"'


def hyrox(slug, name, date_start, date_end, city, country, tz, venue=None, categories=None):
    cats = categories if categories is not None else [
        "singles-pro-men", "singles-pro-women",
        "singles-open-men", "singles-open-women",
        "doubles-men", "doubles-women", "doubles-mixed",
        "relay-mixed",
    ]
    venue_line = f"\n  venue: {_q(venue)}" if venue else ""
    city_url = city.lower().replace(" ", "-").replace(".", "").replace("'", "")
    url = f"https://hyrox.com/event/{city_url}/"
    if cats:
        cats_yaml = "categories:\n" + "\n".join(f"  - {c}" for c in cats)
    else:
        cats_yaml = "categories: []"
    # Quote country code to avoid the YAML "Norway problem" (NO → False)
    return slug, f"""slug: {slug}
name: {_q(name)}
format: hyrox
date_start: {date_start}
date_end: {date_end}
location:
  city: {_q(city)}
  country: {_q(country)}{venue_line}
  timezone: {tz}
url: {_q(url)}
status: confirmed
source: scraped
{cats_yaml}
"""


# Youngstars: youth/junior variant. Distinct categories — leave empty here
# rather than guessing IDs; can be filled in once we add youth categories
# to categories.yml.
def youngstars(slug, name, date_start, date_end, city, country, tz, venue=None):
    return hyrox(slug, name, date_start, date_end, city, country, tz, venue, categories=[])


EVENTS = [
    # -- Late spring 2026: tail of 25/26 season --
    hyrox("hyrox-rimini-2026-05", "HYROX Rimini",
          "2026-05-28", "2026-05-31", "Rimini", "IT", "Europe/Rome"),
    hyrox("hyrox-riga-2026-05", "LEMON GYM HYROX Riga",
          "2026-05-30", "2026-05-31", "Riga", "LV", "Europe/Riga"),
    youngstars("hyrox-youngstars-berlin-2026-05", "HYROX Youngstars Berlin",
               "2026-05-30", "2026-05-31", "Berlin", "DE", "Europe/Berlin"),
    hyrox("hyrox-new-york-2026-05", "NYU Langone Health HYROX New York",
          "2026-05-28", "2026-06-07", "New York", "US", "America/New_York"),
    hyrox("hyrox-johannesburg-2026-05", "Virgin Active HYROX Johannesburg 25/26",
          "2026-05-30", "2026-05-31", "Johannesburg", "ZA", "Africa/Johannesburg"),

    # -- June 2026 --
    hyrox("hyrox-buenos-aires-2026-06", "HYROX Buenos Aires",
          "2026-06-13", "2026-06-13", "Buenos Aires", "AR", "America/Argentina/Buenos_Aires"),
    hyrox("hyrox-stockholm-wc-2026-06", "PUMA HYROX World Championships Stockholm",
          "2026-06-18", "2026-06-21", "Stockholm", "SE", "Europe/Stockholm"),
    hyrox("hyrox-jakarta-2026-06", "AirAsia HYROX Jakarta",
          "2026-06-27", "2026-06-28", "Jakarta", "ID", "Asia/Jakarta"),

    # -- July 2026 --
    hyrox("hyrox-sydney-2026-07", "BYD HYROX Sydney",
          "2026-07-01", "2026-07-05", "Sydney", "AU", "Australia/Sydney"),
    hyrox("hyrox-hangzhou-2026-07", "TORRAS HYROX Hangzhou",
          "2026-07-04", "2026-07-05", "Hangzhou", "CN", "Asia/Shanghai"),
    hyrox("hyrox-delhi-2026-07", "Masters' Union HYROX Delhi",
          "2026-07-24", "2026-07-26", "Delhi", "IN", "Asia/Kolkata"),

    # -- August 2026 --
    hyrox("hyrox-chengdu-2026-08", "HYROX Chengdu",
          "2026-08-01", "2026-08-02", "Chengdu", "CN", "Asia/Shanghai"),
    hyrox("hyrox-istanbul-2026-08", "HYROX Istanbul",
          "2026-08-01", "2026-08-02", "Istanbul", "TR", "Europe/Istanbul"),
    hyrox("hyrox-chiba-2026-08", "AirAsia HYROX Chiba",
          "2026-08-06", "2026-08-09", "Chiba", "JP", "Asia/Tokyo"),
    hyrox("hyrox-bangkok-2026-08", "BYD HYROX Bangkok",
          "2026-08-13", "2026-08-16", "Bangkok", "TH", "Asia/Bangkok"),
    hyrox("hyrox-cape-town-2026-08", "Virgin Active HYROX Cape Town",
          "2026-08-14", "2026-08-15", "Cape Town", "ZA", "Africa/Johannesburg"),
    hyrox("hyrox-shenzhen-2026-08", "HYROX Shenzhen",
          "2026-08-15", "2026-08-16", "Shenzhen", "CN", "Asia/Shanghai"),
    hyrox("hyrox-perth-2026-08", "AirAsia HYROX Perth",
          "2026-08-21", "2026-08-23", "Perth", "AU", "Australia/Perth"),

    # -- September 2026 --
    hyrox("hyrox-washington-2026-09", "Amazfit HYROX Washington D.C.",
          "2026-09-03", "2026-09-07", "Washington D.C.", "US", "America/New_York"),
    hyrox("hyrox-tenerife-2026-09", "HYROX Tenerife",
          "2026-09-04", "2026-09-06", "Santa Cruz de Tenerife", "ES", "Atlantic/Canary"),
    hyrox("hyrox-acapulco-2026-09", "Mundo Imperial HYROX Acapulco",
          "2026-09-05", "2026-09-06", "Acapulco", "MX", "America/Mexico_City"),
    hyrox("hyrox-beijing-2026-09", "HYROX Beijing",
          "2026-09-12", "2026-09-13", "Beijing", "CN", "Asia/Shanghai"),
    hyrox("hyrox-mumbai-2026-09", "Masters' Union HYROX Mumbai",
          "2026-09-17", "2026-09-20", "Mumbai", "IN", "Asia/Kolkata"),
    hyrox("hyrox-salt-lake-city-2026-09", "InBody HYROX Salt Lake City",
          "2026-09-18", "2026-09-20", "Salt Lake City", "US", "America/Denver"),
    youngstars("hyrox-youngstars-maastricht-2026-09", "HYROX Youngstars Maastricht",
               "2026-09-19", "2026-09-20", "Maastricht", "NL", "Europe/Amsterdam"),
    youngstars("hyrox-youngstars-salt-lake-city-2026-09", "HYROX Youngstars Salt Lake City",
               "2026-09-19", "2026-09-20", "Salt Lake City", "US", "America/Denver"),
    hyrox("hyrox-oslo-2026-09", "HYROX Oslo",
          "2026-09-25", "2026-09-27", "Oslo", "NO", "Europe/Oslo"),
    youngstars("hyrox-youngstars-oslo-2026-09", "HYROX Youngstars Oslo",
               "2026-09-26", "2026-09-27", "Oslo", "NO", "Europe/Oslo"),

    # -- October 2026 --
    hyrox("hyrox-toronto-2026-10", "GoodLife HYROX Toronto",
          "2026-10-01", "2026-10-04", "Toronto", "CA", "America/Toronto"),
    hyrox("hyrox-boston-2026-10", "HWPO HYROX Boston",
          "2026-10-08", "2026-10-11", "Boston", "US", "America/New_York"),
    hyrox("hyrox-gdansk-2026-10", "HYROX Gdańsk",
          "2026-10-10", "2026-10-11", "Gdańsk", "PL", "Europe/Warsaw"),
    hyrox("hyrox-sao-paulo-2026-10", "HYROX São Paulo",
          "2026-10-17", "2026-10-17", "São Paulo", "BR", "America/Sao_Paulo"),
    youngstars("hyrox-youngstars-valencia-2026-10", "HYROX Youngstars Valencia",
               "2026-10-17", "2026-10-18", "Valencia", "ES", "Europe/Madrid"),
    hyrox("hyrox-tampa-2026-10", "MyFitnessPal HYROX Tampa",
          "2026-10-23", "2026-10-25", "Tampa", "US", "America/New_York"),
    # Hamburg — first new DACH event for 2026/27!
    hyrox("hyrox-hamburg-2026-10", "Intersport HYROX Hamburg",
          "2026-10-28", "2026-11-01", "Hamburg", "DE", "Europe/Berlin"),
    hyrox("hyrox-mexico-city-2026-10", "HYROX Mexico City",
          "2026-10-30", "2026-11-01", "Mexico City", "MX", "America/Mexico_City"),
    hyrox("hyrox-shanghai-2026-10", "HYROX Shanghai",
          "2026-10-31", "2026-11-01", "Shanghai", "CN", "Asia/Shanghai"),
    youngstars("hyrox-youngstars-birmingham-2026-10", "HYROX Youngstars Birmingham",
               "2026-10-31", "2026-11-01", "Birmingham", "GB", "Europe/London"),

    # -- November 2026 --
    hyrox("hyrox-dublin-2026-11", "HYROX Dublin",
          "2026-11-11", "2026-11-15", "Dublin", "IE", "Europe/Dublin"),
    hyrox("hyrox-denver-2026-11", "HYROX Denver",
          "2026-11-12", "2026-11-15", "Denver", "US", "America/Denver"),
    hyrox("hyrox-seoul-2026-11", "AirAsia HYROX Seoul",
          "2026-11-14", "2026-11-15", "Seoul", "KR", "Asia/Seoul"),
    hyrox("hyrox-dallas-2026-11", "HYROX Dallas",
          "2026-11-18", "2026-11-22", "Dallas", "US", "America/Chicago"),
    hyrox("hyrox-poznan-2026-11", "HYROX Poznań",
          "2026-11-20", "2026-11-22", "Poznań", "PL", "Europe/Warsaw"),
    hyrox("hyrox-guangzhou-2026-11", "HYROX Guangzhou",
          "2026-11-21", "2026-11-22", "Guangzhou", "CN", "Asia/Shanghai"),
    hyrox("hyrox-rio-de-janeiro-2026-11", "HYROX Rio de Janeiro",
          "2026-11-21", "2026-11-21", "Rio de Janeiro", "BR", "America/Sao_Paulo"),
    hyrox("hyrox-singapore-2026-11", "AIA HYROX Singapore",
          "2026-11-27", "2026-11-29", "Singapore", "SG", "Asia/Singapore"),
    hyrox("hyrox-johannesburg-2026-11", "Virgin Active HYROX Johannesburg",
          "2026-11-28", "2026-11-29", "Johannesburg", "ZA", "Africa/Johannesburg"),
    youngstars("hyrox-youngstars-utrecht-2026-11", "HYROX Youngstars Utrecht",
               "2026-11-28", "2026-11-29", "Utrecht", "NL", "Europe/Amsterdam"),

    # -- December 2026 --
    hyrox("hyrox-anaheim-2026-12", "HYROX Anaheim",
          "2026-12-04", "2026-12-06", "Anaheim", "US", "America/Los_Angeles"),
    youngstars("hyrox-youngstars-london-2026-12", "HYROX Youngstars London ExCel",
               "2026-12-05", "2026-12-06", "London", "GB", "Europe/London"),
    youngstars("hyrox-youngstars-anaheim-2026-12", "HYROX Youngstars Anaheim",
               "2026-12-05", "2026-12-06", "Anaheim", "US", "America/Los_Angeles"),
    hyrox("hyrox-sanya-2026-12", "HYROX Sanya",
          "2026-12-05", "2026-12-06", "Sanya", "CN", "Asia/Shanghai"),
    hyrox("hyrox-nashville-2026-12", "HYROX Nashville",
          "2026-12-10", "2026-12-13", "Nashville", "US", "America/Chicago"),
    hyrox("hyrox-helsinki-2026-12", "HYROX Helsinki",
          "2026-12-18", "2026-12-20", "Helsinki", "FI", "Europe/Helsinki"),
    hyrox("hyrox-vancouver-2026-12", "HYROX Vancouver",
          "2026-12-18", "2026-12-20", "Vancouver", "CA", "America/Vancouver"),
    youngstars("hyrox-youngstars-paris-2026-12", "HYROX Youngstars Paris",
               "2026-12-19", "2026-12-20", "Paris", "FR", "Europe/Paris"),
]


# Events skipped because they have no concrete date on the source page:
TBA_SKIPPED = [
    "HYROX Abu Dhabi (AE)",
    "Intersport HYROX Stockholm (SE)",
    "HYROX Melbourne (AU)",
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    for slug, content in EVENTS:
        path = OUT_DIR / f"{slug}.yml"
        if path.exists():
            skipped += 1
            continue
        path.write_text(content)
        written += 1

    print(f"Wrote {written} new events, skipped {skipped} existing")
    print()
    print(f"Note: {len(TBA_SKIPPED)} TBA-date events not added (schema requires dates):")
    for name in TBA_SKIPPED:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
