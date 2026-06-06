"""Einstiegspunkt für Flask.

Aufruf:
    flask --app run.py init-db
    flask --app run.py run
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Lokaler Start (nur Entwicklung). In Produktion gunicorn nutzen.
    app.run(host="127.0.0.1", port=5000)
