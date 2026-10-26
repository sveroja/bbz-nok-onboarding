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
    PasswordField, SelectMultipleField, SubmitField, TextAreaField,
)
from wtforms.validators import (
    DataRequired, Length, Regexp, Optional as OptionalValidator
)
from wtforms.widgets import ListWidget, CheckboxInput

from .models import (
    Abteilung, Bildungsgang, KREISE_SH, SPRACHNIVEAU_CHOICES,
    GESCHLECHT_CHOICES, KONFESSION_CHOICES, KAMMER_CHOICES,
    LETZTE_SCHULE_CHOICES, ALLGEMEINBILDENDER_ABSCHLUSS_CHOICES,
    ART_ABSCHLUSS_CHOICES,
)

# Fuer die ca. 17 nullable Boolean-Spalten an Registration (ja/nein-Fragen
# aus dem Aufnahmebogen): ein SelectField statt BooleanField, damit "keine
# Angabe" (None) beim Bearbeiten nicht versehentlich zu "nein" (False) wird
# (siehe models.py-Docstring: "keine Angabe" muss von False unterscheidbar
# sein). TRI_STATE_FIELDS in routes/teacher.py listet, welche Felder das
# betrifft; dort auch form_to_tri_state/tri_state_to_form verwendet.
JA_NEIN_CHOICES = [("", "– keine Angabe –"), ("ja", "ja"), ("nein", "nein")]


def tri_state_to_form(value) -> str:
    """True/False/None -> "ja"/"nein"/"" (fuers Vorbelegen des SelectField)."""
    if value is True:
        return "ja"
    if value is False:
        return "nein"
    return ""


def form_to_tri_state(value):
    """Gegenstueck zu tri_state_to_form - String aus dem Formular -> Bool/None."""
    if value == "ja":
        return True
    if value == "nein":
        return False
    return None

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


class RegistrationForm(FlaskForm):
    """Vollstaendige Anmeldung bearbeiten - alle Sektionen des Aufnahmebogens,
    nicht nur die LK-Nachpflege-Felder. Fuer Korrekturen direkt aus der
    Uebersicht (z.B. Vertipper der/des SuS beim Ausfuellen).

    zug_id und status laufen weiterhin ueber eigene Aktionen in der
    Uebersicht (Dropdown bzw. "geprüft"-Button), daher hier nicht enthalten.
    Die vielen nullable Boolean-Spalten sind als JA_NEIN_CHOICES-SelectField
    modelliert (siehe dort) statt als BooleanField - Ausnahme ist
    `zeugnis_geprueft`, das weiterhin eine echte Checkbox ist und beim
    Setzen `zeugnis_geprueft_am` auf heute setzt (siehe edit_registration).
    """
    # -- Sektion 1: Klassendaten (LK) --
    hauptlistennummer = StringField(
        "Hauptlistennummer", validators=[OptionalValidator(), Length(max=50)])
    aufnahmedatum = DateField(
        "Aufnahmedatum (Beginn der Ausbildung)", validators=[OptionalValidator()])
    eintrittsdatum = DateField(
        "Eintrittsdatum (in unsere Schule)", validators=[OptionalValidator()])
    nachteilsausgleich = TextAreaField(
        "Nachteilsausgleich", validators=[OptionalValidator()])

    # -- Sektion 2: Schülerdaten --
    nachname = StringField("Nachname", validators=[OptionalValidator(), Length(max=150)])
    vorname = StringField("Vorname", validators=[OptionalValidator(), Length(max=150)])
    geburtsname = StringField("Geburtsname", validators=[OptionalValidator(), Length(max=150)])
    geburtsdatum = DateField("Geburtsdatum", validators=[OptionalValidator()])
    geschlecht = SelectField(
        "Geschlecht", choices=[("", "– keine Angabe –")] + GESCHLECHT_CHOICES,
        validators=[OptionalValidator()])
    geburtsland = StringField("Geburtsland", validators=[OptionalValidator(), Length(max=100)])
    geburtsort = StringField("Geburtsort", validators=[OptionalValidator(), Length(max=150)])
    staatsangehoerigkeit_1 = StringField(
        "1. Staatsangehörigkeit", validators=[OptionalValidator(), Length(max=100)])
    staatsangehoerigkeit_2 = StringField(
        "2. Staatsangehörigkeit", validators=[OptionalValidator(), Length(max=100)])
    muttersprache = StringField("Muttersprache", validators=[OptionalValidator(), Length(max=100)])
    jahr_des_zuzugs = StringField("Jahr des Zuzugs", validators=[OptionalValidator(), Length(max=10)])
    daz_bedarf = SelectField(
        "DaZ-Zusatzunterricht benötigt (Sprachniveau < C1)",
        choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    sprachniveau = SelectField(
        "DaZ-Sprachniveau",
        choices=[("", "– keine Angabe –")] + [(s, s) for s in SPRACHNIVEAU_CHOICES],
        validators=[OptionalValidator()])
    sprachniveau_nachweis = SelectField(
        "DaZ-Zertifikat liegt vor", choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    zug_bool = SelectField(
        "Zug laut Aufnahmebogen bereits bekannt",
        choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    zug_value = StringField(
        "Zug (a/b/c/d, laut Aufnahmebogen - nur Vorschlag, s. Dropdown)",
        validators=[OptionalValidator(), Length(max=5)])

    # -- Sektion 3: Adress-/Kontaktdaten --
    wohnt_bei = StringField("Wohnt bei", validators=[OptionalValidator(), Length(max=200)])
    strasse = StringField("Straße", validators=[OptionalValidator(), Length(max=200)])
    plz = StringField("PLZ", validators=[OptionalValidator(), Length(max=10)])
    ort = StringField("Ort", validators=[OptionalValidator(), Length(max=150)])
    kreis = StringField("Kreis", validators=[OptionalValidator(), Length(max=100)])
    telefon = StringField("Telefon", validators=[OptionalValidator(), Length(max=50)])
    email = StringField("E-Mail", validators=[OptionalValidator(), Length(max=200)])
    konfession = SelectField(
        "Konfession", choices=[("", "– keine Angabe –")] + KONFESSION_CHOICES,
        validators=[OptionalValidator()])
    foerderbedarf = SelectField(
        "Förderbedarf", choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    foerderschwerpunkt = StringField(
        "Förderschwerpunkt", validators=[OptionalValidator(), Length(max=150)])
    foerderbedarf_art = StringField(
        "Art des Förderbedarfs", validators=[OptionalValidator(), Length(max=150)])

    # -- Sektion 4: Eltern/Ansprechpartner/Hauptwohnsitz --
    eltern_nachname = StringField("Nachname", validators=[OptionalValidator(), Length(max=150)])
    eltern_vorname = StringField("Vorname", validators=[OptionalValidator(), Length(max=150)])
    eltern_strasse = StringField("Straße", validators=[OptionalValidator(), Length(max=200)])
    eltern_plz = StringField("PLZ", validators=[OptionalValidator(), Length(max=10)])
    eltern_ort = StringField("Ort", validators=[OptionalValidator(), Length(max=150)])
    eltern_telefon = StringField("Telefon", validators=[OptionalValidator(), Length(max=50)])
    eltern_telefax = StringField("Telefax", validators=[OptionalValidator(), Length(max=50)])
    eltern_ist_vater = SelectField(
        "Person ist Vater", choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    eltern_ist_mutter = SelectField(
        "Person ist Mutter", choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    eltern_ist_ansprechpartner = SelectField(
        "Person ist Ansprechpartner/in", choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    eltern_hauptwohnsitz = SelectField(
        "Gemeldeter Hauptwohnsitz bei dieser Person",
        choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    bundesland_kuerzel = StringField(
        "Kürzel des Bundeslands", validators=[OptionalValidator(), Length(max=10)])

    # -- Sektion 5: Ausbildungsverhältnis (nur duale Ausbildung) --
    betrieb_name = StringField("Betrieb", validators=[OptionalValidator(), Length(max=200)])
    betrieb_kammer = SelectField(
        "Kammer", choices=[("", "– keine Angabe –")] + KAMMER_CHOICES,
        validators=[OptionalValidator()])
    ausbildung_von = DateField("Ausbildung von", validators=[OptionalValidator()])
    ausbildung_bis = DateField("Ausbildung bis", validators=[OptionalValidator()])
    betrieb_kreis = StringField("Kreis (Betrieb)", validators=[OptionalValidator(), Length(max=100)])
    betrieb_strasse = StringField(
        "Straße (Betrieb)", validators=[OptionalValidator(), Length(max=200)])
    betrieb_plz = StringField("PLZ (Betrieb)", validators=[OptionalValidator(), Length(max=10)])
    betrieb_ort = StringField("Ort (Betrieb)", validators=[OptionalValidator(), Length(max=150)])
    betrieb_telefon = StringField(
        "Telefon (Betrieb)", validators=[OptionalValidator(), Length(max=50)])
    betrieb_fax = StringField("Fax (Betrieb)", validators=[OptionalValidator(), Length(max=50)])
    betrieb_email = StringField(
        "E-Mail (Betrieb)", validators=[OptionalValidator(), Length(max=200)])
    beruf = SelectField("Beruf / Bildungsgang", validators=[OptionalValidator()])
    fachrichtung = StringField("Fachrichtung", validators=[OptionalValidator(), Length(max=200)])
    praktikant = SelectField(
        "Praktikant/in", choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    umschueler = SelectField(
        "Umschüler/in", choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    umschulungsvertrag_vorhanden = SelectField(
        "Umschulungsvertrag vorhanden", choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    kostenuebernahme_vorhanden = SelectField(
        "Kostenübernahmeerklärung vorhanden",
        choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])

    # -- Sektion 6: Bisheriger schulischer Werdegang --
    letzte_schule_kurzform = SelectField(
        "Zuletzt besuchte Schulart",
        choices=[("", "– keine Angabe –")] + LETZTE_SCHULE_CHOICES,
        validators=[OptionalValidator()])
    jahr_verlassen = StringField("Jahr verlassen", validators=[OptionalValidator(), Length(max=10)])
    klassenstufe = StringField("Klassenstufe", validators=[OptionalValidator(), Length(max=20)])
    mit_abschluss_beendet = SelectField(
        "Mit Abschluss beendet", choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    art_abschluss_letzte_schule = SelectField(
        "Art des Abschlusses (letzte Schule)",
        choices=[("", "– keine Angabe –")] + ART_ABSCHLUSS_CHOICES,
        validators=[OptionalValidator()])
    allgemeinbildender_abschluss = SelectField(
        "Allgemeinbildender Abschluss",
        choices=[("", "– keine Angabe –")] + ALLGEMEINBILDENDER_ABSCHLUSS_CHOICES,
        validators=[OptionalValidator()])
    lrs = SelectField(
        "Lese-Rechtschreib-Schwäche (LRS)",
        choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])

    # -- Sektion 7: Schulische Abschlüsse am BBZ --
    foerderzentrum = StringField(
        "Zuletzt zuständiges Förderzentrum", validators=[OptionalValidator(), Length(max=200)])
    esa_5_jahre_englisch = SelectField(
        "5 Jahre Englischunterricht erteilt",
        choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    esa_englisch_ausreichend = SelectField(
        "Englischnote mind. ausreichend",
        choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    zeugnis_geprueft = BooleanField(
        "Zeugnis geprüft (setzt das Datum auf heute)", validators=[OptionalValidator()])
    bos_fos_beruf = StringField(
        "Beruf (nur BOS/FOS)", validators=[OptionalValidator(), Length(max=200)])
    zweite_fremdsprache = SelectField(
        "2. Fremdsprache belegen", choices=JA_NEIN_CHOICES, validators=[OptionalValidator()])
    qualifizierungsnachweise_am = DateField(
        "Qualifizierungsnachweise vorgelegen am", validators=[OptionalValidator()])

    # -- Interne LK-Notizen --
    notizen = TextAreaField("Notizen (intern)", validators=[OptionalValidator()])

    submit = SubmitField("Speichern")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.beruf.choices = [("", "– keine Angabe –")] + [
            (b.code, b.name) for b in Bildungsgang.query.order_by(Bildungsgang.name).all()
            if b.code
        ]


class BildungsgangKreisForm(FlaskForm):
    """Welche Kreise/kreisfreien Staedte duerfen fuer einen Bildungsgang an
    dieser Schule beschult werden (Bezirksfachklassen-Regelung SHIBB).
    """
    landesweit = BooleanField(
        "Landesberufsschule (ganz Schleswig-Holstein, keine Kreis-Beschränkung)",
        validators=[OptionalValidator()],
    )
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


class BildungsgangImportForm(FlaskForm):
    datei = FileField(
        "JSON-Datei (Export von \"Bildungsgänge exportieren\")",
        validators=[
            DataRequired("Bitte eine Datei auswählen."),
            FileAllowed(["json"], "Nur JSON erlaubt."),
            FileSize(max_size=2 * 1024 * 1024, message="Datei zu groß (max. 2 MB)."),
        ],
    )
    submit = SubmitField("Importieren")


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
