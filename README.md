# BBZ NOK Onboarding

Internes Tool für Klassenlehrkräfte am BBZ am Nord-Ostsee-Kanal zur Verwaltung
der Schüleraufnahme nach dem offiziellen Aufnahmebogen 2026/27.

Intern auch **NOBO** (NOK-Onboarding-Board) genannt.

## Was es macht

- **SuS / Betriebe** füllen ein Online-Formular auf der Schul-Website aus (Fluent Forms in WordPress)
- **Flask-Tool** holt die Anmeldungen über die Fluent-Forms-REST-API ab
- **Klassenlehrkräfte** prüfen, ergänzen, exportieren die Anmeldungen im internen Web-UI
- **PLZ-Check** gegen [OpenPLZ-API](https://openplzapi.org): liegt die Schüleradresse im erlaubten Kreis?

## Architektur in einem Bild

```
┌────────────────┐   füllt aus    ┌──────────────────┐
│ SuS / Betrieb  │ ─────────────► │ Fluent Forms     │
└────────────────┘                │ (WordPress)      │
                                  └────────┬─────────┘
                                           │
                                           │ REST API
                                           │ (Basic Auth,
                                           │ Application Password)
                                           ▼
                                  ┌──────────────────┐
                                  │ Flask-App        │
                                  │ + SQLite         │
                                  │ + OpenPLZ-Check  │
                                  └────────┬─────────┘
                                           │ Web-UI
                                           ▼
                                  ┌──────────────────┐
                                  │ Klassenlehrkraft │
                                  └──────────────────┘
```

Datenfluss-Richtung: **Flask pollt WP** (kein Webhook). Vorteil: Flask muss
nicht ins Internet erreichbar sein, läuft hinter VPN / im Intranet.

## Features

- **Fluent-Forms-Sync**: holt Submissions per REST API (Pagination, Dubletten-Erkennung via `external_id`)
- **Mapping** auf das vollständige Aufnahmebogen-Schema (~60 Felder in 7 Sektionen)
- **Auffangbecken** `extra_data` für unbekannte WP-Felder (nichts geht verloren)
- **PLZ-Sprengel-Prüfung** mit dreiwertigem Status (passt / passt nicht / unklar)
- **Application Factory + Blueprints**, sauber strukturierte Flask-App
- **CSRF-Schutz** auf allen Formularen (Flask-WTF)
- **Login-Rate-Limit** (10/min), **Sync-Rate-Limit** (6/min)
- **Rollen-Decorator** `@role_required("admin", "teacher")`
- **Secrets ausschließlich aus `.env`**, niemals im Code oder Repo
- **SQLAlchemy 2.x**, UTC-aware Timestamps

## Voraussetzungen

- Docker + Docker Compose auf dem Hostsystem
- WordPress mit installiertem Fluent Forms (Free oder Pro)
- HTTPS auf der WordPress-Seite (Pflicht für Application Passwords)
- **Kein** Hoster-Verzeichnisschutz (Basic Auth) vor dem WordPress, weil das mit Application Passwords kollidiert

## Schnellstart

```bash
git clone git@github.com:DEIN-USERNAME/bbz-nok-onboarding.git
cd bbz-nok-onboarding
cp .env.example .env
# .env editieren - siehe Abschnitt "Konfiguration"
docker compose up -d --build
docker compose logs -f app
```

App läuft auf `http://<host>:8000`. Login als `admin` oder `lehrer` mit den
Passwörtern aus `.env`.

## Konfiguration (`.env`)

| Variable | Bedeutung |
|---|---|
| `SECRET_KEY` | Flask-Session-Schlüssel. `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD` | Initial-Passwort für den `admin`-Nutzer |
| `TEACHER_PASSWORD` | Initial-Passwort für den `lehrer`-Nutzer |
| `REFERENCE_PLZ` | PLZ der Schule (für Sprengel-Prüfung) |
| `SESSION_COOKIE_SECURE` | `True` in Produktion (HTTPS via Reverse Proxy) |
| `FLUENTFORM_BASE_URL` | Basis-URL des WordPress (ohne abschließendes `/`) |
| `FLUENTFORM_FORM_ID` | Numerische ID des Aufnahmebogen-Formulars in Fluent Forms |
| `FLUENTFORM_USERNAME` | WordPress-Username (nicht E-Mail) |
| `FLUENTFORM_PASSWORD` | WP-Application-Password (mit Leerzeichen!) |

### WordPress-Application-Password einrichten

1. WP Admin → **Users** → **Profile**
2. Ganz nach unten zu **Application Passwords**
3. Name vergeben (z.B. `bbz-onboarding`) → **Add New**
4. Token wird **einmalig** angezeigt – sichern und in `.env` als `FLUENTFORM_PASSWORD` eintragen (Leerzeichen mitkopieren)

## Bedienung

### Anmeldungen synchronisieren

**Per Button im UI:** Login als Lehrkraft → „Anmeldungen anzeigen" → **„Jetzt synchronisieren"**

**Per CLI im Container:**
```bash
docker compose exec app flask --app run.py sync-fluentform
```

Beides macht dasselbe: holt alle neuen Submissions aus WordPress ab,
übersetzt sie ins Aufnahmebogen-Schema, prüft die PLZ.

Dubletten werden über die `external_id` (Fluent-Forms-Submission-ID)
erkannt und übersprungen – mehrfaches Syncen ist also gefahrlos.

### Weitere Nutzer anlegen

```bash
docker compose exec app flask --app run.py create-user mariag teacher
```

Rollen: `admin` oder `teacher`. Passwort wird interaktiv abgefragt.

### CSV-Export

Im UI: „Anmeldungen anzeigen" → **„CSV-Export"**. UTF-8 mit BOM, damit Excel
die Umlaute korrekt darstellt.

### Backup der Datenbank

```bash
docker compose exec app sqlite3 /app/instance/schule_app.db \
  ".backup '/app/instance/backup-$(date +%F).db'"
docker cp schule-app:/app/instance/backup-$(date +%F).db ./
```

Das SQLite-Verzeichnis liegt im Named Volume `schule_data` und überlebt
Container-Neustarts.

## Updates einspielen

```bash
git pull
docker compose up -d --build
```

`init-db` wird beim Containerstart automatisch ausgeführt und ist idempotent
(legt nur fehlende Tabellen/Nutzer an, ändert nichts Bestehendes).

**Bei DB-Schema-Änderungen** (z.B. neue Spalten in `Registration`) ist der
aktuelle Stand noch ohne Migrations-Framework. Workaround: SQLite-Datei
sichern, dann `docker compose down -v && docker compose up -d --build` und
ggf. die Daten neu syncen (Dubletten-Schutz verhindert Duplikate).

## Mit Reverse Proxy (Produktion)

In `docker-compose.yml` die `ports:`-Sektion entfernen, Container in dasselbe
Docker-Netz wie den Reverse Proxy (nginx, Caddy, Traefik) hängen.

In `.env`:
```
FLASK_ENV=production
SESSION_COOKIE_SECURE=True
```

## Wenn das Formular geändert wird

Wir mappen WP-Felder explizit im Code (`FIELD_MAPPING` in `app/fluentform.py`).
Bewusst keine Auto-Erkennung, damit nichts unbemerkt verloren geht.

- **Feld umbenannt in Fluent Forms** → reißt den Sync. **Niemals** Name-Attributes
  in Fluent Forms ändern, die wir hier mappen. Labels (Anzeige) können sich
  jederzeit ändern, das ist nur Anzeige.
- **Neues Feld in Fluent Forms** → landet automatisch in `Registration.extra_data`
  als JSON. Geht nicht verloren. Wenn du es richtig auswerten willst:
  1. Spalte in `app/models.py` ergänzen
  2. Eintrag in `FIELD_MAPPING` in `app/fluentform.py` ergänzen
  3. ggf. zu `DATE_FIELDS` / `BOOL_FIELDS` hinzufügen
  4. Commit + Container neu bauen

## Projektstruktur

```
bbz-nok-onboarding/
├── .env.example
├── .gitignore
├── .dockerignore
├── docker-compose.yml
├── Dockerfile
├── docker/
│   └── entrypoint.sh
├── README.md
├── requirements.txt
├── run.py
├── instance/             # SQLite-DB (nicht im Repo)
└── app/
    ├── __init__.py       # create_app()
    ├── config.py         # Config-Klassen, lesen aus ENV
    ├── extensions.py     # db, login_manager, csrf, limiter
    ├── models.py         # User, Registration, PlzRule + Auswahllisten
    ├── decorators.py     # @role_required
    ├── forms.py          # Flask-WTF Forms (Login, Admin, Aktionen)
    ├── plz.py            # OpenPLZ-Anbindung mit Kreis-/Bezirks-Check
    ├── fluentform.py     # Fluent-Forms-Sync (APIClient, Mapping, sync_submissions)
    ├── cli.py            # init-db, create-user, sync-fluentform
    ├── routes/
    │   ├── public.py     # /
    │   ├── auth.py       # /login, /logout
    │   ├── teacher.py    # /teacher/* (inkl. /teacher/sync)
    │   └── admin.py      # /admin/* (PLZ-Regel pflegen)
    └── templates/
        ├── base.html
        ├── _form_macros.html
        ├── index.html
        ├── login.html
        ├── teacher_dashboard.html
        ├── teacher_registrations.html
        ├── admin_dashboard.html
        └── admin_plz.html
```

## Datenschutz-Hinweise

Die App speichert personenbezogene Daten von SuS und ihren Erziehungsberechtigten
sowie Daten von Ausbildungsbetrieben. Besonders schutzwürdig sind:

- Religion / Konfession (Art. 9 DSGVO)
- Förderbedarf, LRS, DaZ-Bedarf (Gesundheitsdaten, Art. 9 DSGVO)
- Geburtsland, Staatsangehörigkeit, Muttersprache (Herkunftsdaten)

**Vor Echteinsatz unbedingt klären:**

- Verarbeitungsverzeichnis (Art. 30 DSGVO)
- Aufbewahrungs- / Löschfristen (die DB wächst sonst unbegrenzt)
- Information der Eltern / SuS über Verarbeitung (Art. 13 DSGVO)
- Abstimmung mit dem schulischen Datenschutzbeauftragten
- TLS-Verschlüsselung in jedem Schritt (HTTPS auf WP, VPN für Flask-Zugriff)

## Lizenz / Mitwirkende

Internes Werkzeug des BBZ am Nord-Ostsee-Kanal. Nicht für Weiterverteilung gedacht.
