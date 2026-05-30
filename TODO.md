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

## Promo — Drafts

Vorlagen für den ersten Promo-Push. Nicht versendet — Tonalität ggf.
anpassen. Strategie-Notiz: Community-Outreach (Reddit r/Hyrox) +
Direkt-Ansprache von 5–10 Veranstaltern/Training-Clubs als Flywheel-
Hebel. Bezahlte Werbung passt nicht zum werbefreien Charakter.

### Reddit r/Hyrox (EN)

**Title**

```
Built a free, ad-free cross-series hybrid race calendar — HYROX, DEKA, ATHX, Deadly Dozen, Turf Games, Wild Hybrid all in one place
```

**Body**

```
I kept juggling six different organiser sites to see what's happening
across the hybrid world, so I built HybridCal — a single calendar
that pulls together every hybrid race series I could find:

- HYROX (Adult + Youngstars), DEKA, ATHX, Deadly Dozen, Turf Games,
  Wild Hybrid, plus smaller series (METRIX, STYREKX, Nuclear Fit, …)
  under "Other".
- Free, ad-free, no account, no tracking. Open source (MIT) and event
  data is CC0.
- Filter by series, country, region. Subscribe via iCal (/feed.ics)
  so events drop into Google/Apple Calendar automatically — or RSS /
  JSON if you'd rather.
- Bilingual (DE/EN).

Link: https://hybridcal.com

Curious what's missing — if your local race isn't listed, drop a
comment or use the submit form on the site. Bug reports and PRs
welcome on GitHub.

Mods: happy to remove if this isn't the right place.
```

**Vor dem Posten**

- r/Hyrox Sub-Regeln zu Self-Promo prüfen (manche Subs verlangen 9:1-
  Verhältnis oder Mod-Flair).
- Account braucht ein bisschen Karma — sonst posten ältere Accounts
  oft besser durch (z.B. von Freunden cross-posten lassen).
- Quer-Posts danach (mit minimal angepasstem Title): r/CrossFit,
  r/AdvancedRunning, r/CompetitiveCrossfit, ggf. r/DeadlyDozen.

### E-Mail an Veranstalter / Training-Clubs (DE)

**Betreff:** `HybridCal — euer Event ist gelistet`

```
Hallo [Vorname / Team],

ich bin der Maintainer von HybridCal (https://hybridcal.com), einem
freien, werbefreien Community-Kalender, der alle Hybrid-Renn-Serien
bündelt (HYROX, DEKA, ATHX, Deadly Dozen, Turf Games u.a.). Euer
Event "[Event-Name, Datum]" ist gelistet:

→ [Link zur Event-Seite]

Wenn ihr mögt, würde ich mich freuen, wenn ihr den Link an eure
Community weitergebt (Insta-Story, Newsletter, Website). Der Kalender
ist kostenlos, ohne Account, ohne Tracking; Daten stehen unter CC0 —
kein kommerzielles Interesse meinerseits.

Falls Details falsch sind oder ihr weitere Termine ankündigen wollt:
einfach per Formular auf der Seite (Button "Neues Event") oder direkt
Antwort auf diese Mail.

Viele Grüße
[Name]
```

### Email to organisers / training clubs (EN)

**Subject:** `HybridCal — your event is listed`

```
Hi [first name / team],

I maintain HybridCal (https://hybridcal.com), a free, ad-free
community calendar that aggregates every hybrid race series (HYROX,
DEKA, ATHX, Deadly Dozen, Turf Games and others). Your event
"[Event name, date]" is already on it:

→ [Link to event page]

If you'd like, I'd be grateful if you could share the link with
your community (Instagram story, newsletter, website). The calendar
is free, no account, no tracking, data is CC0 — no commercial
interest on my side.

If anything is incorrect or you'd like to announce more dates, you
can either use the submit form on the site (button "Submit event")
or just reply to this email.

Best,
[Name]
```

### Empfohlener erster Empfänger-Cluster

Bewährte erste Ansprechpartner (jeweils direkt aus dem Kalender ableitbar):

| Serie / Club | Kontakt | Hook |
|---|---|---|
| **peb2** (Eningen) | info@peb2.de | Event 2026-06-14 gelistet |
| **METRIX** (UK) | über Website | London-Event Sept. 26 |
| **STYREKX** (BE/NL) | über Website | Mechelen + Amsterdam 2026 |
| **Wild Hybrid** (UK) | über `wildhybrid.co.uk` | 9 Events bereits drin |
| **Nuclear Fit** (UK) | über `nuclear-races.co.uk` | Brentwood-Events |
| **Hybrid Games Basel** | über `hybridgames.ch` | Schweiz-Event |
| **hybridfitnessmedia.com** | über Website | Medien-Hebel, sucht Stories |
| **Rox-Coach / Pace Club** | Podcast/Newsletter | Coaching-Reichweite |

## Sonstiges (offen)

- Turf-Games-Namen normalisieren (ALL-CAPS aus der Quelle, z.B.
  "GOLD COAST SUMMER FESTIVAL 2026")
- DSGVO-Check vor öffentlicher Promo
- Format-Detail-Seite für `other` ggf. unterdrücken (zeigt aktuell
  sieben inhomogene Events ohne gemeinsame Stationen-Tabelle)
