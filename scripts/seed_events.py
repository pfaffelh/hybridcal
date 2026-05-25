#!/usr/bin/env python3
"""One-off seed script.

Populates data/events/2026/ with scraped events from HYROX, ATHX, and
Deadly Dozen official calendars. Source date: 2026-05-25.

Run once after initial repo setup. Re-runs are idempotent — files get
overwritten with whatever is in this script.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "data" / "events" / "2026"
EXAMPLES = [
    "hyrox-munich-2026-11.yml",
    "athx-paris-2026-04.yml",
    "deadly-dozen-london-2026-10.yml",
]


def _q(s):
    """Quote a YAML string. Doubles internal double-quotes per YAML spec."""
    return '"' + s.replace('"', '""') + '"'


def hyrox(slug, name, date_start, date_end, city, country, tz, venue=None, url=None):
    cats = """\
  - singles-pro-men
  - singles-pro-women
  - singles-open-men
  - singles-open-women
  - doubles-men
  - doubles-women
  - doubles-mixed
  - relay-mixed"""
    venue_line = f"\n  venue: {_q(venue)}" if venue else ""
    url = url or f"https://hyrox.com/event/{city.lower().replace(' ', '-').replace('.', '')}/"
    return slug, f"""slug: {slug}
name: {_q(name)}
format: hyrox
date_start: {date_start}
date_end: {date_end}
location:
  city: {_q(city)}
  country: {country}{venue_line}
  timezone: {tz}
url: {_q(url)}
status: confirmed
source: scraped
categories:
{cats}
"""


def athx(slug, name, date_start, date_end, city, country, tz, venue, url=None):
    cats = """\
  - paired-rx-men
  - paired-rx-women
  - paired-rx-mixed
  - paired-scaled-men
  - paired-scaled-women
  - paired-scaled-mixed"""
    url = url or "https://athxgames.com/events"
    return slug, f"""slug: {slug}
name: {_q(name)}
format: athx
date_start: {date_start}
date_end: {date_end}
location:
  city: {_q(city)}
  country: {country}
  venue: {_q(venue)}
  timezone: {tz}
url: {_q(url)}
status: confirmed
source: scraped
categories:
{cats}
"""


def deadly(slug, name, date_start, date_end, city, country, tz, venue, url):
    cats = """\
  - deadly-strong-singles
  - deadly-strong-pairs
  - deadly-run-singles"""
    return slug, f"""slug: {slug}
name: {_q(name)}
format: deadly-dozen
date_start: {date_start}
date_end: {date_end}
location:
  city: {_q(city)}
  country: {country}
  venue: {_q(venue)}
  timezone: {tz}
url: {_q(url)}
status: confirmed
source: scraped
categories:
{cats}
"""


EVENTS = [
    # HYROX 2025/26 season tail
    hyrox("hyrox-st-gallen-2026-01", "WELL COME FIT HYROX St. Gallen",
          "2026-01-16", "2026-01-18", "St. Gallen", "CH", "Europe/Zurich",
          venue="OLMA Messen"),
    hyrox("hyrox-vienna-2026-02", "CREAPURE HYROX Vienna",
          "2026-02-06", "2026-02-08", "Vienna", "AT", "Europe/Vienna"),
    hyrox("hyrox-berlin-2026-05", "GILLETTELABS HYROX Berlin",
          "2026-05-22", "2026-05-31", "Berlin", "DE", "Europe/Berlin"),

    # HYROX 2026/27 season
    hyrox("hyrox-maastricht-2026-09", "HYROX Maastricht",
          "2026-09-17", "2026-09-20", "Maastricht", "NL", "Europe/Amsterdam"),
    hyrox("hyrox-rome-2026-09", "HYROX Rome",
          "2026-09-24", "2026-09-27", "Rome", "IT", "Europe/Rome"),
    hyrox("hyrox-bordeaux-2026-09", "HYROX Bordeaux",
          "2026-09-30", "2026-10-04", "Bordeaux", "FR", "Europe/Paris"),
    hyrox("hyrox-karlsruhe-2026-10", "HYROX Karlsruhe",
          "2026-10-01", "2026-10-04", "Karlsruhe", "DE", "Europe/Berlin"),
    hyrox("hyrox-geneva-2026-10", "LET'S GO FITNESS HYROX Geneva",
          "2026-10-09", "2026-10-11", "Geneva", "CH", "Europe/Zurich"),
    hyrox("hyrox-valencia-2026-10", "HYROX Valencia",
          "2026-10-16", "2026-10-18", "Valencia", "ES", "Europe/Madrid"),
    hyrox("hyrox-birmingham-2026-10", "HYROX Birmingham",
          "2026-10-27", "2026-11-01", "Birmingham", "GB", "Europe/London"),
    hyrox("hyrox-nice-2026-10", "HYROX Nice",
          "2026-10-29", "2026-11-01", "Nice", "FR", "Europe/Paris"),
    hyrox("hyrox-dusseldorf-2026-11", "HYROX Düsseldorf",
          "2026-11-11", "2026-11-15", "Düsseldorf", "DE", "Europe/Berlin"),
    hyrox("hyrox-barcelona-2026-11", "HYROX Barcelona",
          "2026-11-12", "2026-11-15", "Barcelona", "ES", "Europe/Madrid"),
    hyrox("hyrox-utrecht-2026-11", "HYROX Utrecht",
          "2026-11-26", "2026-11-29", "Utrecht", "NL", "Europe/Amsterdam"),
    hyrox("hyrox-london-2026-12", "HYROX London",
          "2026-12-02", "2026-12-06", "London", "GB", "Europe/London",
          venue="ExCeL London"),
    hyrox("hyrox-milan-2026-12", "HYROX Milan",
          "2026-12-05", "2026-12-06", "Milan", "IT", "Europe/Rome"),
    hyrox("hyrox-frankfurt-2026-12", "HYROX Frankfurt",
          "2026-12-10", "2026-12-13", "Frankfurt", "DE", "Europe/Berlin"),
    hyrox("hyrox-paris-2026-12", "HYROX Paris",
          "2026-12-12", "2026-12-20", "Paris", "FR", "Europe/Paris"),
    hyrox("hyrox-ghent-2026-12", "HYROX Ghent",
          "2026-12-17", "2026-12-20", "Ghent", "BE", "Europe/Brussels"),

    # ATHX 2026
    athx("athx-dublin-2026-05", "ATHX Dublin",
         "2026-05-30", "2026-05-30", "Dublin", "IE", "Europe/Dublin",
         venue="RDS Dublin"),
    athx("athx-glasgow-2026-06", "ATHX Glasgow",
         "2026-06-20", "2026-06-21", "Glasgow", "GB", "Europe/London",
         venue="Scottish Event Campus"),
    athx("athx-copenhagen-2026-08", "ATHX Copenhagen",
         "2026-08-15", "2026-08-15", "Copenhagen", "DK", "Europe/Copenhagen",
         venue="Bella Centre"),
    athx("athx-birmingham-2026-08", "ATHX Birmingham",
         "2026-08-22", "2026-08-23", "Birmingham", "GB", "Europe/London",
         venue="NEC Birmingham"),
    athx("athx-barcelona-2026-09", "ATHX Barcelona",
         "2026-09-05", "2026-09-05", "Barcelona", "ES", "Europe/Madrid",
         venue="Fira Barcelona"),
    athx("athx-marseille-2026-09", "ATHX Marseille",
         "2026-09-19", "2026-09-19", "Marseille", "FR", "Europe/Paris",
         venue="Marseille Chanot"),
    athx("athx-liverpool-2026-10", "ATHX Liverpool",
         "2026-10-03", "2026-10-04", "Liverpool", "GB", "Europe/London",
         venue="Exhibition Centre Liverpool"),
    athx("athx-amsterdam-2026-11", "ATHX Amsterdam",
         "2026-11-07", "2026-11-07", "Amsterdam", "NL", "Europe/Amsterdam",
         venue="RAI Amsterdam"),
    athx("athx-lisbon-2026-11", "ATHX Lisbon",
         "2026-11-27", "2026-11-29", "Lisbon", "PT", "Europe/Lisbon",
         venue="Lisbon Exhibition and Congress Centre"),

    # Deadly Dozen 2026 UK season
    deadly("deadly-dozen-macclesfield-2026-04", "Deadly Dozen UK: Macclesfield",
           "2026-04-11", "2026-04-11", "Macclesfield", "GB", "Europe/London",
           venue="Macclesfield Leisure Centre",
           url="https://www.deadlydozen.com/ultimate-fitness-race-track-races/macclesfield-11th-april-2026"),
    deadly("deadly-dozen-cardiff-2026-05", "Deadly Dozen UK: Cardiff",
           "2026-05-30", "2026-05-30", "Cardiff", "GB", "Europe/London",
           venue="Cardiff Metropolitan University",
           url="https://www.deadlydozen.com/ultimate-fitness-race-track-races/cardiff-30th-may-2026"),
    deadly("deadly-dozen-edinburgh-2026-06", "Deadly Dozen UK: Edinburgh",
           "2026-06-20", "2026-06-20", "Edinburgh", "GB", "Europe/London",
           venue="Meadowbank Sports Centre",
           url="https://www.deadlydozen.com/ultimate-fitness-race-track-races/deadly-dozen-meadowbank-sports-centre-20th-june-2026"),
    deadly("deadly-dozen-lee-valley-2026-07", "Deadly Dozen UK: Lee Valley",
           "2026-07-18", "2026-07-18", "London", "GB", "Europe/London",
           venue="Lee Valley Athletics Track",
           url="https://www.deadlydozen.com/ultimate-fitness-race-track-races/deadly-dozen-lea-valley-athletics-track-18th-july-2026"),
    deadly("deadly-dozen-crawley-2026-08", "Deadly Dozen UK: Crawley",
           "2026-08-08", "2026-08-08", "Crawley", "GB", "Europe/London",
           venue="K2 Crawley",
           url="https://www.deadlydozen.com/ultimate-fitness-race-track-races/crawley8th-august-2026"),
    deadly("deadly-dozen-world-championships-2026-09", "Deadly Dozen World Championships",
           "2026-09-05", "2026-09-06", "London", "GB", "Europe/London",
           venue="Crystal Palace National Sports Centre",
           url="https://www.deadlydozen.com/deadly-dozen-world-championship"),
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    removed = 0
    for old in EXAMPLES:
        path = OUT_DIR / old
        if path.exists():
            path.unlink()
            removed += 1

    for slug, content in EVENTS:
        (OUT_DIR / f"{slug}.yml").write_text(content)

    print(f"Removed {removed} example event(s)")
    print(f"Wrote {len(EVENTS)} events to {OUT_DIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
