# CLAUDE.md — Arbeitsnotizen für HybridCal

Projekt-Setup, Build und Datenmodell stehen im `README.md`. Diese Datei
sammelt operatives Wissen, das beim Arbeiten am Repo immer wieder gebraucht
wird — vor allem: **wie komme ich pro Renn-Serie an aktuelle Event-Daten?**

## Build & lokale Vorschau

```bash
BASE_PATH= .venv/bin/python build.py        # leeres BASE_PATH -> Links ab /
.venv/bin/python -m http.server -d dist 8000
```

Die Cross-Reference-Validierung im Build fängt kaputte Kategorie-/Format-
Referenzen ab. `.venv` enthält bereits `playwright` (+ chromium headless),
`cairosvg`, `markdown` für Scraping/Asset-Aufgaben.

## Event-Update-Playbook (pro Serie)

Grundprinzip beim "alle zukünftigen Events aktualisieren"-Auftrag:

1. **Datenquelle pro Serie unten nachschlagen.** Die meisten Seiten sind
   JS-gerenderte SPAs → mit Playwright laden und die **XHR/fetch-Calls
   mitsniffen**, um die Backend-API zu finden. API direkt abfragen ist
   schneller und strukturierter als DOM-Scraping.
2. **Matching** unserer YAMLs gegen die Quelle: Stadt normalisieren
   (deaccent, lowercase, nur `[a-z0-9]`) **+ Startdatum**. Fallbacks:
   Stadt-only im selben Jahr, oder Datum+Land für venue-benannte Events.
3. **`url:` muss auf die Einzelveranstaltung zeigen**, nicht auf eine
   Übersichts-/Veranstalter-Startseite.
4. Immer eine **Stichprobe der URLs auf HTTP 200 prüfen** (curl mit
   Browser-User-Agent — manche Seiten blocken sonst).
5. Build laufen lassen, Ergebnis verifizieren.

Heutiges UA-Snippet, das überall durchkommt:
`Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36`

### HYROX
- **Event-Liste:** <https://hyrox.com/find-my-race/> (JS-gerendert, Playwright).
- **Detail-URL-Muster:** `hyrox.com/event/<event-slug>/` — der Slug ist der
  **volle Event-Name**, oft mit Sponsor-Präfix und Saison-Suffix:
  `hyrox-berlin`, `fitness-first-hyrox-frankfurt`,
  `virgin-active-hyrox-johannesburg-25-26`,
  `puma-hyrox-world-championships-stockholm`.
- ⚠ **`hyrox.com/event/<stadt>/` (nur Stadt) ist FALSCH und liefert 404** —
  das alte Seed-Script hatte das fälschlich erzeugt.
- Matching: Stadt als Substring im Card-Text + Startdatum (Format im Text:
  `22. May. 2026 – 31. May. 2026`).
- Gotchas: Ghent → Site nutzt **"Gent"**; Tenerife → `hyrox-tenerife`;
  Youngstars sind **eigene** Events; vergangene Events fallen aus
  find-my-race raus → dann Fallback `hyrox.com/find-my-race/` statt 404.

### Deadly Dozen
- **Backend: Supabase REST.** Die Event-Liste auf
  `deadlydozen.com/ultimate-fitness-race-track-races` lädt einen iframe
  von `events-web-dd.vercel.app/embed/track`, der Supabase abfragt:
  ```
  https://xeltdycwgunxzjrzinxv.supabase.co/rest/v1/events
    ?select=*&is_live=eq.true&is_cancelled=eq.false
    &race_date=gte.<HEUTE>&order=race_date.asc
  ```
  Header `apikey` + `Authorization: Bearer <anon-key>` nötig. Den anon-Key
  aus den XHR-Headers des Embeds sniffen (er rotiert selten; war zuletzt ein
  langes JWT mit `"role":"anon"`).
- Pro Zeile: `ticket_url` (= event-spezifischer Link), `venue_city`,
  `country_code`, `race_date`, `latitude`, `longitude`, `race_type`
  (TRACK / STRONG / ERG / MILE / SPRINT / GROSS / SWIM / BARBELL / DFT / …).
- `ticket_url`-Domains variieren: `in.njuko.com`, `in.deadlydozen.events`,
  `webtickets.co.za`.
- Gotchas: Akzente (Málaga, Nürnberg → "NURNBURG"), Gqeberha-Schreibweise,
  Venue-statt-Stadt ("LEE VALLEY" = unser London) → Datum+Land-Fallback.

### ATHX (Hybrid Games)
- **Event-Liste:** <https://athxgames.com/events> (Laravel/Inertia-SSR).
  **Detail:** `athxgames.com/events/<ULID>`.
- Stadt/Datum stehen nicht in der Card (nur "More Info") → jede
  `/events/<ulid>`-Detailseite besuchen: `<h1>` = "ATHX <STADT> <JAHR>",
  Body enthält "DD Mon YYYY Venue Country Categories …".
- `athxgames.com/api/events/countries` liefert nur Länder, keine Events.
- 2026 UK/EU-Ticketing auch auf FIXR: `fixr.co/organiser/484195045`.
- ⚠ **Nicht alle angekündigten Events sind gelistet/ticketed.** Die
  2027-Saison hat "21+ Städte", aber nur 16 sofort buchbar. Angekündigte,
  aber noch nicht ticketed Events (z.B. mehrere 2027er) haben **noch keine
  Detailseite** → generische `/events`-URL behalten und `status: tentative`
  setzen, bis die Buchung live ist.

### DEKA (Spartan)
- **API** (gefunden via Sniffen von `deka.fit/en/race/find-race`):
  ```
  https://api2.spartan.com/api/races/upcoming_past_planned
    ?new_api=yes&plimit=0&ulimit=500&prlimit=0&units=miles&radius=999999
    &country=&identifiers[]=dekafit&identifiers[]=dekafitultra
    &identifiers[]=dekastrong&identifiers[]=dekamile&identifiers[]=dekaroadshow
  ```
  `country=` leer = weltweit. Antwort: `upcoming[]` mit `venue`
  (city/country/lat/lon), `start_date`/`end_date`, und `events[]`
  (Sub-Events mit `registration_url_1` + `category.category_identifier`).
- **Scraper existiert:** `scripts/add_deka_2026.py` (zweistufig: Stage 1
  schreibt `scripts/_deka_candidates.yml` mit `include:`-Flags zum
  manuellen Review, Stage 2 `--apply` schreibt nur `include: true`).
- Per-Event-URL: `tickets-*.spartan.com/event/<id>` bzw.
  `spartan.com/en/race/detail/<id>/overview`.

### Turf Games
- **Event-Seiten:** <https://turfgames.com/pages/events> (Shopify).
  Detail: `/pages/<city>-2026` (Festival/FITC) oder
  `/blogs/other/<slug>` (Engine-Events, z.B. `engine-london-summer-2026`,
  `gold-coast-engine-2026`).
- Pro Event nach Stadt **und** Format-Variante (Festival/Engine/FITC) matchen.

### STYREKX (Benelux, `format: other`)
- <https://styrekx.com/races> — Detail `/races/styrekx-<venue>`
  (`styrekx-nekkerhal-mechelen`, `styrekx-expo-greater-amsterdam-2026`).
  Booking via Strong Viking / Atleta.cc.

### METRIX (UK, `format: other`)
- <https://metrix.fitness/> — Detail `/events/<city>/<venue-slug>`
  (`events/cardiff/depot-jun-2026`, `events/london/london-5th-september`).

### Nuclear Fit (UK, `format: other`)
- <https://nuclear-races.co.uk/nuclear-fit/> — nur Format-/Hub-Seiten,
  **keine** date-spezifischen Event-Seiten. Hub-Link behalten.

### Hybrid Games Basel (`format: other`)
- `hybridgames.ch` ist eine Single-Event-Site → die Startseite **ist** die
  Event-Seite. Nicht mit ATHX (früher "Hybrid Games ATHX") verwechseln.

## Scraping-Erfahrungen (allgemein)

Gesammelte Lektionen aus den bisherigen Durchläufen — spart beim nächsten Mal
viel Zeit:

- **Erst die API finden, dann erst DOM-Scraping.** Fast alle diese Seiten
  sind SPAs (Vue/Nuxt, Laravel/Inertia, Shopify, Squarespace). Mit Playwright
  laden und im `response`-Handler nach Calls filtern, die `api`, `event`,
  `race`, `supabase`, `.json` enthalten (Tracking-/Asset-URLs wie
  `gtag`, `.js/.css/.png/.woff` rausfiltern). Die Backend-API liefert
  strukturierte Daten mit Datum/Stadt/Koordinaten/Ticket-URL — viel
  zuverlässiger als Text aus Cards zu parsen.
- **Beispiele gefundener Backends:** Deadly Dozen → Supabase REST
  (anon-JWT-Key aus den XHR-Headers); DEKA → `api2.spartan.com`; ATHX →
  Laravel-SSR (Detailseiten statt API). Wenn ein iframe-Embed auftaucht
  (`events-web-dd.vercel.app`), dort die XHRs sniffen.
- **Card-Text reicht oft nicht.** Viele Event-Cards zeigen nur einen Button
  ("More Info" / "Enter now"). Stadt/Datum stehen in Geschwister- oder
  Eltern-Elementen, nicht im Link. Dann lieber die **Detailseite** je Event
  besuchen (H1 + erster Body-Textblock) als im Karten-DOM hochzuklettern.
- **Bot-Schutz:** `curl` ohne Browser-UA bekommt oft 403 (z.B. hyrox.com,
  athxgames.com) oder eine Vercel-Security-Checkpoint-Seite. Lösung: echter
  Browser-UA (Snippet oben) bzw. Playwright. Manche Endpoints (Supabase,
  Spartan-API) gehen auch per `curl` mit UA + Keys.
- **Matching robust machen:** Stadt **deaccenten** (`á→a`, `ü→u`,
  `ß→ss`) und auf `[a-z0-9]` reduzieren, dann gegen Start-Datum matchen.
  Fallback-Kaskade: exaktes Datum → selbes Jahr+Monat → selbes Jahr →
  Datum+Land (für venue-benannte Events wie "Lee Valley" = London).
  Nie blind auf Stadt-Namen verlassen (Ghent/Gent, Nürnberg/Nurnburg,
  Gqeberha/Gqerberha, "Santa Cruz de Tenerife" vs nur "Tenerife").
- **Immer Stichprobe auf HTTP 200 prüfen** nach dem URL-Setzen. Genau so
  ist aufgeflogen, dass die alten HYROX-`event/<city>/`-Links allesamt 404
  waren — sah im Datenmodell plausibel aus, war aber komplett kaputt.
- **Daten-Diskrepanzen ernst nehmen, nicht wegmatchen.** Wenn ein Event
  nicht matcht, ist das ein Signal: falsches Datum in unseren Daten
  (Deadly Dozen Liverpool: 06-19 vs echtes 06-13), fehlendes Event
  (ATHX Miami/Houston), oder angekündigt-aber-noch-nicht-ticketed
  (ATHX-2027). Erst recherchieren/dem User melden, nicht raten.
- **Past Events** fallen aus den meisten "find your race"-Listen raus →
  für die gibt es keine Detailseite mehr; sinnvoller Fallback ist die
  Race-Finder-Übersicht statt einer geratenen 404-URL.
- **Tooling im `.venv`:** Playwright (chromium headless), `cairosvg`,
  `markdown`. Throwaway-Scrape-Skripte nach `/tmp/` schreiben, nicht ins
  Repo. Daten als JSON nach `/tmp/` cachen, damit Matching-Iterationen
  nicht jedes Mal neu fetchen müssen.
- **Massen-Updates an YAMLs:** per Python-Skript die `url:`-Zeile gezielt
  ersetzen (`re.sub(r'^url:.*$', ..., flags=re.M, count=1)`), danach
  `build.py` als Validierung laufen lassen (Cross-Reference-Check).

## Format-Abgrenzung (was gehört in den Kalender?)

Profil: **Ausdauer + Kraft, niedrige Skill-Hürde, für jedermann.**
Ausdauer ≠ nur Laufen — auch Row/Ski/Bike-Erg und Carries unter Last zählen.

- Aufgenommen: HYROX, Deadly Dozen, ATHX, DEKA, Turf Games; kleinere als
  `format: other` (STYREKX, METRIX, Nuclear Fit, Hybrid Games Basel).
- **XENOM bewusst NICHT** aufgenommen: CrossFit-naher "Decathlon of Fitness"
  mit Muscle-Ups / HSPU / schweren Olympic-Lifts → andere Community, hohe
  Skill-Hürde, niedriger Ausdaueranteil.

## Format-Bilder = bewusst Farbkarten, keine offiziellen Logos

`static/logo/formats/<id>.png` sind **selbst generierte Farbkarten**
(Format-Farbe + Name + HybridCal-Läufer), genutzt als JSON-LD-`image` und
og:image. **Bewusste Entscheidung — nicht erneut aufrollen:** keine
offiziellen Veranstalter-Logos verwenden. Gründe: kein Veranstalter bietet
ein freies Press-Kit (HYROX beschränkt Logo-Nutzung ausdrücklich auf
lizenzierte Clubs/Coaches und warnt vor Markenverwirrung; DEKA nur
Affiliate-Toolkit; ATHX/Deadly Dozen/Turf Games haben nur Sponsoring-
Kontakte). Haltung des Eigentümers: "alle Logos oder keine" → also **keine**.
Echte Logos nur, falls je ein Veranstalter explizit schriftlich zustimmt;
dann aber konsequent für alle, sonst weiter Farbkarten.

## Mehrsprachige Inhalte (i18n-Konventionen)

Default-Sprache ist DE, EN ist die Übersetzung. Muster im Datenmodell:
**Basis-/DE-Feld + `_en`-Override**, EN fällt bei fehlendem Override auf DE
zurück. Wo überall Übersetzungen hingehören:

| Datei / Modell | Felder |
|----------------|--------|
| `formats.yml` (Format) | `description_de`/`_en`, `long_description_de`/`_en`, optional `name_de`/`_en` (sonst `name`) |
| `categories.yml` (Category) | `label_de` + `label_en` pro Eintrag |
| `regions.yml` (Region) | `name_de` + `name_en` (beide Pflicht) |
| Event-YAMLs (Event) | `notes` (= DE-Basis) + optional `notes_en` |
| UI-Strings | `data/config/i18n/{de,en}.yml` — jeder DE-Key muss in `en.yml` existieren |

- **Template-Auswahl-Pattern:** `format['description_' + lang] or format.description_de`
  bzw. für Events `event.notes_en if lang == 'en' and event.notes_en else event.notes`.
- **Neues Event mit Notes:** `notes:` immer (DE); `notes_en:` ergänzen, wenn
  Übersetzung vorliegt. `notes` wird auf der Event-Seite als Markdown gerendert.
- **Konsistenz-Check vor Commit:** kurzer Scan, ob ein `_en`-Gegenstück fehlt
  (formats/regions/i18n waren zuletzt vollständig; categories + notes wurden
  am 2026-05-28 nachgezogen).
- **`other`-Format-Detailseite** zeigt bewusst **keine** Beschreibung oben
  (grab-bag ohne gemeinsames Format) — nur die Event-Liste. Logik in
  `format.html` via `{% if format_id != 'other' %}`.
