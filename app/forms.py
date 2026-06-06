"""Flask-WTF-Formulare.

Vorteil gegenüber `request.form.get(...)`:
- CSRF-Token automatisch
- Validierung deklarativ
- Saubere Wiederanzeige bei Fehlern
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DateField, SubmitField
from wtforms.validators import (
    DataRequired, Length, Regexp, Optional as OptionalValidator
)


class LoginForm(FlaskForm):
    username = StringField(
        "Benutzername",
        validators=[DataRequired(message="Bitte Benutzername angeben."),
                    Length(max=150)],
    )
    password = PasswordField(
        "Passwort",
        validators=[DataRequired(message="Bitte Passwort angeben.")],
    )
    submit = SubmitField("Anmelden")


class RegisterStep1Form(FlaskForm):
    """Schritt 1: Schülerdaten."""
    vorname = StringField(
        "Vorname",
        validators=[DataRequired("Pflichtfeld."), Length(min=1, max=150)],
    )
    nachname = StringField(
        "Nachname",
        validators=[DataRequired("Pflichtfeld."), Length(min=1, max=150)],
    )
    geburtsdatum = DateField(
        "Geburtsdatum",
        validators=[DataRequired("Pflichtfeld.")],
        format="%Y-%m-%d",
    )
    submit = SubmitField("Weiter")


class RegisterStep2Form(FlaskForm):
    """Schritt 2: Adresse."""
    strasse = StringField(
        "Straße und Hausnummer",
        validators=[DataRequired("Pflichtfeld."), Length(min=1, max=200)],
    )
    plz = StringField(
        "PLZ",
        validators=[
            DataRequired("Pflichtfeld."),
            Regexp(r"^\d{5}$", message="Bitte 5-stellige PLZ angeben."),
        ],
    )
    ort = StringField(
        "Ort",
        validators=[DataRequired("Pflichtfeld."), Length(min=1, max=150)],
    )
    submit = SubmitField("Weiter")


class SummarySubmitForm(FlaskForm):
    """Reiner CSRF-Schutz für den finalen Submit-Button."""
    submit = SubmitField("Anmeldung absenden")


class ActionForm(FlaskForm):
    """Generisches Form nur für CSRF-Token bei POST-Buttons (löschen, prüfen)."""
    submit = SubmitField()


class PlzRuleForm(FlaskForm):
    reference_plz = StringField(
        "Referenz-PLZ (Schule)",
        validators=[
            DataRequired("Pflichtfeld."),
            Regexp(r"^\d{5}$", message="5-stellige PLZ."),
        ],
    )
    allowed_kreis = StringField(
        "Erlaubter Kreis (optional, sonst gleicher Kreis wie Referenz-PLZ)",
        validators=[OptionalValidator(), Length(max=200)],
    )
    allowed_bezirk = StringField(
        "Erlaubter Regierungsbezirk (optional)",
        validators=[OptionalValidator(), Length(max=200)],
    )
    submit = SubmitField("Speichern")
