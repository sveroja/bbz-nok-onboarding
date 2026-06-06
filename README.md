# Schulanmeldung

Kleine Flask-App für die Online-Anmeldung an einer Schule.

- **SuS / Eltern**: füllen öffentlich ein 2-Schritt-Formular aus (später per API)
- **Lehrer:innen**: sehen Anmeldungen, markieren als geprüft, löschen, exportieren CSV (Zugriff per VPN/Intranet)
- **Admin**: pflegt PLZ-Regel

## Features

- Application Factory + Blueprints (sauber strukturiert)
- CSRF-Schutz auf allen Formularen (Flask-WTF)
- Login-Rate-Limit (10/min)
- Rollen-Decorator `@role_required("admin", "teacher")`
- PLZ-Check über [OpenPLZ API](https://openplzapi.org) mit echtem "unklar"-Status (kein stilles `False` bei API-Ausfall)
- Secrets ausschließlich aus `.env`
- SQLAlchemy 2.x Syntax, UTC-aware Timestamps

## Schnellstart (Docker)

```bash
cp .env.example .env
# .env editieren! SECRET_KEY, ADMIN_PASSWORD, TEACHER_PASSWORD
docker compose up -d --build
```

App auf `http://<host>:8000`. Details siehe unten.

## Standardnutzer

Werden bei `init-db` aus den ENV-Variablen `ADMIN_PASSWORD` und `TEACHER_PASSWORD` angelegt:

- `admin` (Rolle: admin)
- `lehrer` (Rolle: teacher)

## Deployment mit Docker (empfohlen)

```bash
# 1. .env vorbereiten (NICHT committen!)
cp .env.example .env
# .env editieren: SECRET_KEY, ADMIN_PASSWORD, TEACHER_PASSWORD
python3 -c "import secrets; print(secrets.token_hex(32))"

# 2. Bauen und starten
docker compose up -d --build

# 3. Logs anschauen
docker compose logs -f app
```

App läuft dann auf `http://<host>:8000`. Die SQLite-DB liegt im Named
Volume `schule_data` und überlebt Container-Neustarts.

### Updates einspielen

```bash
git pull
docker compose up -d --build
```

`init-db` wird beim Containerstart automatisch ausgeführt und ist idempotent
(legt nur fehlende Tabellen/Nutzer an, ändert nichts Bestehendes).

### Zusätzliche Nutzer im Container anlegen

```bash
docker compose exec app flask --app run.py create-user mariag teacher
```

### Backup der Datenbank

```bash
# In Volume-Inhalt reinschauen
docker compose exec app ls -la /app/instance

# Backup ziehen
docker compose exec app sqlite3 /app/instance/schule_app.db ".backup '/app/instance/backup-$(date +%F).db'"
docker cp schule-app:/app/instance/backup-$(date +%F).db ./
```

Oder direkt aus dem Named Volume per `docker run --rm -v schule_data:/data ...`.

### Mit Reverse Proxy (später)

Wenn TLS dazukommt: in `docker-compose.yml` die `ports:`-Sektion entfernen
und Container und Reverse Proxy ins gleiche Docker-Netz hängen. Dann zusätzlich
in `.env`:

```
FLASK_ENV=production
SESSION_COOKIE_SECURE=True
```

## Lokale Entwicklung (ohne Docker)

```bash
python -m venv venv
source venv/bin/activate            # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # editieren!
flask --app run.py init-db
flask --app run.py run
```

## Wichtige Punkte für den Produktivbetrieb

- starkes `SECRET_KEY` setzen (32+ zufällige Bytes)
- starke Passwörter für `admin` und `lehrer`
- regelmäßiges Backup von `instance/schule_app.db` (siehe oben)
- bei externer Erreichbarkeit: Reverse Proxy mit TLS davor

## Projektstruktur

```
schule_app/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── run.py                # flask --app run.py …
├── instance/             # SQLite-DB (nicht im Repo)
└── app/
    ├── __init__.py       # create_app()
    ├── config.py
    ├── extensions.py     # db, login_manager, csrf, limiter
    ├── models.py
    ├── decorators.py     # role_required
    ├── forms.py          # Flask-WTF Forms
    ├── plz.py            # OpenPLZ-Anbindung
    ├── cli.py            # init-db, create-user
    ├── routes/
    │   ├── public.py     # /, /register/*
    │   ├── auth.py       # /login, /logout
    │   ├── teacher.py    # /teacher/*
    │   └── admin.py      # /admin/*
    └── templates/
        ├── base.html
        ├── _form_macros.html
        ├── index.html
        ├── login.html
        ├── register_step1.html
        ├── register_step2.html
        ├── register_summary.html
        ├── register_done.html
        ├── teacher_dashboard.html
        ├── teacher_registrations.html
        ├── admin_dashboard.html
        └── admin_plz.html
```

## Datenschutz-Hinweise

Die App speichert personenbezogene Daten von (i.d.R. minderjährigen) Schüler:innen. Vor Echteinsatz sollten Sie klären:

- Verarbeitungsverzeichnis (Art. 30 DSGVO)
- Aufbewahrungs-/Löschfristen — die Datenbank wächst sonst unbegrenzt
- Information der Eltern über Verarbeitung (Art. 13 DSGVO)
- Abstimmung mit dem schulischen Datenschutzbeauftragten
