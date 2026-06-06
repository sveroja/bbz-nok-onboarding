"""Application Factory.

Lädt .env, baut die Flask-App, bindet Extensions und Blueprints.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

# .env laden, BEVOR irgendwer config liest
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .config import get_config
from .extensions import db, login_manager, csrf, limiter


def create_app(config_class=None) -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    # Config laden
    app.config.from_object(config_class or get_config())

    # Sicherstellen, dass instance/-Ordner existiert (für SQLite)
    Path(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")).parent.mkdir(
        parents=True, exist_ok=True
    )

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY ist nicht gesetzt! Bitte .env-Datei prüfen "
            "(siehe .env.example)."
        )

    # Logging
    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Extensions binden
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Models importieren, damit SQLAlchemy sie kennt (für create_all)
    from . import models  # noqa: F401

    # Blueprints registrieren
    from .routes.public import bp as public_bp
    from .routes.auth import bp as auth_bp
    from .routes.teacher import bp as teacher_bp
    from .routes.admin import bp as admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(admin_bp)

    # CLI-Befehle
    from .cli import register_cli
    register_cli(app)

    return app
