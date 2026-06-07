"""Datenbankmodelle.

Das Registration-Modell bildet den Schüleraufnahmebogen 2026/27 des
BBZ am Nord-Ostsee-Kanal ab. Die Felder sind in Sektionen gruppiert,
analog zum PDF-Aufnahmebogen:

  Sektion 1: Klassendaten             (durch LK auszufüllen)
  Sektion 2: Schülerdaten             (durch SuS)
  Sektion 3: Adress-/Kontaktdaten     (durch SuS)
  Sektion 4: Eltern/Ansprechpartner   (durch SuS)
  Sektion 5: Ausbildungsverhältnis    (durch SuS, nur duale Ausbildung)
  Sektion 6: Bisheriger Werdegang     (durch SuS)
  Sektion 7: Abschlüsse am BBZ        (durch LK)
  Nachteilsausgleich                  (durch LK)

Alle inhaltlichen Felder sind nullable, weil:
  - SuS-Pflichtfelder werden bereits in Fluent Forms validiert
  - LK-Felder werden später im Tool nachgepflegt
  - Konditionale Felder (z.B. Sektion 5 nur wenn duale Ausbildung) können fehlen
  - "keine Angabe" muss von "False" unterscheidbar sein
"""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db, login_manager


def _utcnow():
    """Aktueller UTC-Zeitpunkt (timezone-aware)."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Auswahllisten / Konstanten (für Forms und Anzeige)
# ---------------------------------------------------------------------------

GESCHLECHT_CHOICES = [
    ("maennlich", "männlich"),
    ("weiblich", "weiblich"),
    ("divers", "divers"),
    ("keine_angabe", "keine Angabe"),
]

KONFESSION_CHOICES = [
    ("ev", "evangelisch"),
    ("rk", "römisch-katholisch"),
    ("isl", "islamisch"),
    ("keine", "keine Angabe"),
]

KAMMER_CHOICES = [
    ("IHK", "IHK"),
    ("HK", "HK"),
    ("LWK", "LWK"),
]

# Tabelle 1 aus dem Aufnahmebogen: zuletzt besuchte Schulart
LETZTE_SCHULE_CHOICES = [
    ("AA",  "AA – Ausländische Schulen"),
    ("AVJ", "AVJ – Ausbildungsvorbereitendes Jahr"),
    ("BAS", "BAS – Berufsaufbauschule"),
    ("BAV", "BAV – Berufsschule, AV-SH"),
    ("BF1", "BF1 – Berufsfachschule 1"),
    ("BF2", "BF2 – Berufsfachschule 2"),
    ("BF3", "BF3 – Berufsfachschule 3"),
    ("BG",  "BG – Berufliches Gymnasium"),
    ("BGJ", "BGJ – Berufsgrundbildungsjahr (schulisch)"),
    ("BIK", "BIK – Berufsschule, BIK-DaZ"),
    ("BJA", "BJA – Berufsschule f. Jugendl. i. Ausbildungsverh."),
    ("BOS", "BOS – Berufsoberschule"),
    ("BVM", "BVM – Berufsvorbereitende Maßnahme"),
    ("EQ",  "EQ – Betriebliche Einstiegsqualifizierung"),
    ("FH",  "FH – Fachhochschule"),
    ("FOS", "FOS – Fachoberschule"),
    ("FS",  "FS – Fachschule"),
    ("GEM", "GEM – Gemeinschaftsschule"),
    ("GES", "GES – Gesamtschule"),
    ("GYM", "GYM – Gymnasium"),
    ("HS",  "HS – Hauptschule"),
    ("JOA", "JOA – Jugendliche ohne Ausbildung/Berufseingangsklasse"),
    ("REG", "REG – Regionalschule"),
    ("RS",  "RS – Realschule"),
    ("SON", "SON – Sonstige Schulen"),
    ("SOS", "SOS – Förderzentrum"),
]

# Tabelle 2: Art des letzten allgemeinbildenden Abschlusses
ALLGEMEINBILDENDER_ABSCHLUSS_CHOICES = [
    ("AH",   "AH – Allgemeine Hochschulreife (Abitur)"),
    ("EH",   "EH – Erweiterter Hauptschulabschluss"),
    ("FH",   "FH – Fachgebundene Hochschulreife"),
    ("FR",   "FR – Fachhochschulreife (schulischer Teil)"),
    ("FRv",  "FRv – Fachhochschulreife (vollständig)"),
    ("HA",   "HA – Hauptschulabschluss bzw. 1. allgemeinb. o. gleichw. Abschluss"),
    ("HAG8", "HAG8 – erster allg. Abschluss aus G8 in das BG versetzt"),
    ("OA",   "OA – ohne Abschluss"),
    ("RE",   "RE – Realschulabschluss oder gleichwertiger Abschluss"),
    ("SAGE", "SAGE – Sonderpäd. Abschluss FSP Geistige Entwicklung"),
    ("SAL",  "SAL – Sonderpäd. Abschluss FSP Lernen"),
]

# Tabelle 3: Art des Abschlusses der letzten Schule
ART_ABSCHLUSS_CHOICES = [
    ("VB01", "VB01 – Schulischer Abschluss einer Maßnahme an einer Berufsschule"),
    ("VB02", "VB02 – Berufsqualifizierender Abschluss BFS II und BFS III"),
    ("VB03", "VB03 – sonstiger beruflicher Abschluss (Fachschule, BOS, FOS, BG)"),
    ("VB04", "VB04 – kein beruflicher Abschluss / ohne berufliche Vorbildung"),
]

STATUS_CHOICES = [
    ("new",       "neu"),
    ("checked",   "geprüft"),
    ("complete",  "vollständig"),  # LK-Felder ergänzt
]


# ---------------------------------------------------------------------------
# Modelle
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    """Lehrer:innen und Admins. SuS haben KEIN Konto."""
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
    """Eine Schüler-Anmeldung gemäß BBZ-Aufnahmebogen 2026/27."""

    # -- System / Metadaten --------------------------------------------------
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    status = db.Column(db.String(20), default="new", nullable=False)

    # Fluent-Forms-Submission-ID (für Dubletten-Erkennung beim Sync).
    # Bleibt NULL, wenn die Anmeldung manuell im Tool erfasst wurde.
    external_id = db.Column(db.String(50), unique=True, nullable=True)
    synced_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # -- Sektion 1: Klassendaten (LK) ----------------------------------------
    klasse = db.Column(db.String(50), nullable=True)
    klassenlehrer = db.Column(db.String(150), nullable=True)
    aufnahmedatum = db.Column(db.Date, nullable=True)        # Beginn der Ausbildung
    eintrittsdatum = db.Column(db.Date, nullable=True)       # in unsere Schule
    hauptlistennummer = db.Column(db.String(50), nullable=True)

    # Nachteilsausgleich (Freitext, LK)
    nachteilsausgleich = db.Column(db.Text, nullable=True)

    # -- Sektion 2: Schülerdaten (SuS) ---------------------------------------
    nachname = db.Column(db.String(150), nullable=True)
    vorname = db.Column(db.String(150), nullable=True)
    geburtsname = db.Column(db.String(150), nullable=True)
    geburtsdatum = db.Column(db.Date, nullable=True)
    geschlecht = db.Column(db.String(20), nullable=True)     # GESCHLECHT_CHOICES
    geburtsland = db.Column(db.String(100), nullable=True)
    geburtsort = db.Column(db.String(150), nullable=True)
    staatsangehoerigkeit_1 = db.Column(db.String(100), nullable=True)
    staatsangehoerigkeit_2 = db.Column(db.String(100), nullable=True)
    muttersprache = db.Column(db.String(100), nullable=True)
    jahr_des_zuzugs = db.Column(db.String(10), nullable=True)  # String wg. "unbekannt" etc.
    daz_bedarf = db.Column(db.Boolean, nullable=True)        # Sprachniveau <C1

    # -- Sektion 3: Adress-/Kontaktdaten (SuS) -------------------------------
    wohnt_bei = db.Column(db.String(200), nullable=True)
    strasse = db.Column(db.String(200), nullable=True)
    plz = db.Column(db.String(10), nullable=True)
    ort = db.Column(db.String(150), nullable=True)
    kreis = db.Column(db.String(100), nullable=True)
    telefon = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    konfession = db.Column(db.String(20), nullable=True)     # KONFESSION_CHOICES
    foerderbedarf = db.Column(db.Boolean, nullable=True)
    foerderschwerpunkt = db.Column(db.String(150), nullable=True)
    foerderbedarf_art = db.Column(db.String(150), nullable=True)

    # PLZ-Prüfung: True = passt, False = passt nicht, None = unklar/nicht geprüft
    plz_ok = db.Column(db.Boolean, nullable=True)
    plz_checked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # -- Sektion 4: Eltern/Ansprechpartner/Hauptwohnsitz (SuS) ---------------
    eltern_nachname = db.Column(db.String(150), nullable=True)
    eltern_vorname = db.Column(db.String(150), nullable=True)
    eltern_strasse = db.Column(db.String(200), nullable=True)
    eltern_plz = db.Column(db.String(10), nullable=True)
    eltern_ort = db.Column(db.String(150), nullable=True)
    eltern_telefon = db.Column(db.String(50), nullable=True)
    eltern_telefax = db.Column(db.String(50), nullable=True)
    eltern_ist_vater = db.Column(db.Boolean, nullable=True)
    eltern_ist_mutter = db.Column(db.Boolean, nullable=True)
    eltern_ist_ansprechpartner = db.Column(db.Boolean, nullable=True)
    eltern_hauptwohnsitz = db.Column(db.Boolean, nullable=True)
    bundesland_kuerzel = db.Column(db.String(10), nullable=True)  # z.B. "SH", "HH"

    # -- Sektion 5: Ausbildungsverhältnis (SuS, nur duale Ausbildung) --------
    betrieb_name = db.Column(db.String(200), nullable=True)
    betrieb_kammer = db.Column(db.String(10), nullable=True)  # KAMMER_CHOICES
    ausbildung_von = db.Column(db.Date, nullable=True)
    ausbildung_bis = db.Column(db.Date, nullable=True)
    betrieb_kreis = db.Column(db.String(100), nullable=True)
    betrieb_strasse = db.Column(db.String(200), nullable=True)
    betrieb_plz = db.Column(db.String(10), nullable=True)
    betrieb_ort = db.Column(db.String(150), nullable=True)
    betrieb_telefon = db.Column(db.String(50), nullable=True)
    betrieb_fax = db.Column(db.String(50), nullable=True)
    betrieb_email = db.Column(db.String(200), nullable=True)
    beruf = db.Column(db.String(200), nullable=True)
    fachrichtung = db.Column(db.String(200), nullable=True)
    praktikant = db.Column(db.Boolean, nullable=True)
    umschueler = db.Column(db.Boolean, nullable=True)
    umschulungsvertrag_vorhanden = db.Column(db.Boolean, nullable=True)
    kostenuebernahme_vorhanden = db.Column(db.Boolean, nullable=True)

    # -- Sektion 6: Bisheriger schulischer Werdegang (SuS) -------------------
    letzte_schule_kurzform = db.Column(db.String(10), nullable=True)  # LETZTE_SCHULE_CHOICES
    jahr_verlassen = db.Column(db.String(10), nullable=True)
    klassenstufe = db.Column(db.String(20), nullable=True)
    mit_abschluss_beendet = db.Column(db.Boolean, nullable=True)
    art_abschluss_letzte_schule = db.Column(db.String(10), nullable=True)  # VB01-VB04
    allgemeinbildender_abschluss = db.Column(db.String(10), nullable=True)  # Tabelle 2
    lrs = db.Column(db.Boolean, nullable=True)  # Lese-Rechtschreib-Schwäche

    # -- Sektion 7: Schulische Abschlüsse am BBZ (LK) ------------------------
    foerderzentrum = db.Column(db.String(200), nullable=True)  # nur wenn Förderbedarf
    esa_5_jahre_englisch = db.Column(db.Boolean, nullable=True)
    esa_englisch_ausreichend = db.Column(db.Boolean, nullable=True)
    zeugnis_geprueft_am = db.Column(db.Date, nullable=True)
    bos_fos_beruf = db.Column(db.String(200), nullable=True)
    zweite_fremdsprache = db.Column(db.Boolean, nullable=True)
    qualifizierungsnachweise_am = db.Column(db.Date, nullable=True)

    # -- Interne LK-Notizen --------------------------------------------------
    notizen = db.Column(db.Text, nullable=True)

    # -- Auffangbecken für unbekannte Fluent-Forms-Felder --------------------
    # Wenn das WP-Formular ein Feld liefert, das nicht im Schema steht
    # (z.B. weil später in Fluent Forms ein neues Feld hinzugefügt wurde),
    # landet es hier als JSON-Dictionary. So geht nichts verloren.
    extra_data = db.Column(db.Text, nullable=True)  # JSON-serialisiert

    # ------------------------------------------------------------------------

    @property
    def vollstaendiger_name(self) -> str:
        teile = [self.vorname, self.nachname]
        return " ".join(t for t in teile if t) or "(ohne Namen)"

    def __repr__(self) -> str:
        return f"<Registration {self.id}: {self.vollstaendiger_name}>"


class PlzRule(db.Model):
    """Aktiv genau eine Regel. Tabelle erlaubt aber Historie."""
    id = db.Column(db.Integer, primary_key=True)
    reference_plz = db.Column(db.String(10), nullable=False, default="24768")
    allowed_kreis = db.Column(db.String(200), nullable=True)
    allowed_bezirk = db.Column(db.String(200), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))
