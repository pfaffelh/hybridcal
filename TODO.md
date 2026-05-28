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
- ✅ Logo (laufende Hantel) als Favicon, Apple-Touch-Icon, OG-Image
  (1200×630) + Top-Nav-Marke (responsive: 2rem mobil / 4rem desktop)
- ✅ **Event-URLs-Audit:** alle zukünftigen Events auf event-spezifische
  Links geprüft (Details unten)

## Event-URLs — Audit erledigt (2026-05-28)

Datenquellen & Vorgehen pro Serie sind jetzt in **`CLAUDE.md`**
dokumentiert (Playbook). Ergebnis des Durchlaufs:

- **HYROX (68):** alte `event/<city>/`-URLs waren **flächendeckend 404** →
  auf echte Slugs gefixt (`event/hyrox-berlin/` etc.)
- **Deadly Dozen (43):** event-spezifische Booking-URLs aus dem Supabase-
  Backend; Liverpool-Datumsfehler korrigiert (06-19 → 06-13)
- **ATHX (32):** 27 auf `events/<ulid>`; Miami + Houston ergänzt
- **Turf Games (7):** je eigene Detailseite
- **DEKA (24):** war schon korrekt (Spartan-Ticket-URLs)
- **STYREKX/METRIX (4):** Detailseiten

Offene Rest-Punkte aus dem Audit:

- **5 ATHX-2027-Events** (Amsterdam/Copenhagen/Glasgow/Liverpool/Marseille)
  sind angekündigt, aber noch nicht ticketed → generische `/events`-URL,
  als `status: tentative` markiert. Sobald Buchung live ist: ULID-URL setzen
  und auf `confirmed` zurück.
- **Nuclear Fit (2):** Veranstalter hat keine date-spezifischen Seiten →
  Hub-Link bleibt.
- **Re-Run-Idee:** Audit periodisch wiederholen (neue Events erscheinen,
  ATHX-2027 wird sukzessive ticketed). Quellen in `CLAUDE.md`.

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

- ✅ **Titles & Descriptions** keyword-/datumsreich: Event-Titel mit Datum,
  Format-Seiten "{Name} — Termine & Kalender {Jahr}" + eigene Description
  (mit Event-Count), Formate-Übersicht und Index mit Brand-Keywords.
  i18n unter `seo:` in beiden Sprachen.
- ✅ **JSON-LD:** Events haben `schema.org/Event` (`_event_json_ld`) inkl.
  `image` (Format-Markenbild) + konsistentem `organizer` + separater
  `BreadcrumbList` (HybridCal › Format › Event). Format-Seiten haben
  `ItemList` der kommenden Events (`_format_item_list`).
- ✅ **Format-Markenbilder** (`static/logo/formats/<id>.png`, in Format-Farbe
  + Name + HybridCal-Läufer) dienen als JSON-LD-`image` und als og:image /
  twitter:image pro Format- und Event-Seite (überschreibbarer `og_image`-Block).
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
- ✅ **OG-Image** (1200×630) + Favicon + Apple-Touch-Icon vorhanden
  (`static/logo/`), in `base.html` verdrahtet

## Sonstiges (offen)

- Turf-Games-Namen normalisieren (ALL-CAPS aus der Quelle, z.B.
  "GOLD COAST SUMMER FESTIVAL 2026")
- DSGVO-Check vor öffentlicher Promo
- Format-Detail-Seite für `other` ggf. unterdrücken (zeigt aktuell
  sieben inhomogene Events ohne gemeinsame Stationen-Tabelle)
