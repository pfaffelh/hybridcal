"""Weekly reconciler entry point.

For each registered source plugin:
  1. Fetch normalised SourceRecord list.
  2. Index existing LOCAL events by source_id.
  3. For records matching an existing future event → diff selected fields
     (dates, URL, location coords/venue/timezone) and update the YAML.
  4. For source IDs not in our data → write a new event YAML.
  5. For future events whose source_id is no longer in the source's set →
     list them under "verschwunden" in the PR body (no auto-delete).

Plus a separate URL health check across all future events of every format.

Writes a markdown PR body to either stdout or the path given by
RECONCILE_REPORT (used by the GitHub Actions workflow).
"""
from __future__ import annotations

import importlib
import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from . import (
    EVENTS_DIR, FieldChange, LocalEvent, ReconcileResult, SourceRecord,
    load_local_events, update_yaml_field, write_new_event_yaml,
)
from .url_check import check_all, broken as broken_urls

PLUGINS = {
    "deadly-dozen": "scripts.reconcile.sources.deadly_dozen",
    "deka":         "scripts.reconcile.sources.deka",
}

# Fields the reconciler updates automatically. Order = display order.
TOP_FIELDS = ["date_start", "date_end", "url"]
LOC_FIELDS = ["city", "country", "venue", "timezone", "lat", "lon"]


def _coord_close(a, b) -> bool:
    """True if two coordinates differ by less than ~5m at the equator."""
    if a is None or b is None:
        return a is b
    try:
        return abs(float(a) - float(b)) < 5e-5
    except (TypeError, ValueError):
        return False


def _diff_fields(local: LocalEvent, rec: SourceRecord) -> list[FieldChange]:
    """Compute the set of field changes we'd write. Skips updates where
    the source value is empty/None — we never blank out existing data."""
    changes: list[FieldChange] = []
    if rec.date_start and rec.date_start != local.date_start:
        changes.append(FieldChange("date_start", local.date_start, rec.date_start))
    if rec.date_end and rec.date_end != local.date_end:
        changes.append(FieldChange("date_end", local.date_end, rec.date_end))
    if rec.url and rec.url != (local.data.get("url") or ""):
        changes.append(FieldChange("url", local.data.get("url"), rec.url))

    loc = local.data.get("location") or {}
    for f in LOC_FIELDS:
        new = getattr(rec, f)
        if new in (None, ""):
            continue
        old = loc.get(f)
        same = _coord_close(old, new) if f in ("lat", "lon") else old == new
        if not same:
            changes.append(FieldChange(f"location.{f}", old, new))
    return changes


def _apply_changes(local: LocalEvent, changes: list[FieldChange],
                   dry_run: bool = False) -> None:
    if dry_run:
        return
    for c in changes:
        if c.field.startswith("location."):
            update_yaml_field(local.path, c.field.split(".", 1)[1], c.after, location=True)
        else:
            update_yaml_field(local.path, c.field, c.after)


def _unique_slug(suggested: str, year_dir: Path, day: int | None) -> str:
    """Append the day (or -2/-3...) until we find an unused slug."""
    if not (year_dir / f"{suggested}.yml").exists():
        return suggested
    if day is not None:
        candidate = f"{suggested}-{day:02d}"
        if not (year_dir / f"{candidate}.yml").exists():
            return candidate
    base = suggested
    n = 2
    while (year_dir / f"{base}-{n}.yml").exists():
        n += 1
    return f"{base}-{n}"


def reconcile_format(fmt: str, dry_run: bool = False) -> ReconcileResult:
    mod = importlib.import_module(PLUGINS[fmt])
    records: list[SourceRecord] = mod.fetch()

    locals_ = load_local_events(fmt)
    future = [le for le in locals_ if le.is_future]
    by_sid: dict[str, LocalEvent] = {le.source_id: le for le in future if le.source_id}

    result = ReconcileResult(fmt=fmt)
    source_ids_seen: set[str] = set()

    for rec in records:
        source_ids_seen.add(rec.source_id)
        local = by_sid.get(rec.source_id)
        if local is not None:
            changes = _diff_fields(local, rec)
            if changes:
                _apply_changes(local, changes, dry_run=dry_run)
                from . import EventDiff
                result.updated.append(EventDiff(local=local, record=rec, changes=changes))
            continue

        # No matching local event → new event. Skip past records as
        # safety belt (we never invent past data).
        if rec.date_start and rec.date_start < date.today():
            continue
        year_dir = EVENTS_DIR / str(rec.date_start.year)
        day = rec.date_start.day if rec.date_start else None
        rec.suggested_slug = _unique_slug(rec.suggested_slug, year_dir, day)
        if dry_run:
            result.new_events.append(year_dir / f"{rec.suggested_slug}.yml")
            continue
        try:
            path = write_new_event_yaml(rec, year_dir)
        except FileExistsError as e:
            result.ambiguous.append(f"new-event slug collision on {e}")
            continue
        result.new_events.append(path)

    # Future-events whose source_id is no longer in the source set.
    for sid, le in by_sid.items():
        if sid not in source_ids_seen:
            result.disappeared.append(le)

    return result


# ---------- markdown report ----------

def _fmt_change(c: FieldChange) -> str:
    return f"`{c.field}`: `{c.before!r}` → `{c.after!r}`"


def render_pr_body(results: list[ReconcileResult], url_results) -> str:
    lines: list[str] = []
    lines.append("# HybridCal — wöchentlicher Reconciler-Lauf")
    lines.append("")
    lines.append(f"Stand: {date.today().isoformat()}")
    lines.append("")
    lines.append("Dieser PR wurde automatisch erstellt. Prüfen, dann mergen.")
    lines.append("Vergangene Events werden vom Reconciler **nicht angefasst**.")
    lines.append("")

    any_data = any(r.updated or r.new_events or r.disappeared or r.ambiguous for r in results)
    bs = broken_urls(url_results)

    if not any_data and not bs:
        lines.append("## Keine Änderungen")
        lines.append("")
        lines.append(f"{len(url_results)} URLs geprüft, alle OK.")
        return "\n".join(lines)

    for r in results:
        if not (r.updated or r.new_events or r.disappeared or r.ambiguous):
            continue
        lines.append(f"## Format: {r.fmt}")
        lines.append("")
        if r.updated:
            lines.append(f"### Daten-Updates ({len(r.updated)})")
            for d in r.updated:
                lines.append(f"- **{d.local.path.name}** (`{d.local.slug}`)")
                for c in d.changes:
                    lines.append(f"  - {_fmt_change(c)}")
            lines.append("")
        if r.new_events:
            lines.append(f"### Neue Events ({len(r.new_events)})")
            for p in r.new_events:
                lines.append(f"- `{p.relative_to(EVENTS_DIR.parent.parent)}`")
            lines.append("")
        if r.disappeared:
            lines.append(f"### Nicht mehr in der Quelle ({len(r.disappeared)})")
            lines.append("Quelle liefert diese source_id nicht mehr — manuell prüfen, "
                         "ob das Event verschoben/abgesagt/umbenannt wurde.")
            for le in r.disappeared:
                lines.append(f"- `{le.path.name}` (source_id `{le.source_id}`)")
            lines.append("")
        if r.ambiguous:
            lines.append("### Hinweise")
            for note in r.ambiguous:
                lines.append(f"- {note}")
            lines.append("")

    lines.append(f"## URL-Health-Check ({len(url_results)} Events geprüft)")
    if not bs:
        lines.append("")
        lines.append("Alle URLs liefern 2xx/3xx. ")
    else:
        lines.append("")
        lines.append(f"{len(bs)} URLs liefern Fehler — manuell prüfen und ggf. ersetzen:")
        by_fmt: dict[str, list] = defaultdict(list)
        for r in bs:
            by_fmt[r.event.data.get("format", "?")].append(r)
        for fmt in sorted(by_fmt):
            lines.append("")
            lines.append(f"### {fmt}")
            for r in by_fmt[fmt]:
                lines.append(f"- `{r.event.path.name}` — **{r.note}** — {r.url}")

    return "\n".join(lines)


def main() -> int:
    only = os.environ.get("RECONCILE_ONLY") or None
    dry_run = "--dry-run" in sys.argv or os.environ.get("RECONCILE_DRY_RUN") == "1"
    fmts = [only] if only else sorted(PLUGINS.keys())

    if dry_run:
        print("[*] dry-run: no YAMLs will be modified", file=sys.stderr)

    results: list[ReconcileResult] = []
    for fmt in fmts:
        print(f"[{fmt}] reconciling…", file=sys.stderr)
        try:
            r = reconcile_format(fmt, dry_run=dry_run)
        except SystemExit as e:
            print(f"[{fmt}] skipped: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"[{fmt}] FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        results.append(r)
        print(f"[{fmt}] {len(r.updated)} updated · "
              f"{len(r.new_events)} new · "
              f"{len(r.disappeared)} disappeared", file=sys.stderr)

    print("[*] running URL health check…", file=sys.stderr)
    url_results = check_all()
    print(f"[*] {len(url_results)} URLs checked, "
          f"{len(broken_urls(url_results))} broken", file=sys.stderr)

    body = render_pr_body(results, url_results)
    out = os.environ.get("RECONCILE_REPORT")
    if out:
        Path(out).write_text(body)
        print(f"wrote {out}", file=sys.stderr)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
