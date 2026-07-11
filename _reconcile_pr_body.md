# HybridCal — wöchentlicher Reconciler-Lauf

Stand: 2026-07-11

Dieser PR wurde automatisch erstellt. Prüfen, dann mergen.
Vergangene Events werden vom Reconciler **nicht angefasst**.

## Format: deadly-dozen

### Nicht mehr in der Quelle (1)
Quelle liefert diese source_id nicht mehr — manuell prüfen, ob das Event verschoben/abgesagt/umbenannt wurde.
- `deadly-dozen-stoke-on-trent-2026-07.yml` (source_id `26e3b27b-60c6-4da9-ad89-ea13fbace988`)

_41 Records gefiltert (Affiliate-Gym-Records: Deadly Barbell / Deadly ERG / DFT etc. an Partner-Gyms — passen nicht ins Hybrid-Profil)._

## Format: deka

### Daten-Updates (1)
- **deka-chicago-2026-07.yml** (`deka-chicago-2026-07`)
  - `url`: `'https://tickets-usdk.spartan.com/event/1999'` → `'https://tickets-usdk.spartan.com/event/2000'`

## Format: hyrox

### Daten-Updates (3)
- **hyrox-tampa-2026-10.yml** (`hyrox-tampa-2026-10`)
  - `date_start`: `datetime.date(2026, 10, 23)` → `datetime.date(2026, 10, 22)`
- **hyrox-melbourne-2026-tba.yml** (`hyrox-melbourne-2026-tba`)
  - `date_start`: `None` → `datetime.date(2026, 12, 9)`
  - `date_end`: `None` → `datetime.date(2026, 12, 13)`
- **hyrox-nashville-2026-12.yml** (`hyrox-nashville-2026-12`)
  - `date_start`: `datetime.date(2026, 12, 10)` → `datetime.date(2026, 12, 9)`

_4 Records gefiltert (Youngstars-Events (Jugend 12-15) — eigene Zielgruppe, nicht im Kalenderprofil)._

## URL-Health-Check (181 Events geprüft)

1 URLs liefern Fehler — manuell prüfen und ggf. ersetzen:

### other
- `bfm-games-loerrach-2026-09.yml` — **HEAD 500** — https://bfmgames.de/