# HybridCal

A community-driven calendar for hybrid sport events — HYROX, ATHX, Deadly Dozen, DEKA, and more.

Live: https://hybridcal.de

## Was das ist

Ein kostenloser, werbefreier, statischer Kalender für Hybrid-Sport-Events im DACH-Raum und darüber hinaus. Kein kommerzielles Produkt, sondern ein Community-Service.

## Mitmachen

Drei Wege, ein Event einzureichen:

1. **Formular** (für die meisten): https://hybridcal.de/de/submit.html
2. **GitHub Issue**: Bei Fehlern in bestehenden Events
3. **Pull Request**: Für Tech-Affine — siehe `data/events/2026/hyrox-munich-2026-11.yml` als Vorlage

## Datenmodell

- `data/config/formats.yml` — definierte Hybrid-Formate (HYROX, ATHX, ...)
- `data/config/categories.yml` — Kategorien pro Format
- `data/events/<jahr>/<slug>.yml` — eine Datei pro Event

Validierung läuft automatisch über `scripts/validate.py` bei jedem PR.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python build.py
python -m http.server -d dist 8000
# → http://localhost:8000/de/
```

### Lokale Vorschau ohne base_path-Mismatch

Produktiv läuft die Seite unter der Custom-Domain `hybridcal.de` (GitHub
Pages, `custom_domain` in `site.yml`), dort ist `base_path: ""`. Nur ohne
Custom-Domain (Fallback `pfaffelh.github.io/hybridcal/`) bräuchte es
`base_path: /hybridcal` — dann lägen alle Links lokal unter `http.server`
falsch. In dem Fall beim Build `BASE_PATH` als leere Umgebungsvariable setzen:

```bash
BASE_PATH= python build.py
python -m http.server -d dist 8000
# → http://localhost:8000/  funktioniert mit allen Links
```

CI bleibt davon unberührt (Env-Var dort nicht gesetzt → `site.yml` greift).

## Build & Deploy

GitHub Actions (`.github/workflows/deploy.yml`) baut bei jedem Push auf `main` und täglich um 03:00 UTC. Deployment auf GitHub Pages.

## Offene Daten

Alle Event-Daten unter [CC0](https://creativecommons.org/publicdomain/zero/1.0/). Maschinenlesbar verfügbar unter:

- `/events.json` — alle Events
- `/feed.ics` — Kalender-Abo
- `/feed.rss` — RSS

## Lizenz

Code: MIT. Daten: CC0.
