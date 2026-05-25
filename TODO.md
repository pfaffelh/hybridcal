# TODO — Tally-Submission-Form anlegen

Was du im Browser machen musst, damit das Submit-Formular auf der Live-Seite funktioniert.

Aktueller Stand: `data/config/site.yml` enthält noch den Platzhalter
`tally_form: https://tally.so/r/PLATZHALTER`. Die Submit-Seite zeigt deshalb
einen toten Button. Die Tally-Form muss noch angelegt werden.

---

## 1. Account + Form anlegen

1. Auf https://tally.so registrieren (Free-Tier reicht: 200 Submissions/Monat, unbegrenzt Felder)
2. „Create new form" → leeres Formular
3. **Sprache:** Deutsch (Zielgruppe DACH-fokussiert)
4. **Form-Titel:** `Hybrid-Sport-Event einreichen`
5. **Form-Beschreibung:**
   > Danke, dass du HybridCal mit Daten versorgst. Wir prüfen Submissions
   > und tragen passende Events innerhalb von 24-48 h ein.

---

## 2. Pflicht-Felder (in dieser Reihenfolge)

| Feld | Tally-Typ | Hinweis / Beispiel |
|---|---|---|
| Event-Name | Short answer | „HYROX Munich" |
| Format | Dropdown | Optionen: HYROX, Hybrid Games ATHX, Deadly Dozen, DEKA, Turf Games, XENOM, Andere |
| Startdatum | Date | |
| Enddatum | Date | Bei Eintages-Event gleich wie Startdatum |
| Stadt | Short answer | „München" |
| Land | Dropdown | DE, AT, CH, GB, IE, FR, IT, ES, NL, BE, PT, DK, … (ISO-Code, 2 Buchstaben) |
| Offizielle URL | URL | Link zur Veranstalter-Seite |
| Quelle der Information | Long answer | Trust-Check, Pflichtfeld: „Newsletter vom 12.08.", „Eigene Teilnahme", „Instagram-Post @hyrox" |

---

## 3. Optional-Felder

| Feld | Tally-Typ | Hinweis |
|---|---|---|
| Venue | Short answer | „Olympiahalle" |
| Kategorien | Long answer | Freitext, „Singles Pro, Doubles Mixed, Relay Mixed" |
| Bist du Veranstalter? | Multiple choice | Ja / Nein — beeinflusst `source: organizer` vs. `community` |
| Deine Email | Email | Für Rückfragen — optional |
| Anmerkungen | Long answer | Freier Kommentar |

---

## 4. DSGVO-Einwilligung (als letztes Feld)

Tally hat ein eingebautes Consent-Field. Inhalt:

> Mit dem Absenden willige ich ein, dass meine Daten zur Bearbeitung der
> Submission verarbeitet werden.
> [Datenschutzerklärung](https://pfaffelh.github.io/hybridcal/de/privacy.html)

Als **required** markieren.

---

## 5. Button-Labels

| Button | Label |
|---|---|
| Submit (Hauptbutton) | **Event einreichen** |
| Next (bei mehrseitigem Form) | **Weiter** |
| Previous / Back | **Zurück** |
| Restart (optional) | **Neu starten** |

---

## 6. Form-Settings

- **Spam-Schutz**: Settings → reCAPTCHA-Alternative ist eingebaut, aktivieren
- **Confirmation message** nach Submit:
  > Danke! Wir melden uns ggf. innerhalb von 48 h.
- **Notifications**: Settings → Notifications → Email an `pfaffelh@gmail.com`
  bei jeder Submission

---

## 7. Share-URL holen

- Oben rechts „Share" → öffentlichen Link kopieren
- Format: `https://tally.so/r/XXXXXX` (sechs Zeichen, alphanumerisch)

---

## 8. URL in `site.yml` eintragen

```yaml
# data/config/site.yml
tally_form: https://tally.so/r/XXXXXX   # ← deine Form-URL
```

Dann:

```bash
python build.py                              # lokal verifizieren
git add data/config/site.yml
git commit -m "Set real Tally form URL"
git push
```

GitHub Actions baut + deployed in ~30 s. Submit-Seite hat dann den richtigen Link.

---

## Optional — später

- **Embed statt Link:** Tally bietet einen iframe-Embed an. Saubereres UX,
  aber zusätzliches Drittanbieter-Embed auf der Seite. Privacy-Policy
  deckt es schon ab (Tally ist gelistet). Würde Tally automatisch
  beim Aufruf von `/submit` laden statt erst beim Klick.
- **Zweites Form für EN-Sprache** wenn englische Submissions >10% werden.
  Aktuell DE-only mit Hinweis in `templates/submit.html` für EN-User
  auf das GitHub-Issue-Template.

---

## Realistischer Zeitaufwand

- Account + Form bauen: 15-25 Min
- URL eintragen + push: 2 Min
