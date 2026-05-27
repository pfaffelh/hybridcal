# HybridCal — TODO

## Erledigt

- ✅ Top-Nav umstrukturiert: **Events** | **Formate** (Dropdown) | DE/EN-Switch | Hamburger
- ✅ Formate-Dropdown im Top-Nav listet alle 7 Serien direkt
- ✅ Formate-Übersichtsseite (`/formats.html`) mit Karten pro Format
- ✅ Format-Detail-Seiten: ausführliche Beschreibung via Markdown
  (`long_description_de` / `_en` in `formats.yml`)
- ✅ HYROX-Detailseite mit Stationen-Tabelle, Gewichten (Open/Pro), Kategorien, Geschichte
- ✅ Format-Detail-Seite zeigt nur zukünftige Events (inkl. TBA)
- ✅ Sprachumschalter kompakt: `DE/EN`, aktiv = fett, ganzes Element klickbar
- ✅ Liste/Karte/Kalender-Buttons: blauer Fokus-/Hover-Rahmen entfernt

## Format-Detail-Seiten ausbauen

Für die restlichen 6 Formate `long_description_de` (und ggf. `_en`) in
`data/config/formats.yml` füllen, analog zum HYROX-Schema:

1. Kurzer Format-Absatz
2. Stationen / Workouts mit Distanzen & Gewichten als Markdown-Tabelle
3. Kategorien
4. Geschichte (1–2 Absätze)
5. Hinweis auf offizielle Quelle

Offen: ATHX, Deadly Dozen, DEKA, Turf Games, XENOM, Other.

## Mobile-Nav

Das fixierte Bottom-Nav (Liste/Karte/Kalender) in der mobilen Ansicht bleibt
unverändert — soll genau so bleiben.

## Sonstiges (offen)

- EN-Übersetzungen: viele Kategorie-Labels und Format-Beschreibungen
  fallen noch auf DE zurück (inkl. der neuen HYROX-`long_description_de` —
  noch keine `_en`-Variante)
- Turf-Games-Namen normalisieren (ALL-CAPS aus der Quelle, z.B.
  "GOLD COAST SUMMER FESTIVAL 2026")
- DSGVO-Check vor öffentlicher Promo
