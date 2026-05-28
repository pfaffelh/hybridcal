from pathlib import Path
from datetime import date
import json
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
import markdown as md

from .models import Event, Format, Category, Site, Region


def _event_description(event: Event, format_name: str, format_type: str, lang: str) -> str:
    """One-line text for <meta name=description>. Plain text, no HTML."""
    if lang == "de":
        date_part = (
            f"am {event.date_start.strftime('%d.%m.%Y')}"
            if event.date_start and event.date_start == event.date_end
            else (
                f"vom {event.date_start.strftime('%d.%m.%Y')} bis {event.date_end.strftime('%d.%m.%Y')}"
                if event.date_start and event.date_end
                else "Termin noch offen"
            )
        )
        loc = f"{event.location.city}, {event.location.country}"
        return f"{event.name} {date_part} in {loc}. {format_name} — {format_type}."
    else:
        date_part = (
            f"on {event.date_start.strftime('%b %d, %Y')}"
            if event.date_start and event.date_start == event.date_end
            else (
                f"from {event.date_start.strftime('%b %d')} to {event.date_end.strftime('%b %d, %Y')}"
                if event.date_start and event.date_end
                else "Date TBA"
            )
        )
        loc = f"{event.location.city}, {event.location.country}"
        return f"{event.name} {date_part} in {loc}. {format_name} — {format_type}."


def _event_json_ld(event: Event, format_data: dict, site_url: str, lang: str) -> dict | None:
    """Schema.org Event markup. Returns None if event lacks required fields
    (Google requires startDate)."""
    if event.date_start is None:
        return None
    status_map = {
        "confirmed": "https://schema.org/EventScheduled",
        "tentative": "https://schema.org/EventScheduled",
        "cancelled": "https://schema.org/EventCancelled",
    }
    data: dict = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": event.name,
        "startDate": event.date_start.isoformat(),
        "eventStatus": status_map.get(event.status, "https://schema.org/EventScheduled"),
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "url": f"{site_url}/{lang}/events/{event.slug}.html",
        "image": f"{site_url}/static/logo/formats/{event.format}.png",
        "location": {
            "@type": "Place",
            "name": event.location.venue or event.location.city,
            "address": {
                "@type": "PostalAddress",
                "addressLocality": event.location.city,
                "addressCountry": event.location.country,
            },
        },
        "offers": {
            "@type": "Offer",
            "url": event.url,
            "availability": "https://schema.org/InStock",
        },
    }
    if event.date_end:
        data["endDate"] = event.date_end.isoformat()
    if event.location.lat is not None and event.location.lon is not None:
        data["location"]["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": event.location.lat,
            "longitude": event.location.lon,
        }
    # Organizer: always set the series name; add url only when known.
    organizer = {"@type": "Organization", "name": format_data["name"]}
    if format_data.get("website"):
        organizer["url"] = format_data["website"]
    data["organizer"] = organizer
    return data


def _breadcrumb_json_ld(event: Event, fmt_name: str, fmt_id: str,
                        site_url: str, lang: str) -> dict:
    """schema.org BreadcrumbList: HybridCal › <Format> › <Event>."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "HybridCal",
             "item": f"{site_url}/{lang}/"},
            {"@type": "ListItem", "position": 2, "name": fmt_name,
             "item": f"{site_url}/{lang}/{fmt_id}.html"},
            # Last crumb = current page → no "item" per Google guidance.
            {"@type": "ListItem", "position": 3, "name": event.name},
        ],
    }


def _format_item_list(fmt_events: list[Event], fmt_name: str,
                      site_url: str, lang: str) -> dict | None:
    """schema.org ItemList of a format's upcoming events (list-page markup)."""
    items = []
    for i, e in enumerate(fmt_events, start=1):
        items.append({
            "@type": "ListItem",
            "position": i,
            "url": f"{site_url}/{lang}/events/{e.slug}.html",
            "name": e.name,
        })
    if not items:
        return None
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"{fmt_name} — upcoming events",
        "numberOfItems": len(items),
        "itemListElement": items,
    }


def _write_sitemap(out_dir: Path, site_url: str, languages: list[str],
                   events: list[Event], formats: dict, today: date) -> None:
    """Generate sitemap.xml with hreflang alternate links."""
    paths_per_lang = ["/", "/formats.html", "/about.html", "/submit.html", "/impressum.html", "/privacy.html"]
    for fmt_id in formats:
        paths_per_lang.append(f"/{fmt_id}.html")
    for event in events:
        paths_per_lang.append(f"/events/{event.slug}.html")

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    # One entry per language-page combination
    for path in paths_per_lang:
        for lang in languages:
            lines.append("  <url>")
            lines.append(f"    <loc>{site_url}/{lang}{path}</loc>")
            lines.append(f"    <lastmod>{today.isoformat()}</lastmod>")
            lines.append(f"    <changefreq>{'weekly' if path.startswith('/events/') else 'daily' if path == '/' else 'monthly'}</changefreq>")
            lines.append(f"    <priority>{'0.9' if path.startswith('/events/') else '1.0' if path == '/' else '0.6'}</priority>")
            for other in languages:
                lines.append(f'    <xhtml:link rel="alternate" hreflang="{other}" href="{site_url}/{other}{path}"/>')
            lines.append("  </url>")
    lines.append("</urlset>")
    (out_dir / "sitemap.xml").write_text("\n".join(lines))


def _write_robots(out_dir: Path, site_url: str) -> None:
    (out_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n"
    )


def _fmt_date_for(lang: str):
    def f(d):
        if not d:
            return ""
        if lang == "en":
            return d.strftime("%b %d, %Y")
        return d.strftime("%d.%m.%Y")
    return f


def event_region(country: str, regions: list[Region]) -> str:
    """Map an event's country to a region ID. Falls back to 'world'."""
    for r in regions:
        if country in r.countries:
            return r.id
    return "world"


def render_site(
    events: list[Event],
    formats: dict[str, Format],
    categories: dict[str, list[Category]],
    translations: dict[str, dict],
    site: Site,
    regions: list[Region],
    out_dir: Path,
    templates_dir: Path,
    static_dir: Path,
    last_data_update=None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    languages = list(translations.keys())
    default_lang = site.default_language

    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html"]),
    )
    # Don't sort dict keys when serializing to JSON — preserve insertion
    # order (used for format dropdown order in the filter UI).
    env.policies["json.dumps_kwargs"] = {"sort_keys": False}

    def _markdown(text):
        if not text:
            return ""
        return Markup(md.markdown(text, extensions=["extra", "sane_lists"]))
    env.filters["markdown"] = _markdown

    static_out = out_dir / "static"
    if static_out.exists():
        shutil.rmtree(static_out)
    shutil.copytree(static_dir, static_out)

    formats_dict = {k: f.model_dump() for k, f in formats.items()}
    categories_dict = {
        k: [c.model_dump() for c in cats] for k, cats in categories.items()
    }
    site_dict = site.model_dump()
    regions_dump = [r.model_dump() for r in regions]

    def localized_formats(lang: str) -> dict:
        """Pre-resolve format.name per language (uses name_de/name_en if set)."""
        out = {}
        for k, f in formats_dict.items():
            localized_name = f.get(f"name_{lang}") or f["name"]
            out[k] = {**f, "name": localized_name}
        return out

    def localized_regions(lang: str) -> list[dict]:
        """Add a localized 'name' field to each region for templates/JS."""
        return [
            {**r, "name": r[f"name_{lang}"]}
            for r in regions_dump
        ]

    for lang in languages:
        env.filters["fmt_date"] = _fmt_date_for(lang)
        t = translations[lang]
        lang_dir = out_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)

        formats_for_lang = localized_formats(lang)
        regions_for_lang = localized_regions(lang)

        common = {
            "lang": lang,
            "t": t,
            "site": site_dict,
            "formats": formats_for_lang,
            "formats_json": formats_for_lang,
            "regions_json": regions_for_lang,
            "last_data_update": last_data_update,
            "current_year": date.today().year,
        }

        (lang_dir / "index.html").write_text(
            env.get_template("index.html").render(
                **common,
                events=events,
                current_path="/",
            )
        )

        events_out = lang_dir / "events"
        events_out.mkdir(exist_ok=True)
        for event in events:
            cats = categories_dict.get(event.format, [])
            fmt_for_lang = formats_for_lang[event.format]
            description = _event_description(event, fmt_for_lang["name"], fmt_for_lang["type"], lang)
            (events_out / f"{event.slug}.html").write_text(
                env.get_template("event.html").render(
                    **common,
                    event=event,
                    format=fmt_for_lang,
                    categories=cats,
                    current_path=f"/events/{event.slug}.html",
                    event_description=description,
                    event_json_ld=_event_json_ld(event, fmt_for_lang, site.url, lang),
                    breadcrumb_json_ld=_breadcrumb_json_ld(
                        event, fmt_for_lang["name"], event.format, site.url, lang),
                )
            )

        today = date.today()
        for fmt_id, fmt in formats_for_lang.items():
            fmt_events = [
                e for e in events
                if e.format == fmt_id
                and (e.is_tba or (e.date_end and e.date_end >= today))
            ]
            (lang_dir / f"{fmt_id}.html").write_text(
                env.get_template("format.html").render(
                    **common,
                    format=fmt,
                    format_id=fmt_id,
                    events=fmt_events,
                    categories=categories_dict.get(fmt_id, []),
                    current_path=f"/{fmt_id}.html",
                    item_list_json_ld=_format_item_list(
                        fmt_events, fmt["name"], site.url, lang),
                )
            )

        format_counts = {
            fmt_id: sum(1 for e in events if e.format == fmt_id)
            for fmt_id in formats_for_lang
        }
        (lang_dir / "formats.html").write_text(
            env.get_template("formats.html").render(
                **common,
                format_counts=format_counts,
                current_path="/formats.html",
            )
        )

        for page in ["about", "submit", "impressum", "privacy"]:
            (lang_dir / f"{page}.html").write_text(
                env.get_template(f"{page}.html").render(
                    **common,
                    current_path=f"/{page}.html",
                )
            )

    base = site.base_path or ""
    (out_dir / "index.html").write_text(
        f"""<!DOCTYPE html>
<html lang="{default_lang}">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url={base}/{default_lang}/">
  <link rel="canonical" href="{base}/{default_lang}/">
  <title>HybridCal</title>
</head>
<body>
  <p><a href="{base}/{default_lang}/">→ HybridCal</a></p>
</body>
</html>
"""
    )

    today = date.today()
    _write_sitemap(out_dir, site.url, languages, events, formats_dict, today)
    _write_robots(out_dir, site.url)

    events_json = [
        {
            "slug": e.slug,
            "name": e.name,
            "format": e.format,
            "date_start": e.date_start.isoformat() if e.date_start else None,
            "date_end": e.date_end.isoformat() if e.date_end else None,
            "location": {
                "city": e.location.city,
                "country": e.location.country,
                "venue": e.location.venue,
                "lat": e.location.lat,
                "lon": e.location.lon,
            },
            "region": event_region(e.location.country, regions),
            "url": e.url,
            "status": e.status,
            "categories": e.categories,
        }
        for e in events
    ]
    (out_dir / "events.json").write_text(json.dumps(events_json, ensure_ascii=False))
