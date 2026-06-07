"""Fluent-Forms-Anbindung: Submissions vom WordPress holen und in die DB schreiben.

Dieses Modul stellt die Verbindung zum WP-Server her, holt neue Submissions
über die Fluent-Forms-REST-API und mappt sie auf das Registration-Modell.

Aufbau:
  - APIClient:        kapselt HTTP-Aufrufe zur Fluent-Forms-API (Basic Auth)
  - FIELD_MAPPING:    welches WP-Feld landet in welcher DB-Spalte
  - parse_*:          Hilfsfunktionen zum Konvertieren der Roh-Werte
  - sync_submissions: Hauptfunktion, die alles zusammenführt

Konfiguration (aus app.config / .env):
  FLUENTFORM_BASE_URL    z.B. https://schule.example.de
  FLUENTFORM_FORM_ID     numerische Form-ID (z.B. "9")
  FLUENTFORM_USERNAME    API-Username (aus FF Settings → Developer)
  FLUENTFORM_PASSWORD    API-Passwort
"""
import json
import logging
from datetime import date, datetime, timezone
from typing import Optional

import requests
from flask import current_app

from .extensions import db
from .models import Registration, PlzRule
from .plz import check_plz_against_rule

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapping: WP-Feldname  →  Registration-Spaltenname
# ---------------------------------------------------------------------------
# Wenn ihr im Fluent-Forms-Formular Felder umbenennt, müssen hier die Keys
# entsprechend angepasst werden. Werte sind die Spaltennamen aus models.py.
#
# Spezial-Behandlung:
#   - "names" wird separat geparst (verschachtelt: first_name + last_name)
#   - Date-Felder werden über DATE_FIELDS deklariert
#   - Boolean-Felder über BOOL_FIELDS

FIELD_MAPPING = {
    # Sektion 2 - Schülerdaten
    "geburtsname":             "geburtsname",
    "geburtsdatum":            "geburtsdatum",
    "geschlecht":              "geschlecht",
    "geburtsland":             "geburtsland",
    "geburtsort":              "geburtsort",
    "staatsangehoerigkeit_1":  "staatsangehoerigkeit_1",
    "staatsangehoerigkeit_2":  "staatsangehoerigkeit_2",
    "muttersprache":           "muttersprache",
    "jahr_des_zuzugs":         "jahr_des_zuzugs",
    "daz_bedarf":              "daz_bedarf",

    # Sektion 3 - Adresse/Kontakt
    "wohnt_bei":               "wohnt_bei",
    "strasse":                 "strasse",
    "plz":                     "plz",
    "ort":                     "ort",
    "kreis":                   "kreis",
    "telefon":                 "telefon",
    "email":                   "email",
    "konfession":              "konfession",
    "foerderbedarf":           "foerderbedarf",
    "foerderschwerpunkt":      "foerderschwerpunkt",
    "foerderbedarf_art":       "foerderbedarf_art",

    # Sektion 4 - Eltern/Ansprechpartner
    "eltern_nachname":             "eltern_nachname",
    "eltern_vorname":              "eltern_vorname",
    "eltern_strasse":              "eltern_strasse",
    "eltern_plz":                  "eltern_plz",
    "eltern_ort":                  "eltern_ort",
    "eltern_telefon":              "eltern_telefon",
    "eltern_telefax":              "eltern_telefax",
    "eltern_ist_vater":            "eltern_ist_vater",
    "eltern_ist_mutter":           "eltern_ist_mutter",
    "eltern_ist_ansprechpartner":  "eltern_ist_ansprechpartner",
    "eltern_hauptwohnsitz":        "eltern_hauptwohnsitz",
    "bundesland_kuerzel":          "bundesland_kuerzel",

    # Sektion 5 - Ausbildungsverhältnis
    "betrieb_name":                  "betrieb_name",
    "betrieb_kammer":                "betrieb_kammer",
    "ausbildung_von":                "ausbildung_von",
    "ausbildung_bis":                "ausbildung_bis",
    "betrieb_kreis":                 "betrieb_kreis",
    "betrieb_strasse":               "betrieb_strasse",
    "betrieb_plz":                   "betrieb_plz",
    "betrieb_ort":                   "betrieb_ort",
    "betrieb_telefon":               "betrieb_telefon",
    "betrieb_fax":                   "betrieb_fax",
    "betrieb_email":                 "betrieb_email",
    "beruf":                         "beruf",
    "fachrichtung":                  "fachrichtung",
    "praktikant":                    "praktikant",
    "umschueler":                    "umschueler",
    "umschulungsvertrag_vorhanden":  "umschulungsvertrag_vorhanden",
    "kostenuebernahme_vorhanden":    "kostenuebernahme_vorhanden",

    # Sektion 6 - Werdegang
    "letzte_schule_kurzform":       "letzte_schule_kurzform",
    "jahr_verlassen":               "jahr_verlassen",
    "klassenstufe":                 "klassenstufe",
    "mit_abschluss_beendet":        "mit_abschluss_beendet",
    "art_abschluss_letzte_schule":  "art_abschluss_letzte_schule",
    "allgemeinbildender_abschluss": "allgemeinbildender_abschluss",
    "lrs":                          "lrs",
}

# Felder, die als Datum (dd.mm.YYYY) geparst werden müssen
DATE_FIELDS = {
    "geburtsdatum", "ausbildung_von", "ausbildung_bis",
}

# Felder, die als ja/nein-String reinkommen und zu Boolean werden
BOOL_FIELDS = {
    "daz_bedarf", "foerderbedarf",
    "eltern_ist_vater", "eltern_ist_mutter",
    "eltern_ist_ansprechpartner", "eltern_hauptwohnsitz",
    "praktikant", "umschueler",
    "umschulungsvertrag_vorhanden", "kostenuebernahme_vorhanden",
    "mit_abschluss_beendet", "lrs",
}

# Felder, die wir aus den WP-Daten ignorieren (WP-internes Zeug)
IGNORED_PREFIXES = ("_fluent", "_wp", "__")


# ---------------------------------------------------------------------------
# Wert-Parser
# ---------------------------------------------------------------------------

def parse_date(value: str) -> Optional[date]:
    """Wandelt '26.06.2026' in date(2026, 6, 26). Leer → None."""
    if not value or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%d.%m.%Y").date()
    except ValueError:
        logger.warning("Konnte Datum nicht parsen: %r", value)
        return None


def parse_bool(value: str) -> Optional[bool]:
    """Mappt 'ja'/'nein' auf True/False. Leer → None (= keine Angabe)."""
    if value is None:
        return None
    v = str(value).strip().lower()
    if v == "":
        return None
    if v in ("ja", "yes", "true", "1"):
        return True
    if v in ("nein", "no", "false", "0"):
        return False
    logger.warning("Unbekannter Boolean-Wert: %r", value)
    return None


def parse_str(value) -> Optional[str]:
    """Leere Strings werden zu None, sonst getrimmt."""
    if value is None:
        return None
    v = str(value).strip()
    return v if v else None


# ---------------------------------------------------------------------------
# Mapping einer Submission auf ein Registration-Objekt
# ---------------------------------------------------------------------------

def submission_to_registration(submission: dict) -> Registration:
    """Wandelt eine Fluent-Forms-Submission in ein (noch nicht gespeichertes)
    Registration-Objekt um.

    `submission` ist ein Item aus dem `data`-Array der API-Antwort.
    Die eigentlichen Feldwerte stecken im JSON-String `submission["response"]`.
    """
    # response-Feld ist ein JSON-String, der die eigentlichen Form-Daten enthält
    response_raw = submission.get("response")
    if isinstance(response_raw, str):
        try:
            data = json.loads(response_raw)
        except json.JSONDecodeError:
            logger.exception("Konnte response-JSON nicht parsen für Submission %s",
                             submission.get("id"))
            data = {}
    elif isinstance(response_raw, dict):
        # Falls die API in einer anderen Version doch ein Objekt liefert
        data = response_raw
    else:
        data = {}

    reg = Registration()

    # Stamm-Metadaten
    reg.external_id = str(submission.get("id") or "")
    reg.synced_at = datetime.now(timezone.utc)

    # Spezialfall 1: "names" ist verschachtelt {first_name, last_name}
    names = data.get("names") or {}
    if isinstance(names, dict):
        reg.vorname = parse_str(names.get("first_name"))
        reg.nachname = parse_str(names.get("last_name"))

    # Reguläres Feld-Mapping
    unmapped = {}
    for wp_field, value in data.items():
        # WP-Interna überspringen
        if wp_field.startswith(IGNORED_PREFIXES):
            continue
        # Bereits behandelt
        if wp_field == "names":
            continue

        if wp_field not in FIELD_MAPPING:
            unmapped[wp_field] = value
            continue

        db_field = FIELD_MAPPING[wp_field]

        if db_field in DATE_FIELDS:
            parsed = parse_date(value)
        elif db_field in BOOL_FIELDS:
            parsed = parse_bool(value)
        else:
            parsed = parse_str(value)

        setattr(reg, db_field, parsed)

    if unmapped:
        reg.extra_data = json.dumps(unmapped, ensure_ascii=False)
        logger.info("Submission %s hat %d unbekannte Felder: %s",
                    reg.external_id, len(unmapped), list(unmapped.keys()))

    return reg


# ---------------------------------------------------------------------------
# API-Client
# ---------------------------------------------------------------------------

class APIClient:
    """Minimaler Client für die Fluent-Forms-REST-API.

    Auth: Basic Auth mit dem Username/Password-Paar aus Fluent Forms →
    Settings → Developer/REST API. Diese Credentials sind nicht der
    WP-Admin-Login.
    """

    def __init__(self, base_url: str, username: str, password: str,
                 timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)
        self.timeout = timeout

    def list_submissions(self, form_id: str, per_page: int = 100,
                         page: int = 1) -> dict:
        """Holt eine Seite Submissions für ein Formular.

        Fluent-Forms-Endpunkt:
          GET /wp-json/fluentform/v1/submissions?form_id={id}&per_page=&page=

        Antwort ist eine Laravel-Style-Paginierung:
          {
            "current_page": 1,
            "data": [ {submission}, ... ],
            "last_page": 5,
            "total": 423,
            ...
          }

        Rückgabe: das geparste JSON-Dict (mit allen Pagination-Feldern).
        Aufrufer ist verantwortlich für die Paginierung (siehe sync_submissions).
        """
        url = f"{self.base_url}/wp-json/fluentform/v1/submissions"
        params = {
            "form_id": form_id,
            "per_page": per_page,
            "page": page,
        }
        resp = requests.get(url, auth=self.auth, params=params,
                            timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def sync_submissions(per_page: int = 100, max_pages: int = 100) -> dict:
    """Holt alle Submissions vom WP, importiert noch unbekannte.

    Rückgabe:
        {"fetched": int, "created": int, "skipped": int, "errors": int}

    Dubletten werden über `external_id` (= submission["id"]) erkannt.
    Pagination wird automatisch durchlaufen, bis keine weitere Seite
    mehr existiert (oder max_pages erreicht ist - Sicherheitsnetz).
    """
    cfg = current_app.config
    required = ["FLUENTFORM_BASE_URL", "FLUENTFORM_FORM_ID",
                "FLUENTFORM_USERNAME", "FLUENTFORM_PASSWORD"]
    missing = [k for k in required if not cfg.get(k)]
    if missing:
        raise RuntimeError(
            f"Fluent-Forms-Sync nicht konfiguriert. Fehlend in .env: "
            f"{', '.join(missing)}"
        )

    client = APIClient(
        base_url=cfg["FLUENTFORM_BASE_URL"],
        username=cfg["FLUENTFORM_USERNAME"],
        password=cfg["FLUENTFORM_PASSWORD"],
    )

    result = {"fetched": 0, "created": 0, "skipped": 0, "errors": 0}
    rule = PlzRule.query.filter_by(active=True).first()
    form_id = cfg["FLUENTFORM_FORM_ID"]

    page = 1
    while page <= max_pages:
        try:
            payload = client.list_submissions(form_id, per_page=per_page,
                                              page=page)
        except Exception:
            logger.exception("Sync: Fehler beim Abruf von Seite %d", page)
            result["errors"] += 1
            break

        submissions = payload.get("data") or []
        last_page = payload.get("last_page", 1)
        result["fetched"] += len(submissions)
        logger.info("Sync: Seite %d/%s, %d Submissions geholt",
                    page, last_page, len(submissions))

        for sub in submissions:
            ext_id = str(sub.get("id") or "")
            if not ext_id:
                result["errors"] += 1
                logger.warning("Submission ohne id übersprungen")
                continue

            existing = Registration.query.filter_by(external_id=ext_id).first()
            if existing:
                result["skipped"] += 1
                continue

            try:
                reg = submission_to_registration(sub)
                # PLZ-Check (best effort)
                if reg.plz and rule:
                    try:
                        reg.plz_ok = check_plz_against_rule(reg.plz, rule)
                        reg.plz_checked_at = datetime.now(timezone.utc)
                    except Exception:
                        logger.exception("PLZ-Check fehlgeschlagen für %s",
                                         ext_id)

                db.session.add(reg)
                db.session.commit()
                result["created"] += 1
            except Exception:
                db.session.rollback()
                result["errors"] += 1
                logger.exception("Fehler beim Import von Submission %s", ext_id)

        if page >= last_page:
            break
        page += 1

    logger.info(
        "Sync fertig: %d geholt, %d neu, %d übersprungen, %d Fehler.",
        result["fetched"], result["created"], result["skipped"], result["errors"]
    )
    return result
