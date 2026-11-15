# TODO

## Nächster Bulk-Commit (Kleinkram)

- **Klassen verwalten – Feld „Zuständige Lehrkraft"**: Label-Zusatz
  „(optional, nur zur Anzeige)" raus, stattdessen „(= Klassenlehrer/in im
  Stammdatenblatt)". (`app/forms.py`, `KlasseForm.zustaendige_lehrkraft`)
- **Klassen verwalten – Spalte „Bildungsgänge"** bei den bestehenden
  Klassen zeigt die Codes/Keywords statt der Klarnamen. Codes →
  `Bildungsgang.name` mappen. (`teacher_klassen.html` bzw. im View eine
  `code→name`-Map mitgeben, wie in anderen Templates.)
- **Klassen verwalten – „Bearbeiten"-Button je bestehende Klasse**: Name +
  zugeordnete Bildungsgänge nachträglich ändern (bisher nur Anlegen +
  Löschen). Route `POST /teacher/klassen/<id>/bearbeiten` + Formular
  (Checkbox-Liste der Bildungsgänge, vorbelegt), `KlasseBildungsgang`-
  Zeilen entsprechend anlegen/löschen.
- **Kopfzeile der Anmeldungsübersicht**: „Klasse: … / Klasse wechseln" ist
  zu unauffällig (grauer Fließtext + Link). Als Button gestalten, im
  gleichen Layout wie rechts („Jetzt synchronisieren" / „Klassen
  verwalten") – z.B. ein `btn-outline-secondary btn-sm` „Bereich: ELI026 ▾"
  links neben den beiden anderen Buttons.
- **Automatischer Sync per Host-Cron** (einmal täglich reicht fürs Erste,
  deutlich innerhalb der 31-Tage-WP-Löschfrist). Host-Cron statt Cron im
  Container (siehe Chat-Begründung: kein Image-Umbau nötig, Single-Host-
  Setup). Umsetzung:
  - Crontab-Zeile auf dem Prod-Server (Nutzer trägt sie ein, ich kann sie
    nicht selbst einrichten — kein Zugriff auf den Server):
    ```
    0 4 * * * cd /pfad/zum/repo && docker compose exec -T app flask --app run.py sync-fluentform >> /var/log/nobo-sync.log 2>&1
    ```
    (`-T` = kein TTY, nötig für Cron; Uhrzeit/Pfad an die echte Installation
    anpassen.)
  - README-Abschnitt „Automatischer Sync" ergänzen: obiger Crontab-Eintrag
    + Hinweis, dass der Sync alle WP-Submissions neu abruft (kein
    inkrementeller Abruf) und external_id-Dedup greift, + Warnung, dass
    ohne Sync innerhalb der WP-Löschfrist Anmeldungen unwiderruflich
    verloren gehen können.
  - Gleichzeitig dran denken: `.env` auf Prod um
    `FLUENTFORM_RETENTION_DAYS=31` ergänzen (aktuell nicht gesetzt),
    damit die „WP: noch X Tage"-Anzeige in der Übersicht stimmt.
- **Neuer Export „Office 365-Anmeldung" (xlsx)**: Nutzer hat eine Vorlage
  hochgeladen (`EDV-Abteilung mit Benutzernamengenerierung.xlsx`, Sheet
  „TEST Import-CSV für Office 365-", Header in Zeile 1, Daten ab Zeile 2).
  Spalte A (Benutzername) und D (Anzeigename) sind in der Vorlage bereits
  Formeln auf Basis von B/C (`Vorname.Nachname@bbzamnok.onmicrosoft.com`
  mit Umlaut-Ersetzung bzw. `Vorname Nachname`) – die bleiben unangetastet,
  nur Werte eintragen, keine Formeln überschreiben. Zu befüllende
  („grüne") Spalten, analog zu `build_klassenbuch_excel`/`build_daz_excel`
  als neue Funktion in `app/exports.py` + neuer Vorlagen-Key in
  `app/vorlagen.py` (`VORLAGEN["office365"]`) + Export-Button in
  `teacher_registrations.html`:
  - B Vorname ← `r.vorname`
  - C Nachname ← `r.nachname`
  - E Position ← fest `"Schüler"`
  - F Abteilung ← wie im DaZ-Export über `Bildungsgang.query.filter_by(
    code=r.beruf).first().abteilung.name` ermitteln
  - L Adresse ← `r.strasse`
  - M Ort ← `r.ort`
  - N Bundesland/Kanton ← `r.bundesland_kuerzel` (Achtung: das ist das
    Bundesland aus Sektion 4 „Eltern/Hauptwohnsitz", während
    Straße/Ort/PLZ aus Sektion 3 kommen – beim Nutzer gegenprüfen, ob das
    für alle SuS dieselbe Adresse meint oder ob hier eine Inkonsistenz
    entstehen kann. Evtl. auch Kürzel → Klarname mappen, falls Office 365
    den vollen Bundesland-Namen statt „SH"/„HH" erwartet.)
  - O Postleitzahl ← `r.plz`
  - P Land oder Region ← vermutlich fest `"Deutschland"` (kein eigenes
    Länder-Feld im Datenmodell) – mit Nutzer abklären.

## Offen / vom Nutzer gegenzuprüfen

- **WebUntis-Export**: echten Export einmal in Excel öffnen und Farben/
  Streifen/Datumsformat gegenprüfen (Fix: Tabellen-Range auf alle Zeilen +
  Schrift-Reset + `DD.MM.YYYY` erzwungen).
- **Namensschild**: jetzt 1 Spalte/4 Zeilen (3 Faltmarken, auf der langen
  Seite gefaltet). Zeile 1+4 bleiben leer (Standfüße, liegen gefaltet flach
  auf dem Tisch), Zeile 2 = Vorname+Logo (180° gedreht gedruckt), Zeile 3 =
  Nachname+Logo (normal) – das sind die beiden schrägen Flächen des
  Aufstellers. Je nach Lehrkraft (du/sie) wird das fertig gefaltete Schild
  einfach um 180° (Hochachse) gedreht, dann zeigt wahlweise Vor- oder
  Nachname nach vorn. Visuell per pymupdf-Simulation geprüft (Flip-Logik
  stimmt), aber einmal real ausdrucken/falten und gegenprüfen, ob die
  Standfüße stabil genug stehen.
- **NOBO-Untertitel** „Onboarding-Tool für die Schüleraufnahme" — Wortlaut
  ändern, falls gewünscht (Start- + Login-Seite).

## Später

- **Button „Zug-Vorschläge übernehmen" wieder rausnehmen?** Sobald die
  Klassen/Züge verlässlich *vor* dem Sync angelegt werden, ordnet
  `sync_submissions` alles direkt zu und es gibt keine offenen Vorschläge
  mehr → Button (und `_zug_vorschlaege` / `zuege_uebernehmen`) kann weg.
  Solange Klassen teils erst nach dem Sync entstehen, wird er noch
  gebraucht. Nach einem kompletten Aufnahme-Durchlauf prüfen.

- **Anmeldungen zurücksetzen als Admin-Button**: `flask reset-registrations`
  (löscht nur die `registration`-Tabelle) im Admin-Bereich als Button
  abbilden – mit deutlicher Rückfrage/Bestätigung, nur für Dev/Test.
  Aktuell nur per CLI (`docker compose exec app flask reset-registrations`).
- **`foerderbedarf_art`**: kommt per Sync rein, wird aber nur als Fallback
  gezeichnet (wenn `foerderschwerpunkt` leer ist). Klären, ob beide Felder
  wirklich getrennt gebraucht werden.
- **Volles Bearbeiten-Formular + Zug/Beruf-Konsistenz**: Wenn im neuen
  „Anmeldung bearbeiten"-Formular der Beruf geändert wird, bleibt eine
  bereits gesetzte Zug-Zuordnung unangetastet – der Zug kann dann zu einem
  anderen Bildungsgang gehören als der (neue) Beruf. Kein Auto-Fix bisher,
  nur über das Zug-Dropdown in der Übersicht manuell korrigierbar.
- **„Realschule" / „Hauptschule" ersetzen**: Laut Nutzer müssen diese
  Bezeichnungen perspektivisch raus/ersetzt werden (Details noch zu
  klären). Fundstelle: `app/models.py` (`LETZTE_SCHULE_CHOICES`, Codes
  `HS`/`RS`), ggf. auch Stammdatenblatt-Layout/PDF-Vorlage prüfen, falls
  die Begriffe dort ebenfalls vorkommen.

## Zurückgestellt

- **Datenbereinigung im Tool selbst**: alte/abgeschlossene Anmeldungen nach
  Fristablauf löschen/archivieren. Ergänzt die WordPress-Bereinigung
  (`FLUENTFORM_RETENTION_DAYS` zeigt jetzt schon „WP: noch X Tage" an). Noch
  nicht spezifiziert: Frist, Definition „abgeschlossen", Löschen vs.
  Archivieren.
