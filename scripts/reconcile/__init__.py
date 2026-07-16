"""Reconciler library — common data shapes and helpers.

Per-format plugins under sources/ produce SourceRecord lists. The reconciler
compares them against our existing YAMLs (matched by source_id) and emits:

  - field updates on existing future events (regex-targeted YAML edits)
  - newly-discovered events as full YAML files
  - a markdown summary suitable for the PR body
  - a list of broken URLs (from the separate url_check)

Past events (date_end < today) are NEVER modified.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EVENTS_DIR = ROOT / "data" / "events"


# ---------- normalisation helpers ----------

def deaccent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def normalise_city(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", deaccent(s).lower())


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", deaccent(s).lower()).strip("-")


# ---------- normalised record from an external source ----------

@dataclass
class SourceRecord:
    """One event as returned by a per-format source plugin."""
    source_id: str        # stable upstream id (string form)
    format: str           # 'deadly-dozen', 'deka', ...
    name: str
    date_start: date | None
    date_end: date | None
    city: str
    country: str          # ISO-3166-1 alpha-2
    venue: str | None = None
    timezone: str = ""
    lat: float | None = None
    lon: float | None = None
    url: str = ""
    categories: list[str] = field(default_factory=list)
    suggested_slug: str = ""  # used when creating a new YAML
    # True if this record looks like a flagship-brand event worth
    # auto-creating as a new YAML. False for affiliate / micro events
    # that should only appear in the PR body's candidate list. Set by
    # the plugin; default True keeps existing plugins unaffected.
    is_main_brand: bool = True
    # Why this record wasn't auto-created, for the PR body. Only set it
    # when a human should act (e.g. an event we couldn't resolve); the
    # deliberate silent drops (affiliate gyms) leave it empty.
    skip_note: str = ""

    def end_date(self) -> date | None:
        return self.date_end or self.date_start


# ---------- existing YAML loading ----------

@dataclass
class LocalEvent:
    path: Path
    data: dict

    @property
    def slug(self) -> str:
        return self.data.get("slug", "")

    @property
    def source_id(self) -> str | None:
        sid = self.data.get("source_id")
        return str(sid) if sid is not None else None

    @property
    def date_start(self) -> date | None:
        return self.data.get("date_start")

    @property
    def date_end(self) -> date | None:
        return self.data.get("date_end") or self.data.get("date_start")

    @property
    def city(self) -> str:
        return (self.data.get("location") or {}).get("city", "")

    @property
    def is_future(self) -> bool:
        de = self.date_end
        return de is None or de >= date.today()


def load_local_events(fmt: str | None = None) -> list[LocalEvent]:
    """Load every YAML under data/events/. Optionally filter by format."""
    out: list[LocalEvent] = []
    for p in sorted(EVENTS_DIR.rglob("*.yml")):
        d = yaml.safe_load(p.read_text())
        if fmt is not None and d.get("format") != fmt:
            continue
        out.append(LocalEvent(path=p, data=d))
    return out


# ---------- targeted YAML field updates (preserves rest of the file) ----------

_SCALAR_RE = {
    "date_start": r"^date_start:.*$",
    "date_end":   r"^date_end:.*$",
    "url":        r"^url:.*$",
    "source_id":  r"^source_id:.*$",
    "status":     r"^status:.*$",
}
_LOC_SCALAR_RE = {
    "city":     r"^  city:.*$",
    "country":  r"^  country:.*$",
    "venue":    r"^  venue:.*$",
    "timezone": r"^  timezone:.*$",
    "lat":      r"^  lat:.*$",
    "lon":      r"^  lon:.*$",
}


def _yaml_quote(v) -> str:
    """Single-line YAML value emitter, quoted only when needed."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, date):
        return v.isoformat()
    s = str(v)
    # Numeric-looking strings must stay quoted, otherwise YAML readers
    # would parse them as int/float and break Pydantic str fields.
    if s == "" or any(c in s for c in ':#"\'\n,[]{}') or s.strip() != s \
            or re.match(r"^-?\d+(\.\d+)?$", s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def update_yaml_field(path: Path, field: str, value, location: bool = False) -> bool:
    """Update a single scalar field in a YAML file, preserving everything
    else. Returns True if the file was modified."""
    table = _LOC_SCALAR_RE if location else _SCALAR_RE
    pat = table.get(field)
    if pat is None:
        raise ValueError(f"no regex for field {field!r}")
    line = ("  " if location else "") + f"{field}: {_yaml_quote(value)}"
    txt = path.read_text()
    new, n = re.subn(pat, line, txt, count=1, flags=re.M)
    if n == 0:
        # field absent — append at top level (or under location: for nested)
        if location:
            new = re.sub(r"(^location:.*$)",
                         r"\1\n" + line, txt, count=1, flags=re.M)
            if new == txt:
                return False
        else:
            new = txt.rstrip("\n") + "\n" + line + "\n"
    if new == txt:
        return False
    path.write_text(new)
    return True


def write_new_event_yaml(rec: SourceRecord, year_dir: Path) -> Path:
    """Materialise a fresh YAML for a newly-discovered event."""
    year_dir.mkdir(parents=True, exist_ok=True)
    out = year_dir / f"{rec.suggested_slug}.yml"
    if out.exists():
        # avoid clobber; the caller should have given a unique slug
        raise FileExistsError(out)
    lines = [
        f"slug: {rec.suggested_slug}",
        f"name: {_yaml_quote(rec.name)}",
        f"format: {rec.format}",
        f"date_start: {rec.date_start.isoformat() if rec.date_start else 'null'}",
        f"date_end: {(rec.date_end or rec.date_start).isoformat() if rec.date_end or rec.date_start else 'null'}",
        "location:",
        f"  city: {_yaml_quote(rec.city)}",
        f'  country: "{rec.country}"',
    ]
    if rec.venue:
        lines.append(f"  venue: {_yaml_quote(rec.venue)}")
    if rec.timezone:
        lines.append(f"  timezone: {rec.timezone}")
    if rec.lat is not None:
        lines.append(f"  lat: {rec.lat}")
        lines.append(f"  lon: {rec.lon}")
    lines.append(f"url: {_yaml_quote(rec.url)}")
    lines.append("status: confirmed")
    lines.append("source: scraped")
    lines.append(f"source_id: {_yaml_quote(rec.source_id)}")
    if rec.categories:
        lines.append("categories:")
        for c in rec.categories:
            lines.append(f"  - {c}")
    else:
        lines.append("categories: []")
    out.write_text("\n".join(lines) + "\n")
    return out


# ---------- diff & report types ----------

@dataclass
class FieldChange:
    field: str            # e.g. "date_start", "location.lat", "url"
    before: object
    after: object


@dataclass
class EventDiff:
    local: LocalEvent
    record: SourceRecord
    changes: list[FieldChange] = field(default_factory=list)


@dataclass
class ReconcileResult:
    fmt: str
    updated: list[EventDiff] = field(default_factory=list)   # existing future events whose fields changed
    new_events: list[Path] = field(default_factory=list)     # written new YAMLs
    disappeared: list[LocalEvent] = field(default_factory=list)  # future events no longer in source
    ambiguous: list[str] = field(default_factory=list)       # human-readable notes
    filtered_non_main_brand: int = 0  # rows skipped because !is_main_brand
