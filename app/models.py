"""Datenbankmodelle."""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db, login_manager


def _utcnow():
    """Aktueller UTC-Zeitpunkt (timezone-aware)."""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """Lehrer:innen und Admins. Eltern/SuS haben KEIN Konto."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "admin" | "teacher"
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"


class Registration(db.Model):
    """Eine Schüler-Anmeldung."""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    status = db.Column(db.String(20), default="new", nullable=False)  # "new" | "checked"

    # Schülerdaten
    nachname = db.Column(db.String(150), nullable=False)
    vorname = db.Column(db.String(150), nullable=False)
    geburtsdatum = db.Column(db.Date, nullable=False)

    # Adresse
    strasse = db.Column(db.String(200), nullable=False)
    plz = db.Column(db.String(10), nullable=False)
    ort = db.Column(db.String(150), nullable=False)

    # PLZ-Prüfung: True/False = geprüft, None = konnte nicht geprüft werden
    plz_ok = db.Column(db.Boolean, nullable=True)
    plz_checked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Registration {self.id}: {self.vorname} {self.nachname}>"


class PlzRule(db.Model):
    """Aktuell genau eine aktive Regel. Tabelle erlaubt aber Historie."""
    id = db.Column(db.Integer, primary_key=True)
    reference_plz = db.Column(db.String(10), nullable=False, default="24768")
    allowed_kreis = db.Column(db.String(200), nullable=True)
    allowed_bezirk = db.Column(db.String(200), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)


@login_manager.user_loader
def load_user(user_id: str):
    # SQLAlchemy 2.x: db.session.get statt Query.get
    return db.session.get(User, int(user_id))
