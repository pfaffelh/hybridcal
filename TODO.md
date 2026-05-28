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

## Übersetzungen — vollständig (Stand 2026-05-28)

Systematischer Scan über alle Config-Dateien, alle Lücken geschlossen:

| Datei | Status |
|-------|--------|
| `data/config/formats.yml` | ✅ `description_de`/`_en` + `long_description_de`/`_en` |
| `data/config/regions.yml` | ✅ `name_de`/`_en` überall |
| `data/config/i18n/en.yml` | ✅ deckt alle DE-Keys ab (inkl. `seo:`) |
| `data/config/categories.yml` | ✅ alle Einträge haben jetzt `label_en` (14 ergänzt) |
| Event-`notes` | ✅ Modell hat `notes` (DE) + `notes_en`; bilingual gerendert in `event.html`. 10 Events übersetzt |

i18n-Konventionen sind in `CLAUDE.md` dokumentiert (Abschnitt
"Mehrsprachige Inhalte"). Beim Anlegen neuer Inhalte daran halten.

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
- ✅ **OG-Image** (1200×630) + Favicon + Apple-Touch-Icon vorhanden
  (`static/logo/`), in `base.html` verdrahtet
- ✅ **Sitemap.xml** geprüft (404 URLs): alle Format-Seiten inkl.
  `format: other`-Events, `/formats.html` DE+EN, mit hreflang-Alternates

Noch offen:

- **robots.txt + Sitemap an Google Search Console** anmelden (braucht
  GSC-Zugang → Owner-Task, kein Code)
- **Performance / Lighthouse**: Score in Chrome DevTools messen; größter
  Hebel wäre **Leaflet lazy-load** (Karten-Lib erst beim Öffnen der Karte
  laden statt auf jeder Seite). Code-seitig machbar, sobald gewünscht.
- **Canonicals + hreflang** sind gesetzt — nur noch stichprobenartig im
  Live-Deploy validieren (Owner-Check).

## Sonstiges (offen)

- Turf-Games-Namen normalisieren (ALL-CAPS aus der Quelle, z.B.
  "GOLD COAST SUMMER FESTIVAL 2026")
- DSGVO-Check vor öffentlicher Promo
- Format-Detail-Seite für `other` ggf. unterdrücken (zeigt aktuell
  sieben inhomogene Events ohne gemeinsame Stationen-Tabelle)
