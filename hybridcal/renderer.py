from pathlib import Path
import json
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import Event, Format, Category, Site, Region


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
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    languages = list(translations.keys())
    default_lang = site.default_language

    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html"]),
    )

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
            (events_out / f"{event.slug}.html").write_text(
                env.get_template("event.html").render(
                    **common,
                    event=event,
                    format=formats_for_lang[event.format],
                    categories=cats,
                    current_path=f"/events/{event.slug}.html",
                )
            )

        for fmt_id, fmt in formats_for_lang.items():
            fmt_events = [e for e in events if e.format == fmt_id]
            (lang_dir / f"{fmt_id}.html").write_text(
                env.get_template("format.html").render(
                    **common,
                    format=fmt,
                    format_id=fmt_id,
                    events=fmt_events,
                    categories=categories_dict.get(fmt_id, []),
                    current_path=f"/{fmt_id}.html",
                )
            )

        for page in ["about", "submit"]:
            (lang_dir / f"{page}.html").write_text(
                env.get_template(f"{page}.html").render(
                    **common,
                    current_path=f"/{page}.html",
                )
            )

    (out_dir / "index.html").write_text(
        f"""<!DOCTYPE html>
<html lang="{default_lang}">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=/{default_lang}/">
  <link rel="canonical" href="/{default_lang}/">
  <title>HybridCal</title>
</head>
<body>
  <p><a href="/{default_lang}/">→ HybridCal</a></p>
</body>
</html>
"""
    )

    events_json = [
        {
            "slug": e.slug,
            "name": e.name,
            "format": e.format,
            "date_start": e.date_start.isoformat(),
            "date_end": e.date_end.isoformat(),
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
