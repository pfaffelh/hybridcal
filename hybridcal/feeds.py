from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo

from ics import Calendar, Event as IcsEvent
from feedgen.feed import FeedGenerator

from .models import Event


def write_ics(events: list[Event], out_path: Path, site_url: str) -> None:
    cal = Calendar()
    for e in events:
        # ICS requires concrete dates; skip TBA events.
        if e.date_start is None or e.date_end is None:
            continue
        ics_event = IcsEvent()
        ics_event.name = e.name
        tz = ZoneInfo(e.location.timezone)
        ics_event.begin = datetime.combine(e.date_start, time(0, 0), tzinfo=tz)
        ics_event.end = datetime.combine(e.date_end, time(23, 59), tzinfo=tz)
        venue = e.location.venue
        ics_event.location = (
            f"{venue}, {e.location.city}" if venue else e.location.city
        )
        ics_event.url = e.url
        ics_event.uid = f"{e.slug}@hybridcal.com"
        ics_event.description = f"Format: {e.format}"
        cal.events.add(ics_event)
    out_path.write_text(cal.serialize())


def write_rss(events: list[Event], out_path: Path, site_url: str) -> None:
    fg = FeedGenerator()
    fg.id(site_url)
    fg.title("HybridCal — Upcoming Hybrid Sport Events")
    fg.link(href=site_url, rel="alternate")
    fg.description(
        "Community-driven calendar for HYROX, ATHX, Deadly Dozen, DEKA and more."
    )
    fg.language("de")

    today = datetime.now().date()
    # Upcoming = no date_end yet, OR date_end >= today
    upcoming = [e for e in events if e.date_end is None or e.date_end >= today]
    # Dated first (chronological), then TBA at end
    from datetime import date as _date
    _FAR = _date(9999, 1, 1)
    upcoming.sort(key=lambda e: (e.date_start is None, e.date_start or _FAR))
    for e in upcoming[:50]:
        entry = fg.add_entry()
        entry.id(f"{site_url}/events/{e.slug}.html")
        if e.date_start:
            date_part = e.date_start.strftime("%d.%m.%Y")
            range_part = (
                f" – {e.date_end.strftime('%d.%m.%Y')}"
                if e.date_end and e.date_end != e.date_start
                else ""
            )
        else:
            date_part = "TBA"
            range_part = ""
        entry.title(f"{e.name} — {date_part}")
        entry.link(href=f"{site_url}/events/{e.slug}.html")
        entry.description(
            f"{e.location.city}, {e.location.country} · {date_part}{range_part}"
        )
    fg.rss_file(str(out_path))
