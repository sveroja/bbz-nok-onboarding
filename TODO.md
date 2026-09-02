# TODO

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

- **Anmeldungen zurücksetzen als Admin-Button**: `flask reset-registrations`
  (löscht nur die `registration`-Tabelle) im Admin-Bereich als Button
  abbilden – mit deutlicher Rückfrage/Bestätigung, nur für Dev/Test.
  Aktuell nur per CLI (`docker compose exec app flask reset-registrations`).
- **Ganze Klassen-Bearbeitung**: Name/Bildungsgänge einer bestehenden Klasse
  ändern (bisher nur Anlegen + Löschen; Klassenlehrer/erster Schultag über
  „Gemeinsame Daten").
- **`foerderbedarf_art`**: kommt per Sync rein, wird aber nur als Fallback
  gezeichnet (wenn `foerderschwerpunkt` leer ist). Klären, ob beide Felder
  wirklich getrennt gebraucht werden.

## Zurückgestellt

- **Datenbereinigung im Tool selbst**: alte/abgeschlossene Anmeldungen nach
  Fristablauf löschen/archivieren. Ergänzt die WordPress-Bereinigung
  (`FLUENTFORM_RETENTION_DAYS` zeigt jetzt schon „WP: noch X Tage" an). Noch
  nicht spezifiziert: Frist, Definition „abgeschlossen", Löschen vs.
  Archivieren.
