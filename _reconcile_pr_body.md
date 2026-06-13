# HybridCal — wöchentlicher Reconciler-Lauf

Stand: 2026-06-13

Dieser PR wurde automatisch erstellt. Prüfen, dann mergen.
Vergangene Events werden vom Reconciler **nicht angefasst**.

## Format: athx

### Daten-Updates (5)
- **athx-glasgow-2027-06.yml** (`athx-glasgow-2027-06`)
  - `url`: `'https://athxgames.com/events'` → `'https://athxgames.com/events/01krwy8tkc67qrvhyxrkf7rr2a'`
- **athx-copenhagen-2027-07.yml** (`athx-copenhagen-2027-07`)
  - `url`: `'https://athxgames.com/events'` → `'https://athxgames.com/events/01krwyb4rb5gawjp5w64cn32wk'`
- **athx-marseille-2027-09.yml** (`athx-marseille-2027-09`)
  - `url`: `'https://athxgames.com/events'` → `'https://athxgames.com/events/01krwye8tdjj9gscaw7xht2sme'`
- **athx-amsterdam-2027-10.yml** (`athx-amsterdam-2027-10`)
  - `url`: `'https://athxgames.com/events'` → `'https://athxgames.com/events/01krwyg5j85v7nrbwh5eak1tb9'`
- **athx-liverpool-2027-10.yml** (`athx-liverpool-2027-10`)
  - `url`: `'https://athxgames.com/events'` → `'https://athxgames.com/events/01krwyfbxhpxxdyn42cas8bcd1'`

### Neue Events (2)
- `data/events/2027/athx-milan-2027-03.yml`
- `data/events/2027/athx-montpellier-2027-05.yml`

## Format: deadly-dozen

### Neue Events (1)
- `data/events/2026/deadly-dozen-marsa-2026-11.yml`

### Nicht mehr in der Quelle (1)
Quelle liefert diese source_id nicht mehr — manuell prüfen, ob das Event verschoben/abgesagt/umbenannt wurde.
- `deadly-dozen-stoke-on-trent-2026-07.yml` (source_id `26e3b27b-60c6-4da9-ad89-ea13fbace988`)

_44 Records gefiltert (Affiliate-Gym-Records: Deadly Barbell / Deadly ERG / DFT etc. an Partner-Gyms — passen nicht ins Hybrid-Profil)._

## Format: deka

### Neue Events (2)
- `data/events/2026/deka-austin-2026-09.yml`
- `data/events/2026/deka-geneve-2026-11.yml`

## Format: hyrox

### Daten-Updates (3)
- **hyrox-rome-2026-09.yml** (`hyrox-rome-2026-09`)
  - `date_start`: `datetime.date(2026, 9, 24)` → `datetime.date(2026, 9, 23)`
- **hyrox-anaheim-2026-12.yml** (`hyrox-anaheim-2026-12`)
  - `date_start`: `datetime.date(2026, 12, 4)` → `datetime.date(2026, 12, 3)`
- **hyrox-stockholm-intersport-2026-tba.yml** (`hyrox-stockholm-intersport-2026-tba`)
  - `date_start`: `None` → `datetime.date(2026, 12, 10)`
  - `date_end`: `None` → `datetime.date(2026, 12, 13)`

_2 Records gefiltert (Youngstars-Events (Jugend 12-15) — eigene Zielgruppe, nicht im Kalenderprofil)._

## URL-Health-Check (193 Events geprüft)

Alle URLs liefern 2xx/3xx. 