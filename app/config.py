"""Konfigurationsklassen.

Werte werden aus Umgebungsvariablen (.env) geladen.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class BaseConfig:
    # Pflicht: muss aus ENV kommen
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # SQLite in instance/-Ordner (Flask-Standard)
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'schule_app.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session-Cookie-Sicherheit
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False") == "True"

    # CSRF
    WTF_CSRF_TIME_LIMIT = 3600  # 1 Stunde

    # OpenPLZ
    REFERENCE_PLZ = os.environ.get("REFERENCE_PLZ", "24768")
    OPENPLZ_TIMEOUT = 5  # Sekunden

    # Fluent-Forms-Anbindung (WordPress)
    FLUENTFORM_BASE_URL = os.environ.get("FLUENTFORM_BASE_URL", "")
    FLUENTFORM_FORM_ID = os.environ.get("FLUENTFORM_FORM_ID", "")
    FLUENTFORM_USERNAME = os.environ.get("FLUENTFORM_USERNAME", "")
    FLUENTFORM_PASSWORD = os.environ.get("FLUENTFORM_PASSWORD", "")

    # Rate-Limit-Storage (in-Memory reicht für eine Instanz)
    RATELIMIT_STORAGE_URI = "memory://"


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    # In Produktion erzwingen wir HTTPS-only Cookies
    SESSION_COOKIE_SECURE = True


def get_config():
    """Wählt die passende Config-Klasse basierend auf FLASK_ENV."""
    env = os.environ.get("FLASK_ENV", "development").lower()
    if env == "production":
        return ProductionConfig
    return DevelopmentConfig
