from pathlib import Path
import yaml

from .models import Event, Format, Category, Site, Region


def load_events(data_dir: Path) -> list[Event]:
    events = []
    for path in sorted((data_dir / "events").rglob("*.yml")):
        with open(path) as f:
            data = yaml.safe_load(f)
        try:
            events.append(Event(**data))
        except Exception as e:
            raise ValueError(f"Failed to load {path}: {e}") from e
    return sorted(events, key=lambda e: e.date_start)


def load_formats(data_dir: Path) -> dict[str, Format]:
    with open(data_dir / "config" / "formats.yml") as f:
        raw = yaml.safe_load(f)
    return {k: Format(**v) for k, v in raw.items()}


def load_categories(data_dir: Path) -> dict[str, list[Category]]:
    with open(data_dir / "config" / "categories.yml") as f:
        raw = yaml.safe_load(f)
    return {
        fmt: [Category(**c) for c in (cats or [])]
        for fmt, cats in raw.items()
    }


def load_site(data_dir: Path) -> Site:
    with open(data_dir / "config" / "site.yml") as f:
        raw = yaml.safe_load(f)
    return Site(**raw)


def load_regions(data_dir: Path) -> list[Region]:
    with open(data_dir / "config" / "regions.yml") as f:
        raw = yaml.safe_load(f) or []
    return [Region(**r) for r in raw]


def load_translations(data_dir: Path) -> dict[str, dict]:
    """Load all i18n YAML files; returns {lang: translations_dict}."""
    i18n_dir = data_dir / "config" / "i18n"
    translations: dict[str, dict] = {}
    for path in sorted(i18n_dir.glob("*.yml")):
        lang = path.stem
        with open(path) as f:
            translations[lang] = yaml.safe_load(f)
    return translations


def validate_cross_references(
    events: list[Event],
    formats: dict[str, Format],
    categories: dict[str, list[Category]],
) -> list[str]:
    """Returns list of error strings; empty if all valid."""
    errors = []
    for event in events:
        if event.format not in formats:
            errors.append(f"{event.slug}: unknown format '{event.format}'")
            continue
        valid_cats = {c.id for c in categories.get(event.format, [])}
        for cat in event.categories:
            if cat not in valid_cats:
                errors.append(
                    f"{event.slug}: unknown category '{cat}' for format '{event.format}'"
                )
        for entry in event.schedule:
            if entry.category not in valid_cats:
                errors.append(
                    f"{event.slug}: schedule references unknown category '{entry.category}'"
                )
    return errors
