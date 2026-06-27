# HybridCal — wöchentlicher Reconciler-Lauf

Stand: 2026-06-27

Dieser PR wurde automatisch erstellt. Prüfen, dann mergen.
Vergangene Events werden vom Reconciler **nicht angefasst**.

## Format: athx

### Daten-Updates (2)
- **athx-marseille-2027-09.yml** (`athx-marseille-2027-09`)
  - `date_start`: `datetime.date(2027, 9, 11)` → `datetime.date(2027, 9, 10)`
- **athx-bilbao-2027-10.yml** (`athx-bilbao-2027-10`)
  - `date_start`: `datetime.date(2027, 10, 9)` → `datetime.date(2027, 11, 6)`
  - `date_end`: `datetime.date(2027, 10, 9)` → `datetime.date(2027, 11, 6)`

## Format: deadly-dozen

### Nicht mehr in der Quelle (1)
Quelle liefert diese source_id nicht mehr — manuell prüfen, ob das Event verschoben/abgesagt/umbenannt wurde.
- `deadly-dozen-stoke-on-trent-2026-07.yml` (source_id `26e3b27b-60c6-4da9-ad89-ea13fbace988`)

_45 Records gefiltert (Affiliate-Gym-Records: Deadly Barbell / Deadly ERG / DFT etc. an Partner-Gyms — passen nicht ins Hybrid-Profil)._

## Format: deka

### Daten-Updates (1)
- **deka-derby-2026-09-12.yml** (`deka-derby-2026-09-12`)
  - `date_start`: `datetime.date(2026, 9, 12)` → `datetime.date(2026, 9, 11)`

### Neue Events (1)
- `data/events/2027/deka-lisboa-2027-05.yml`

## Format: hyrox

### Daten-Updates (2)
- **hyrox-barcelona-2026-11.yml** (`hyrox-barcelona-2026-11`)
  - `date_start`: `datetime.date(2026, 11, 12)` → `datetime.date(2026, 11, 11)`
- **hyrox-singapore-2026-11.yml** (`hyrox-singapore-2026-11`)
  - `date_start`: `datetime.date(2026, 11, 27)` → `datetime.date(2026, 11, 26)`

_4 Records gefiltert (Youngstars-Events (Jugend 12-15) — eigene Zielgruppe, nicht im Kalenderprofil)._

## URL-Health-Check (188 Events geprüft)

Alle URLs liefern 2xx/3xx. 