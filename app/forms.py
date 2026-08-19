"""Flask-WTF-Formulare.

Vorteil gegenüber `request.form.get(...)`:
- CSRF-Token automatisch
- Validierung deklarativ
- Saubere Wiederanzeige bei Fehlern
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import (
    BooleanField, DateField, RadioField, SelectField, StringField,
    PasswordField, SelectMultipleField, SubmitField,
)
from wtforms.validators import (
    DataRequired, Length, Regexp, Optional as OptionalValidator
)
from wtforms.widgets import ListWidget, CheckboxInput

from .models import Abteilung, Bildungsgang, KREISE_SH, SPRACHNIVEAU_CHOICES

LOGO_MAX_SIZE_MB = 2


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


class KlasseForm(FlaskForm):
    name = StringField(
        "Name (z.B. ELI026a)",
        validators=[DataRequired("Pflichtfeld."), Length(max=50)],
    )
    zustaendige_lehrkraft = StringField(
        "Zuständige Lehrkraft (optional, nur zur Anzeige)",
        validators=[OptionalValidator(), Length(max=150)],
    )
    bildungsgaenge = SelectMultipleField(
        "Bildungsgänge",
        option_widget=CheckboxInput(),
        widget=ListWidget(prefix_label=False),
        validators=[DataRequired("Mindestens einen Bildungsgang auswählen.")],
    )
    submit = SubmitField("Klasse anlegen")

    def __init__(self, *args, **kwargs):
        # Choices erst hier statt als Klassenattribut setzen: Bildungsgang
        # kommt jetzt aus der DB (admin-pflegbar), die ist beim Laden dieses
        # Moduls noch nicht verfuegbar.
        super().__init__(*args, **kwargs)
        self.bildungsgaenge.choices = [
            (b.code, b.name) for b in Bildungsgang.query.order_by(Bildungsgang.name).all()
        ]


class RegistrationLKForm(FlaskForm):
    """Felder aus Sektion 1 (Klassendaten) + DaZ-Sprachniveau - beides von
    der LK im Tool nachgepflegt, steht nicht/nicht vollstaendig im
    Aufnahmebogen bzw. wird nicht per Fluent-Forms-Sync geliefert.
    """
    hauptlistennummer = StringField(
        "Hauptlistennummer", validators=[OptionalValidator(), Length(max=50)],
    )
    aufnahmedatum = DateField(
        "Aufnahmedatum (Beginn der Ausbildung)", validators=[OptionalValidator()],
    )
    eintrittsdatum = DateField(
        "Eintrittsdatum (in unsere Schule)", validators=[OptionalValidator()],
    )
    sprachniveau = SelectField(
        "DaZ-Sprachniveau",
        choices=[("", "– keine Angabe –")] + [(s, s) for s in SPRACHNIVEAU_CHOICES],
        validators=[OptionalValidator()],
    )
    sprachniveau_nachweis = BooleanField(
        "DaZ-Zertifikat liegt vor", validators=[OptionalValidator()],
    )
    submit = SubmitField("Speichern")


class BildungsgangKreisForm(FlaskForm):
    """Welche Kreise/kreisfreien Staedte duerfen fuer einen Bildungsgang an
    dieser Schule beschult werden (Bezirksfachklassen-Regelung SHIBB).
    """
    kreise = SelectMultipleField(
        "Erlaubte Kreise/kreisfreie Städte",
        choices=[(k, k) for k in KREISE_SH],
        option_widget=CheckboxInput(),
        widget=ListWidget(prefix_label=False),
        validators=[OptionalValidator()],
    )
    submit = SubmitField("Speichern")


class AbteilungForm(FlaskForm):
    name = StringField(
        "Abteilung (z.B. Elektrotechnik)",
        validators=[DataRequired("Pflichtfeld."), Length(max=150)],
    )
    submit = SubmitField("Abteilung hinzufügen")


class BildungsgangForm(FlaskForm):
    name = StringField(
        "Bildungsgang / Beruf",
        validators=[DataRequired("Pflichtfeld."), Length(max=200)],
    )
    code = StringField(
        "Code (= Value im Fluent-Forms-Dropdown, z.B. maurer)",
        validators=[
            DataRequired("Pflichtfeld."), Length(max=100),
            Regexp(r"^[a-z0-9_]+$", message="Nur Kleinbuchstaben, Ziffern, Unterstrich."),
        ],
    )
    abteilung_id = RadioField(
        "Abteilung", coerce=int, validators=[OptionalValidator()],
    )
    submit = SubmitField("Beruf hinzufügen")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.abteilung_id.choices = [
            (a.id, a.name) for a in Abteilung.query.order_by(Abteilung.name).all()
        ]


class VorlageForm(FlaskForm):
    datei = FileField(
        "Datei",
        validators=[
            DataRequired("Bitte eine Datei auswählen."),
            FileAllowed(["pdf", "xlsx"], "Nur PDF oder XLSX erlaubt."),
            FileSize(max_size=10 * 1024 * 1024,
                     message="Datei zu groß (max. 10 MB)."),
        ],
    )
    submit = SubmitField("Hochladen")


class LogoForm(FlaskForm):
    logo = FileField(
        "Logo (PNG oder JPG, max. {} MB)".format(LOGO_MAX_SIZE_MB),
        validators=[
            DataRequired("Bitte eine Datei auswählen."),
            FileAllowed(["png", "jpg", "jpeg"], "Nur PNG oder JPG erlaubt."),
            FileSize(max_size=LOGO_MAX_SIZE_MB * 1024 * 1024,
                     message="Datei zu groß (max. {} MB).".format(LOGO_MAX_SIZE_MB)),
        ],
    )
    submit = SubmitField("Hochladen")
