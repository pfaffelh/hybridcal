# HybridCal — TODO

## Navigation umstrukturieren

Aktuelles Top-Menü ersetzen durch:

- **Events** — Hauptseite (Liste/Karte/Kalender wie bisher)
- **Formate** — neue Übersichtsseite, listet alle Rennformate mit kurzer Erklärung
- **Sprach-Umschalter** — wie bisher (DE / EN)
- **Hamburger-Menü** — enthält:
  - Neues Event einreichen (`/submit`)
  - Korrektur melden (Anker auf `/submit`)
  - Über (`/about`)
  - Impressum / Datenschutz (unten)

### Formate-Seite

Pro Format eine kurze Erklärung (1–2 Absätze):
- HYROX — Stationen-basiertes Hybrid-Race, weltweites Rennformat
- ATHX (Hybrid Games) — Multi-Disziplin-Wettkampf, längere Events
- Deadly Dozen — 12-Stationen-Format, UK-Ursprung
- DEKA — Decathlon-artiges Funktional-Fitness-Format
- Turf Games — Festival-Format mit mehreren Disziplinen
- XENOM — neueres Format, weniger verbreitet
- Other — sonstige Hybrid-Events

Beschreibungen liegen schon (teilweise) in `data/config/formats.yml` unter
`description_de` / `description_en` — von dort generieren.

## Mobile-Nav

Beim Restrukturieren prüfen, ob das fixierte Bottom-Nav (Liste/Karte/Kalender)
zum neuen Top-Menü passt oder ob es konsolidiert werden kann.

## Sonstiges (offen)

- EN-Übersetzungen: viele Kategorie-Labels und Format-Beschreibungen
  fallen noch auf DE zurück
- Turf-Games-Namen normalisieren (ALL-CAPS aus der Quelle, z.B.
  "GOLD COAST SUMMER FESTIVAL 2026")
- DSGVO-Check vor öffentlicher Promo
