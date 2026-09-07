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

## Offen / vom Nutzer gegenzuprüfen

- **Logo für hellen Hintergrund**: Kopfleiste ist jetzt weiß, das aktuelle
  Logo ist für dunklen Grund. Neues Logo hochladen (gilt auch fürs
  Namensschild).
- **WebUntis-Export**: echten Export einmal in Excel öffnen und Farben/
  Streifen/Datumsformat gegenprüfen (Fix: Tabellen-Range auf alle Zeilen +
  Schrift-Reset + `DD.MM.YYYY` erzwungen).
- **Namensschild**: Falt-/Stellgeometrie ggf. anpassen (Name höher/tiefer,
  Logo-Größe) — auf Rückmeldung.
- **NOBO-Untertitel** „Onboarding-Tool für die Schüleraufnahme" — Wortlaut
  ändern, falls gewünscht (Start- + Login-Seite).
- **`ausbildung_bis` zum Pflichtfeld** im WP-Formular machen (dann ist der
  berechnete „letzter Schultag" für alle regulären SuS gefüllt).

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

## Zurückgestellt

- **Datenbereinigung im Tool selbst**: alte/abgeschlossene Anmeldungen nach
  Fristablauf löschen/archivieren. Ergänzt die WordPress-Bereinigung
  (`FLUENTFORM_RETENTION_DAYS` zeigt jetzt schon „WP: noch X Tage" an). Noch
  nicht spezifiziert: Frist, Definition „abgeschlossen", Löschen vs.
  Archivieren.
