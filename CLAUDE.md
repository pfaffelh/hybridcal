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

### Conquer Fitness / "Level 7" (UK, `format: other`)
- **Event-Seite:** <https://www.conquerfitness.org.uk/events/level-7>
  (Framer-SPA; Übersicht <https://www.conquerfitness.org.uk/events/>).
  Format "Leven Seven": 7 funktionelle Stationen + je 450 m Lauf,
  ausgetragen über die Ebenen eines Parkhauses (Glasshouse Car Park,
  Alderley Park, Macclesfield SK10 4TG).
- **Saison:** Spring + Autumn (gleiche Kern-Struktur, neue Station pro Jahr).
- **Buchung über Eventrac**, Detail-URLs `conquerfitness.eventrac.co.uk/e/
  <spring|autumn>-<jahr>-level-seven-fitness-race-alderley-park-<id>`
  (Spring 2026 = …-13586, Autumn 2026 = …-13680). Daten stehen nicht im
  statischen HTML der Eventrac-Seite → aus Event-Seite/FB/Web ableiten.

### The Hybrid Games (UK, `format: other`)
- **Offizielle Site:** <https://thehybridgames.com/> — Events unter
  `/events/<city>/` bzw. `/events/<city>-2026/` (Datum + Venue im HTML).
  ⚠ Nicht verwandt mit **Hybrid Games Basel**.
- Format: 10 Läufe + 10 Stationen + 200-m-Sprint-Finish (Newcastle nur 9+9
  wegen Halle). Singles/Doubles/Mixed Doubles.
- **Tickets über FIXR** (`fixr.co/organiser/thehybridgames`): das eingebettete
  JSON enthält pro Stadt die Venue-Objekte mit `latitude`/`longitude`/
  `postcode` (NEC Birmingham, SEC Arena Glasgow, Utilita Arena Newcastle).
  Pro Stadt gibt es Einzel-Ticket-Events je Kategorie.

### Fura World (ES, `format: other`)
- **Veranstalter:** <https://furaworld.com/> (JS-SPA; statisches HTML zeigt
  nur teilweise Events). Hybrid-Race: Lauf + 10 Stationen; Open 500-m-Läufe,
  Elite 750-m-Läufe. Einzel + Paare (Open/Elite, M/W/Mixed).
- **Offizielle Anmeldung & verlässliche Event-Daten über Sportmaniacs:**
  `sportmaniacs.com/c/fura-<event>-<jahr>` (z.B. `fura-la-palma-2026` =
  25.07.2026, Los Llanos de Aridane, La Palma). ⚠ OCR-Aggregatoren wie
  `carrerasocr.com` listen Fura mit **falscher Insel** (Tenerife statt
  La Palma) und teils unbestätigten Zusatz-Events → immer gegen Sportmaniacs
  gegenchecken, nicht blind übernehmen.

### Wild Hybrid (UK, `format: wild-hybrid`)
- **Event-Liste:** <https://www.wildhybrid.co.uk/calendars/sport-events/>
  (Next.js-SSR, Events stehen im HTML). Veranstalter: Wild Deer Events,
  Buchung über eventrac.
- **Detail-URL-Muster:** `wildhybrid.co.uk/e/<slug>-<id>`. Jedes Rennen ist
  je als `-pairs-<id>` **und** `-solos-<id>` gelistet (gleiche Venue/Datum)
  → als **ein** Event zusammenfassen, `url:` auf die Solos-Seite bzw. die
  kombinierte `-pairs-and-solos-`-Seite, wo vorhanden.
- Datum + Venue-Adresse stehen auf der Detailseite ("Next Race: dd/mm/yyyy
  <Adresse mit Postcode>"). Jahr ableiten (Mai–Dez → 2026, Jan–Apr → 2027).
- **Koordinaten:** nur die kombinierte Seite hat sie inline; sonst Postcode
  per <https://api.postcodes.io/postcodes/{PLZ}> geocoden (frei, kein Key).
- Format (Season 2): Trail-Lauf-Runden + 5 Stationen (Sandbag Lunges, D-Ball
  Cleans, Sled Push & Pull, Devil's Press, Wall Balls); Solo/Pairs, RX/Scaled;
  optionale Wild Ruck Runs (5/10 km, Pack M 10 kg / W 7 kg). Die Cheshire-
  Delamere-Veranstaltung ist das Invitational-Saisonfinale. Workout-Details
  liegen als PNG-Grafiken auf den "Season 2 - Solo/Pairs"-Seiten
  (`/contents/<id>-...`).

## Einzelnes neues Event hinzufügen ("ergänze Event X")

Ablauf, wenn der User auf eine einzelne Event-Seite verweist (kein
Serien-Massen-Update). Beispiel-Durchlauf: Black Forest Major Games
(`bfm-games-loerrach-2026-09.yml`, 2026-06-01).

1. **Quelle laden** (WebFetch reicht meist; bei JS-SPA Playbook oben). Name,
   Datum, Stadt, Venue, Land, Ticket-/Anmelde-URL, Format-Beschreibung ziehen.
2. **Anmelde-/Ticket-Seite schlägt Startseite.** Die Veranstalter-Homepage
   ist oft ungenau (Marketing-Zeitraum statt Renntag, Gym-Adresse statt
   Wettkampfort). Die **Registrierungsseite** (Eventfrog, njuko, Atleta.cc …)
   hat die echten Wettkampfdaten. Bei Widerspruch: Anmelde-Seite gewinnt,
   Diskrepanz dem User melden (nicht stillschweigend wegmatchen).
   *Bsp.:* Homepage sagte "5.–9. Sep, GymAzo Steinen"; Eventfrog sagte
   "5. Sep, Stadion Grütt Lörrach" (400-m-Bahn passt zum Format) → Lörrach
   genommen, GymAzo als Veranstalter in die Notes.
3. **Format wählen.** Etabliertes Format nur bei echter Serien-Zugehörigkeit;
   sonst `format: other`. Vorher an der "Format-Abgrenzung"-Sektion prüfen,
   ob das Event überhaupt reingehört (Ausdauer+Kraft, niedrige Skill-Hürde).
4. **Koordinaten** per Nominatim geocoden (frei, kein Key), mit Browser-UA:
   `https://nominatim.openstreetmap.org/search?street=<Str+Nr>&city=<Stadt>&country=Germany&format=json&limit=1`.
   UK: Postcode über `api.postcodes.io/postcodes/{PLZ}`. Auf 4 Nachkommastellen
   runden (wie Bestand).
5. **Slug:** Serien-/Veranstalter-Präfix + Stadt + Jahr + Monat (nicht
   literal `other`!), deaccent. Z.B. `bfm-games-loerrach-2026-09`. Datei
   `data/events/<jahr>/<slug>.yml`. Schema-Details in der Slug-Sektion unten.
6. **YAML schreiben** nach dem `other`-Muster (s. STYREKX-Beispiel):
   `slug, name, format, date_start, date_end, location{city,country,venue,
   timezone,lat,lon}, url, status, source: scraped, categories: [], notes,
   notes_en`. `url:` auf die Einzelveranstaltung. `notes` = DE-Basis,
   `notes_en` = Übersetzung (beide, i18n-Konvention).
7. **Validieren:** `BASE_PATH= .venv/bin/python build.py` (Cross-Reference-
   Check muss `ok` sagen, Event-Count steigt um 1).
8. **URL-Stichprobe** auf HTTP 200 mit Browser-UA (`curl -o /dev/null -w
   "%{http_code}"`). Generierte Seiten liegen unter
   `dist/{de,en}/events/<slug>.html`.
9. **Erst committen/pushen, wenn der User es sagt.** Commit-Message-Stil:
   `data: add <Name> <Jahr> (<Stadt>, <TT.MM.>, format: <fmt>)`.

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

## Wöchentlicher Reconciler

Automatische Pipeline, die jeden **Samstag 03:00 UTC** über GitHub Actions
läuft (`.github/workflows/reconcile.yml`) und einen einzelnen PR
`reconcile/weekly` öffnet bzw. updated. Auto-Merge ist **aus**; jeder Lauf
geht durch menschliches Review.

**Was der Reconciler tut:**

1. Pro Format mit Quell-Plugin (`deadly-dozen`, `deka`, `hyrox`,
   `hyrox-youngstars`, `athx`, `wild-hybrid`) holt er die aktuelle
   Event-Liste der Quelle und normalisiert sie in `SourceRecord`-Einträge
   mit stabiler `source_id`.
2. Matching mit bestehenden YAMLs **ausschließlich über `source_id`**.
3. Für gematchte Events vergleicht er die Felder
   `date_start`, `date_end`, `url`, `location.{city,country,venue,timezone,lat,lon}`
   und schreibt Änderungen direkt ins YAML.
   `categories` und `name` werden **nie** automatisch geändert
   (kuratiert; manuelle Pflege).
4. Für Quell-IDs ohne lokale Entsprechung wird **direkt eine neue
   Event-YAML** im PR-Diff angelegt (kein zweistufiges `include: false`).
5. Für lokale Future-Events, deren `source_id` nicht mehr in der Quelle
   auftaucht, gibt es **nur einen Eintrag im PR-Body** ("verschwunden") —
   kein Auto-Delete.
6. **Vergangene Events** (`date_end < heute`) werden komplett ignoriert.
7. Danach läuft `url_check.py` über die `url:`-Felder **aller**
   Future-Events (alle Formate, inkl. `other`) per HEAD/GET. Defekte URLs
   landen als Block im PR-Body, ohne Auto-Fix.

**Bootstrap (einmalig pro Format):**

Bevor der Reconciler im Steady-State läuft, muss jede bestehende
Future-YAML eine `source_id` bekommen. Dafür existiert
`scripts/reconcile/bootstrap.py`:

```bash
.venv/bin/python -m scripts.reconcile.bootstrap deka --dry-run
.venv/bin/python -m scripts.reconcile.bootstrap deka
HYBRIDCAL_DD_SUPABASE_ANON_KEY="<jwt>" \
  .venv/bin/python -m scripts.reconcile.bootstrap deadly-dozen --dry-run
HYBRIDCAL_DD_SUPABASE_ANON_KEY="<jwt>" \
  .venv/bin/python -m scripts.reconcile.bootstrap deadly-dozen
```

Matching im Bootstrap: deaccent(city) + date_start ±2 Tage (engste
Datumsdistanz gewinnt). Fallback: Land + (Jahr, Monat) für venue-only
Events ohne city-Feld (Manchester Convention Centre Complex etc.).

**Geheimnis:** Der DD-Anon-Key liegt als GitHub-Actions-Secret
`HYBRIDCAL_DD_SUPABASE_ANON_KEY` im Repo. Lokal als Env-Var setzen.
Wie man ihn auffrischt, falls er rotiert, steht oben im Deadly-Dozen-
Abschnitt (XHR-Header des `events-web-dd.vercel.app`-Embeds sniffen).

**HYROX** wird voll reconciled, obwohl es keine JSON-API gibt: das Plugin
parst die server-gerenderten Cards von `find-my-race` (post-ID = stabile
`source_id`). Land/Koordinaten fehlen dort → für **unbekannte** Events
öffnet es die Event-Seite, liest das Custom-Field `en_event_address` und
geocodet die per Nominatim. Details:

- **Detailseiten nur für neue `source_id`s.** Bestehende Events werden
  aus der Card allein synchronisiert (nur `date_start`/`date_end`/`url`
  ändert der Reconciler an ihnen) — das spart ~70 Fetches + Geocodes pro
  Lauf und schützt die kuratierten Location-Felder.
- **Die `continent-*`-Klasse der Card ist der Geocode-Wächter.** Viele
  Adressen nennen kein Land ("Metropolitan Expo, Athens International
  Airport") und lösen sonst nach Athens, *Georgia* auf. Die Kontinent-
  Bbox geht als `viewbox`+`bounded=1` in die Nominatim-Query — reines
  Nachfiltern reicht nicht: "Athens" hat in den Top-5 **keinen**
  griechischen Treffer.
- **`timezone` ist Pflichtfeld** (`hybridcal/models.py`, IANA-validiert).
  Ohne Land *und* Zeitzone wird nichts angelegt (`is_main_brand=False`),
  sondern mit Begründung im PR-Body gemeldet (`skip_note`). Neue Länder
  → `_COUNTRY_TZ` ergänzen; Mehrzonen-Länder (US/CA/MX/BR/AU, Kanaren)
  → `_CITY_TZ`.
- `venue` setzt das Plugin bewusst **nicht**: die Adressen sind zu
  uneinheitlich (mal "Messe Basel", mal "600 E Grand Ave"), und nur
  2/68 Bestands-YAMLs pflegen das Feld überhaupt.
- Nominatim: max 1 req/s, eigener UA, Retry mit Backoff — ein transienter
  Fehler darf **nicht** als "Ort existiert nicht" gecacht werden, sonst
  fällt ein echtes Event still unter den Tisch.

**Phase 2 (offen):** ATHX / Turf Games / `other`-Formate haben keine
vertrauenswürdige öffentliche Quelle → die laufen weiterhin nur durch
den URL-Health-Check, nicht durch den Daten-Reconciler.

**Manueller Trigger / Einzel-Format:**

```bash
# Lokal trockenlauf, ohne YAMLs zu ändern:
RECONCILE_ONLY=deka .venv/bin/python -m scripts.reconcile.run --dry-run

# In GitHub: Actions → "Weekly Reconciler" → Run workflow, optional
# Eingabe `only: deka` setzen.
```

## Slug- und Datei-Konventionen für Events

Slug-Schema: `<format>-<city>-<jahr>-<monat>` (deaccent, lowercase).
Beispiel: `deadly-dozen-strasbourg-2026-07`. Datei: `data/events/<jahr>/<slug>.yml`.
URL: `/events/<slug>/`.

**Eindeutigkeit bei mehreren Future-Events derselben Stadt und desselben
Monats** (etwa vier Macclesfield-DD-Events im selben Monat): an den Slug den
Tag anhängen, also `<format>-<city>-<jahr>-<monat>-<tag>` für den zweiten
und folgende. Beispiele:
- `deadly-dozen-macclesfield-2026-09.yml` (erstes Event im Monat)
- `deadly-dozen-macclesfield-2026-09-19.yml` (zweites Event)
- `deadly-dozen-macclesfield-2026-09-26.yml` (drittes Event)

Wenn auch der Tag schon belegt ist (extrem selten — zwei Events an exakt
demselben Datum), wird ein `-2`, `-3` hinten angehängt. Das ist die
Fallback-Regel des Reconciler-Slug-Generators und sollte nie greifen.

`source_id` (Supabase-UUID, Spartan-ID …) gehört **nicht in URL/Slug** —
URLs bleiben menschenlesbar. Die ID lebt ausschließlich im YAML als Feld
`source_id:` und ist der Schlüssel, mit dem der Reconciler identische
Events über Läufe hinweg wiedererkennt (auch wenn Stadt/Datum driften).

## Format-Abgrenzung (was gehört in den Kalender?)

Profil: **Ausdauer + Kraft, niedrige Skill-Hürde, für jedermann.**
Ausdauer ≠ nur Laufen — auch Row/Ski/Bike-Erg und Carries unter Last zählen.

- Aufgenommen: HYROX, Deadly Dozen, ATHX, DEKA, Turf Games, Wild Hybrid;
  kleinere als `format: other` (STYREKX, METRIX, Nuclear Fit, Hybrid Games
  Basel).
- **XENOM bewusst NICHT** aufgenommen: CrossFit-naher "Decathlon of Fitness"
  mit Muscle-Ups / HSPU / schweren Olympic-Lifts → andere Community, hohe
  Skill-Hürde, niedriger Ausdaueranteil.
- **HalfRox / "Half HYROX" bewusst NICHT** aufgenommen: kein eigener
  Veranstalter, sondern ein Sammelbegriff für Half-Distance-HYROX-
  Simulationen, die einzelne Gyms/Clubs lokal fahren (z.B. TRYROX / C26 Hub
  Kansas, TeamLDN Kanada, Greater Cincinnati). Hyperlokale HYROX-Sims ohne
  gemeinsamen Kalender → würde die Tür für beliebig viele Gym-Sims öffnen.
  (Recherche 2026-05-29.)

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
