# HybridCal — wöchentlicher Reconciler-Lauf

Stand: 2026-06-06

Dieser PR wurde automatisch erstellt. Prüfen, dann mergen.
Vergangene Events werden vom Reconciler **nicht angefasst**.

## Format: deadly-dozen

### Daten-Updates (1)
- **deadly-dozen-lee-valley-2026-07.yml** (`deadly-dozen-lee-valley-2026-07`)
  - `url`: `'https://www.deadlydozen.com/ultimate-fitness-race-track-races/deadly-dozen-lea-valley-athletics-track-18th-july-2026'` → `'https://in.njuko.com/deadly-dozen-lee-valley---18th-july-261751149039951'`

### Nicht mehr in der Quelle (1)
Quelle liefert diese source_id nicht mehr — manuell prüfen, ob das Event verschoben/abgesagt/umbenannt wurde.
- `deadly-dozen-stoke-on-trent-2026-07.yml` (source_id `26e3b27b-60c6-4da9-ad89-ea13fbace988`)

_44 Affiliate-Gym-Records wurden ausgefiltert (Deadly Barbell / Deadly ERG / DFT etc. an Partner-Gyms — passen nicht ins Hybrid-Profil)._

## Format: deka

### Daten-Updates (1)
- **deka-philadelphia-2026-08.yml** (`deka-philadelphia-2026-08`)
  - `date_start`: `datetime.date(2026, 8, 7)` → `datetime.date(2026, 8, 8)`

### Neue Events (1)
- `data/events/2026/deka-beijing-2026-06.yml`

## URL-Health-Check (176 Events geprüft)

3 URLs liefern Fehler — manuell prüfen und ggf. ersetzen:

### turf-games
- `turf-games-gold-coast-engine-2026-09.yml` — **HEAD 503** — https://turfgames.com/blogs/other/gold-coast-engine-2026
- `turf-games-gold-coast-summer-festival-2026-09.yml` — **HEAD 503** — https://turfgames.com/pages/gold-coast-2026
- `turf-games-singapore-2026-08.yml` — **HEAD 503** — https://turfgames.com/pages/singapore-2026