# HybridCal — TODO

## Erledigt

- ✅ Top-Nav umstrukturiert: **Events** | **Formate** (Dropdown) | DE/EN-Switch | Hamburger
- ✅ Formate-Dropdown im Top-Nav listet alle Serien direkt
- ✅ Formate-Übersichtsseite (`/formats.html`) mit Karten pro Format
- ✅ Format-Detail-Seiten: ausführliche Beschreibung via Markdown
  (`long_description_de` / `_en` in `formats.yml`) für HYROX, Deadly Dozen,
  ATHX, DEKA, Turf Games
- ✅ HYROX-Detailseite mit Stationen-Tabelle, Gewichten (Open/Pro),
  Kategorien, Geschichte, Youngstars-Sektion (8–15 J. pro Altersgruppe)
- ✅ Deadly Dozen: 12 Labours mit M/W-Gewichten, Race-Varianten
  (Track / Sprint / Ruck / Mile / Youth / Gross / Swim / Strong / ERG /
  Barbell)
- ✅ ATHX: Zonen + 2026-Workouts + Movement-Standards-Link
- ✅ DEKA: 10 Zones + Subformate (FIT / FIT Ultra / MILE / STRONG /
  Affiliate / ATLAS), Scraper für Events
- ✅ Turf Games: Wettkampf-Varianten (Festival 6er / FITC 4er / ENGINE
  Solo+Pairs+Team), categories.yml gefüllt
- ✅ Mobile Bottom-Nav: Kalender-Button durch **Neues Event** ersetzt
  (Link auf Submit-Formular)
- ✅ Format-Detail-Seite zeigt nur zukünftige Events (inkl. TBA)
- ✅ Sprachumschalter kompakt: `DE/EN`, aktiv = fett, ganzes Element klickbar
- ✅ Liste/Karte/Neues-Event-Buttons: blauer Fokus-/Hover-/Group-Rahmen
  entfernt (`role="group"` aus Markup raus)
- ✅ XENOM bewusst rausgenommen — CrossFit-nahes Format mit Muscle-Ups /
  HSPU, nicht das Hybrid-für-jedermann-Profil dieses Kalenders
- ✅ Kleinere Serien als `format: other` integriert (mit beschreibenden
  Notes): STYREKX (NL/BE), METRIX (UK), Nuclear Fit (UK)

## Nächster Schritt: Event-URLs prüfen

**Alle Events durchgehen und sicherstellen, dass `url:` auf die jeweilige
Event-Detail-Seite zeigt — nicht nur auf die generische
Veranstalter-Homepage.**

Status heute:

- **HYROX**-Events haben oft `https://hyrox.com/event/<city>/` — meist die
  richtige Detail-Seite (aus dem Seed-Script), aber stichprobenartig prüfen
  (Tickets-Subdomain wäre noch besser)
- **DEKA**-Events (Scraper): URL zeigt auf
  `https://tickets-*.spartan.com/event/<id>` bzw.
  `https://www.spartan.com/en/race/detail/<id>/overview` — das ist die
  Event-Detailseite, gut
- **Deadly Dozen** / **ATHX** / **Turf Games**: vermutlich gemischt —
  manche zeigen evtl. nur auf die Veranstalter-Hauptseite. Stichprobe nötig
- **`format: other`** (STYREKX / METRIX / Nuclear Fit): URLs zeigen aktuell
  auf die Race-Übersicht (`/races`, `/`), nicht auf die Event-spezifische
  Detail-Seite — diese gibt es teilweise auch nicht separat
- Wenn keine echte Event-Seite existiert, ist der Veranstalter-Link OK,
  sollte aber idealerweise im `notes:`-Feld erwähnt werden

## Mobile-Nav

Das fixierte Bottom-Nav in der mobilen Ansicht ist final:
**Liste | Karte | Neues Event** (Kalender-Button bewusst entfernt zugunsten
des Submit-CTAs).

## Übersetzungs-Lücken (Stand 2026-05-28)

Stand systematischer Scan über alle Config-Dateien:

| Datei | Status |
|-------|--------|
| `data/config/formats.yml` | ✅ vollständig (alle Formate haben `description_de`+`description_en`, alle 5 ausgebauten Formate haben `long_description_de`+`long_description_en`) |
| `data/config/regions.yml` | ✅ vollständig (`name_de`+`name_en` überall) |
| `data/config/i18n/en.yml` | ✅ vollständig (deckt alle DE-Keys ab) |
| `data/config/categories.yml` | ⚠ **14 Einträge ohne `label_en`** (siehe unten) |
| Event-`notes:`-Feld | ⚠ Schema hat nur ein einziges Free-Text-`notes:`-Feld (DE) — kein `notes_en`. Aktuell betroffen: 10 von 188 Events |

### Fehlende `label_en` in `data/config/categories.yml`

ATHX (Paired-Kategorien aus der alten Saison, evtl. überflüssig — siehe
Beschreibungstext: aktuelles ATHX-Format ist LITE/ATHX/PRO × Individual/Teams):

- `athx/paired-rx-men`, `paired-rx-women`, `paired-rx-mixed`
- `athx/paired-scaled-men`, `paired-scaled-women`, `paired-scaled-mixed`

Deadly Dozen (Bestands-IDs vor dem Format-Ausbau):

- `deadly-dozen/deadly-strong-singles`, `deadly-strong-pairs`
- `deadly-dozen/deadly-run-singles`
- `deadly-dozen/deadly-erg-singles`

DEKA (Bestands-IDs):

- `deka/deka-fit-singles`, `deka-fit-pairs`
- `deka/deka-strong-singles`
- `deka/deka-mile`

Diese Namen sind alle bereits englisch lesbar ("Deadly Strong Singles",
"DEKA FIT Pairs" usw.) — `label_en` einfach gleich `label_de` setzen
oder leichte Variation ("Männer" → "Men"). Bei ATHX-Paired-Einträgen
zuerst prüfen, ob die Kategorien noch relevant sind oder beim
nächsten Aufräumen entfernt werden können.

### Event-Notes (DE-only-Schema)

Das Pydantic-Modell hat `notes: str | None` — kein paralleles `notes_en`.
Wenn EN-Notes gewünscht sind, müsste `models.py` erweitert werden
(`notes_de` / `notes_en`) und die Templates müssten den passenden auswählen.
Aktuell betroffen sind 10 Events mit Notes (u. a. die `format: other`-
Events: STYREKX, METRIX, Nuclear Fit, Hybrid Games Basel) sowie ein paar
manuell angelegte HYROX/DEKA-Einträge.

## SEO

Vor öffentlicher Promo durchgehen:

- **Meta-Tags** pro Seite prüfen: Title, Description, Open Graph
  (vorhanden, aber Inhalt vs. Bedarf evaluieren — viele Detail-Seiten
  vererben generische `t.meta.description`)
- **JSON-LD** für Event-Detail-Seiten ist schon drin (`_event_json_ld`
  in renderer.py); für Formate noch ergänzen
- **Sitemap.xml** wird generiert — prüfen ob alle Formate und neuen
  Events korrekt drin sind (auch `format: other`)
- **Canonicals + hreflang**: aktuell richtig gesetzt, aber stichprobenartig
  validieren
- **Page-Titel pro Format** mit echter Keyword-Dichte
  (z. B. "HYROX 2026 Race-Kalender — alle Events weltweit") statt
  nur "HYROX — HybridCal"
- **Strukturierte Daten für Formate** (Event-Series-Schema?)
- **robots.txt + sitemap ping** an Google Search Console
- **Performance**: Lighthouse-Score checken (Pico+Alpine sind klein,
  Leaflet könnte sich noch lohnen lazy-zu-laden)
- **Bild-Assets**: aktuell minimal, OG-Preview-Bild fehlt komplett
  (nur favicon-Suppress) — eigenes 1200×630 OG-Bild ergänzen

## Sonstiges (offen)

- Turf-Games-Namen normalisieren (ALL-CAPS aus der Quelle, z.B.
  "GOLD COAST SUMMER FESTIVAL 2026")
- DSGVO-Check vor öffentlicher Promo
- Format-Detail-Seite für `other` ggf. unterdrücken (zeigt aktuell
  sieben inhomogene Events ohne gemeinsame Stationen-Tabelle)
