# Data Schema

Reference for the YAML files that drive HybridCal. Everything you need to know to add an event, a format, a category, or a translation.

If your submission fails CI validation, the error message tells you which file and field. This doc explains *why*.

## Directory layout

```
data/
├── config/
│   ├── site.yml              # Site URLs and defaults
│   ├── formats.yml           # Hybrid sport formats (HYROX, ATHX, ...)
│   ├── categories.yml        # Categories per format
│   └── i18n/
│       ├── de.yml            # German UI strings
│       └── en.yml            # English UI strings
└── events/
    └── <year>/
        └── <slug>.yml        # One file per event
```

One YAML file per event. Filename should match the `slug` field.

## Event schema

### Minimal valid event

```yaml
slug: hyrox-munich-2026-11
name: HYROX Munich
format: hyrox
date_start: 2026-11-14
date_end: 2026-11-15
location:
  city: München
  country: DE
  timezone: Europe/Berlin
url: https://hyrox.com/events/munich
```

### Full event with all optional fields

```yaml
slug: hyrox-munich-2026-11
name: HYROX Munich
format: hyrox

date_start: 2026-11-14
date_end: 2026-11-15

location:
  city: München
  country: DE
  venue: Olympiahalle
  timezone: Europe/Berlin
  lat: 48.1755
  lon: 11.5518

url: https://hyrox.com/events/munich
status: confirmed
source: organizer

categories:
  - singles-pro-men
  - singles-pro-women
  - doubles-mixed
  - relay-mixed

schedule_url: https://hyrox.com/events/munich/schedule
schedule_updated_at: 2026-09-15
schedule:
  - category: singles-pro-men
    day: 2026-11-14
    start_time: "10:00"
  - category: doubles-mixed
    day: 2026-11-15
    start_time: "09:30"

notes: Datum laut Newsletter vom 12.08.2026, vor Saison nochmal verifizieren.
```

### Field reference

| Field | Required | Type | Notes |
|---|---|---|---|
| `slug` | ✅ | string | Unique identifier, lowercase + hyphens. Convention: `<format>-<city>-<year>-<month>`. Used as filename and URL path. |
| `name` | ✅ | string | Display name. Language-neutral — keep what the organizer calls it. |
| `format` | ✅ | string | Must match a key in `data/config/formats.yml`. |
| `date_start` | ✅ | date | ISO format `YYYY-MM-DD`. Local date (no timezone here). |
| `date_end` | ✅ | date | Same date as `date_start` for single-day events. Must be `≥ date_start`. |
| `location.city` | ✅ | string | |
| `location.country` | ✅ | string | ISO 3166-1 alpha-2, uppercase (DE, AT, CH, GB, US, ...). |
| `location.venue` | ⚪ | string | Specific venue name. Omit if unknown. |
| `location.timezone` | ✅ | string | IANA timezone identifier (`Europe/Berlin`, `America/New_York`). DST-safe. |
| `location.lat` | ⚪ | float | Latitude. Will be auto-geocoded if missing. |
| `location.lon` | ⚪ | float | Longitude. Auto-geocoded if missing. |
| `url` | ✅ | string | Official event page. |
| `status` | ⚪ | enum | `confirmed` \| `tentative` \| `cancelled`. Default: `confirmed`. |
| `source` | ⚪ | enum | `organizer` \| `community` \| `scraped`. Default: `community`. Trust signal. |
| `categories` | ⚪ | list[string] | Category IDs from `categories.yml[format]`. |
| `schedule_url` | ⚪ | string | Link to official schedule. |
| `schedule_updated_at` | ⚪ | date | When you last verified the schedule. Shown as trust signal. |
| `schedule` | ⚪ | list[object] | See below. Optional structured timing data. |
| `notes` | ⚪ | string | For maintainers only. Not rendered on the site. |

### Schedule entries

Each entry maps a category to a specific day and start time within the event:

```yaml
schedule:
  - category: singles-pro-men
    day: 2026-11-14
    start_time: "10:00"
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `category` | ✅ | string | Must reference a valid category for this event's format. |
| `day` | ✅ | date | Must fall within `date_start`..`date_end`. |
| `start_time` | ✅ | string | Format `"HH:MM"` in 24-hour notation. Local to `location.timezone`. Quote in YAML to avoid number parsing. |

## Timezone handling

Times are stored **local to the event's timezone**, never in UTC.

```yaml
location:
  timezone: Europe/Berlin   # IANA, validates against tzdata at build time
schedule:
  - start_time: "10:00"     # 10:00 in Europe/Berlin — DST-aware
```

Why: An event happens at the time the organizer announces it. "10:00 Munich time" stays 10:00 regardless of DST. Storing UTC would force you to update the field at every DST transition. The frontend handles user-timezone conversion.

## Cross-references

The validator checks these on every PR:

- `event.format` must exist as a key in `formats.yml`
- Every entry in `event.categories` must exist as a category ID under `categories.yml[event.format]`
- Every `schedule[].category` must also match a valid category
- `location.timezone` must be a valid IANA identifier
- `date_end >= date_start`

A failed cross-reference fails CI (`scripts/validate.py`), and the PR can't merge until fixed.

## Common patterns

### Single-day event

```yaml
date_start: 2026-04-25
date_end: 2026-04-25
```

### Multi-day with categories on different days

```yaml
date_start: 2026-11-14
date_end: 2026-11-15
schedule:
  - category: singles-pro-men
    day: 2026-11-14
    start_time: "10:00"
  - category: doubles-mixed
    day: 2026-11-15
    start_time: "09:30"
```

### Tentative event (info from social media, not officially announced)

```yaml
status: tentative
source: community
notes: Datum laut Instagram-Post von Deadly Dozen vom 12.08.2026.
```

The site shows a "tentative" badge on the listing and detail page.

### Cancelled event

```yaml
status: cancelled
notes: Veranstaltung am 2026-09-10 abgesagt — siehe Mail von ATHX.
```

Stays in the data so historic links keep working.

## Adding a new format

Two steps. Both files live under `data/config/`.

### 1. Define the format in `formats.yml`

```yaml
xyz-race:
  name: XYZ Race
  type: Hybrid Race          # short descriptor
  website: https://xyzrace.com
  description_de: >
    Optionale deutsche Beschreibung, was das Format ist.
  description_en: >
    Optional English description.
```

### 2. Define its categories in `categories.yml`

```yaml
xyz-race:
  - id: singles-rx-men
    label_de: Singles RX Männer
    label_en: Singles RX Men
  - id: singles-rx-women
    label_de: Singles RX Frauen
    label_en: Singles RX Women
```

Convention: category IDs are lowercase + hyphens, gender baked into the ID (`-men`, `-women`, `-mixed`). Pragmatic over pure — keeps filtering simple.

## Configuration files

### `site.yml`

Language-agnostic, non-translatable site config:

```yaml
url: https://hybridcal.com
github_repo: https://github.com/<owner>/hybridcal
tally_form: https://tally.so/r/<form-id>
default_language: de
default_countries: [DE, AT, CH]
```

`default_countries` controls which countries are pre-selected in the filter UI on first visit.

### `i18n/<lang>.yml`

UI strings per language. Add a new language by adding `i18n/<lang>.yml` with the full key set — the build picks it up automatically and produces `dist/<lang>/`.

The site's nav language switcher derives from the set of `i18n/*.yml` files.

## Running validation locally

```bash
python scripts/validate.py
```

Returns 0 if all YAML files are valid and all cross-references resolve. Returns 1 with a list of errors otherwise.

The same script runs in CI on every pull request that touches `data/**` or related Python code.

## Submitting an event

Three paths, in order of friction:

1. **Form** at `/submit` — easiest. No GitHub account needed.
2. **GitHub Issue** using the "Event-Einreichung" template — moderate.
3. **Pull Request** with a new YAML file under `data/events/<year>/` — for tech-savvy contributors. Use an existing event file as your template. Validation runs automatically and tells you immediately if anything's off.
