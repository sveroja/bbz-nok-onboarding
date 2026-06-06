"""Zentrale Flask-Extensions.

Werden hier instanziiert, damit Models und Routen sie importieren
können, ohne Zirkularimporte zu erzeugen. Die eigentliche Bindung
an die App-Instanz passiert in app/__init__.py.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # keine globalen Limits, nur dort wo wir es brauchen
)

# Login-Konfiguration
login_manager.login_view = "auth.login"
login_manager.login_message = "Bitte melde dich an."
login_manager.login_message_category = "info"
