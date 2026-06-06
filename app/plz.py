"""OpenPLZ-Anbindung.

Isoliert in einem eigenen Modul, damit es einfach getestet und
ggf. später durch eine andere Datenquelle ersetzt werden kann.
"""
import logging
from typing import Optional

import requests
from flask import current_app

logger = logging.getLogger(__name__)

OPENPLZ_URL = "https://openplzapi.org/de/Localities"


def _fetch_locality(plz: str, timeout: int) -> Optional[dict]:
    """Holt den ersten Treffer für eine PLZ. Gibt None bei Fehlern zurück."""
    try:
        resp = requests.get(
            OPENPLZ_URL,
            params={"postalCode": plz},
            headers={"accept": "application/json"},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        logger.warning("OpenPLZ Netzwerkfehler für PLZ %s: %s", plz, exc)
        return None

    if resp.status_code != 200:
        logger.warning("OpenPLZ HTTP %s für PLZ %s", resp.status_code, plz)
        return None

    try:
        payload = resp.json()
    except ValueError:
        logger.warning("OpenPLZ: keine valide JSON-Antwort für %s", plz)
        return None

    # API liefert je nach Version Liste oder {"data": [...]}
    if isinstance(payload, dict) and "data" in payload:
        items = payload["data"]
    elif isinstance(payload, list):
        items = payload
    else:
        items = [payload]

    return items[0] if items else None


def check_plz_against_rule(plz: str, rule) -> Optional[bool]:
    """Prüft, ob `plz` zur PLZ-Regel passt.

    Rückgabe:
        True  - PLZ passt zur Regel
        False - PLZ passt NICHT
        None  - konnte nicht geprüft werden (Netzwerk/API-Problem) → manuell prüfen!

    Logik:
        1. Wenn rule.allowed_kreis gesetzt: muss exakt matchen.
        2. Wenn rule.allowed_bezirk gesetzt: muss exakt matchen.
        3. Sonst: gleicher Kreis wie reference_plz (Bezirk optional).
    """
    if rule is None:
        logger.warning("PLZ-Check ohne aktive Regel.")
        return None

    timeout = current_app.config.get("OPENPLZ_TIMEOUT", 5)

    data_plz = _fetch_locality(plz, timeout)
    data_ref = _fetch_locality(rule.reference_plz, timeout)

    if not data_plz or not data_ref:
        # API nicht erreichbar oder PLZ unbekannt – ehrlich "unklar" zurückgeben
        return None

    kreis_plz = (data_plz.get("district") or {}).get("name")
    kreis_ref = (data_ref.get("district") or {}).get("name")
    bezirk_plz = (data_plz.get("governmentRegion") or {}).get("name")
    bezirk_ref = (data_ref.get("governmentRegion") or {}).get("name")

    logger.debug(
        "PLZ-Check: %s (Kreis=%s, Bezirk=%s) vs Ref %s (Kreis=%s, Bezirk=%s)",
        plz, kreis_plz, bezirk_plz,
        rule.reference_plz, kreis_ref, bezirk_ref,
    )

    # 1) Explizit erlaubter Kreis
    if rule.allowed_kreis:
        return kreis_plz == rule.allowed_kreis

    # 2) Explizit erlaubter Bezirk
    if rule.allowed_bezirk:
        return bezirk_plz == rule.allowed_bezirk

    # 3) Standard: gleicher Kreis wie Referenz
    if kreis_plz != kreis_ref:
        return False

    # Falls beide einen Bezirk haben (z.B. nicht in SH), muss der auch passen
    if bezirk_plz and bezirk_ref and bezirk_plz != bezirk_ref:
        return False

    return True
