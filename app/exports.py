"""Export-Generierung: Klassen-LK-Excel, Klassenbuch-Import, DaZ-Import,
Stammdatenblatt-PDF. Nutzt die admin-hochgeladenen Vorlagen aus vorlagen.py.
"""
import io
from datetime import date
from typing import Optional

import openpyxl
from openpyxl.styles import Font
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from . import vorlagen
from .stammdatenblatt_layout import (
    CHECKBOX_FIELDS, PAGE_HEIGHT, PAGE_WIDTH, TEXT_FIELDS,
)

PLZ_OK_LABEL = {True: "ja", False: "nein", None: "unklar"}

GESCHLECHT_KURZFORM = {
    "maennlich": "m",
    "weiblich": "w",
    "divers": "d",
    "keine_angabe": "",
}


def _autosize_columns(ws):
    for col_cells in ws.columns:
        length = max((len(str(c.value)) for c in col_cells if c.value is not None), default=8)
        ws.column_dimensions[col_cells[0].column_letter].width = min(length + 2, 40)


# ---------------------------------------------------------------------------
# Excel fuer die Klassen-LK (wichtigste Daten, kein externes Zielformat)
# ---------------------------------------------------------------------------

def build_klassen_lk_excel(regs) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Anmeldungen"

    headers = [
        "Nachname", "Vorname", "Geburtsdatum", "Beruf", "Zug",
        "Straße", "PLZ", "Ort", "Telefon", "E-Mail",
        "Eltern/Ansprechpartner", "Eltern-Telefon",
        "Status", "PLZ-Prüfung", "Eingegangen am",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for r in regs:
        ws.append([
            r.nachname, r.vorname,
            r.geburtsdatum.strftime("%d.%m.%Y") if r.geburtsdatum else None,
            r.beruf, r.zug.name if r.zug else None,
            r.strasse, r.plz, r.ort, r.telefon, r.email,
            f"{r.eltern_vorname or ''} {r.eltern_nachname or ''}".strip() or None,
            r.eltern_telefon,
            r.status, PLZ_OK_LABEL[r.plz_ok],
            r.created_at.strftime("%d.%m.%Y %H:%M") if r.created_at else None,
        ])

    _autosize_columns(ws)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Klassenbuch-Import (schreibt in die admin-hochgeladene Vorlage)
# ---------------------------------------------------------------------------

def build_klassenbuch_excel(regs, letzter_schultag: Optional[date]) -> io.BytesIO:
    """Wirft FileNotFoundError, wenn keine Vorlage hochgeladen wurde."""
    path = vorlagen.vorlage_path("klassenbuch")
    if not path.exists():
        raise FileNotFoundError("Klassenbuch-Vorlage wurde noch nicht hochgeladen.")

    wb = openpyxl.load_workbook(path)
    ws = wb["Schüler"]

    row = 2  # Zeile 1 = Kopfzeile der Vorlage
    for r in regs:
        ws.cell(row=row, column=1, value=r.nachname)
        ws.cell(row=row, column=2, value=r.vorname)
        ws.cell(row=row, column=3, value=r.zug.name if r.zug else None)
        ws.cell(row=row, column=4, value=r.geburtsdatum)
        ws.cell(row=row, column=5, value=GESCHLECHT_KURZFORM.get(r.geschlecht, ""))
        ws.cell(row=row, column=6, value=r.eintrittsdatum)
        ws.cell(row=row, column=7, value=letzter_schultag)
        ws.cell(row=row, column=8, value=r.email)
        row += 1

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# DaZ-Import (schreibt in die admin-hochgeladene Vorlage, nur daz_bedarf=True)
# ---------------------------------------------------------------------------

def build_daz_excel(regs, abteilung: str, schuljahr: str) -> io.BytesIO:
    """Wirft FileNotFoundError, wenn keine Vorlage hochgeladen wurde."""
    path = vorlagen.vorlage_path("daz")
    if not path.exists():
        raise FileNotFoundError("DaZ-Vorlage wurde noch nicht hochgeladen.")

    wb = openpyxl.load_workbook(path)
    ws = wb["Tabelle1"]

    ws["B1"] = abteilung
    ws["B4"] = schuljahr

    row = 13  # Zeile 12 = Kopfzeile der Vorlage
    for r in regs:
        if not r.daz_bedarf:
            continue
        ws.cell(row=row, column=1, value=r.zug.name if r.zug else None)
        ws.cell(row=row, column=2, value=f"{r.nachname or ''}, {r.vorname or ''}".strip(", "))
        ws.cell(row=row, column=3, value=r.ort)
        # Sprachniveau: Spalte D (mit Nachweis) oder E (ohne Nachweis), je
        # nachdem was die LK im Tool eingetragen hat. Fehlt beides, bleibt
        # die Zeile dort leer - zum manuellen Nachtragen.
        if r.sprachniveau:
            col = 4 if r.sprachniveau_nachweis else 5
            ws.cell(row=row, column=col, value=r.sprachniveau)
        row += 1

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Stammdatenblatt-PDF (Koordinaten-Overlay auf die admin-hochgeladene Vorlage)
# ---------------------------------------------------------------------------

def _fmt_date(d) -> Optional[str]:
    return d.strftime("%d.%m.%Y") if d else None


def _combine(*parts) -> Optional[str]:
    joined = " ".join(p for p in parts if p)
    return joined or None


def _field_values(r) -> dict:
    return {
        "hauptlistennummer": r.hauptlistennummer,
        "aufnahmedatum": _fmt_date(r.aufnahmedatum),
        "zug_name": r.zug.name if r.zug else None,
        "zug_lehrkraft": r.zug.zustaendige_lehrkraft if r.zug else None,
        "eintrittsdatum": _fmt_date(r.eintrittsdatum),
        "nachname": r.nachname,
        "geburtsland": r.geburtsland,
        "vorname": r.vorname,
        "geburtsort": r.geburtsort,
        "geburtsname": r.geburtsname,
        "staatsangehoerigkeit_1": r.staatsangehoerigkeit_1,
        "staatsangehoerigkeit_2": r.staatsangehoerigkeit_2,
        "geburtsdatum": _fmt_date(r.geburtsdatum),
        "muttersprache": r.muttersprache,
        "jahr_des_zuzugs": r.jahr_des_zuzugs,
        "wohnt_bei": r.wohnt_bei,
        "strasse": r.strasse,
        "foerderbedarf_art": r.foerderbedarf_art,
        "plz_ort": _combine(r.plz, r.ort),
        "kreis": r.kreis,
        "telefon": r.telefon,
        "email": r.email,
        "eltern_nachname": r.eltern_nachname,
        "eltern_vorname": r.eltern_vorname,
        "eltern_strasse": r.eltern_strasse,
        "eltern_plz_ort": _combine(r.eltern_plz, r.eltern_ort),
        "eltern_telefon": r.eltern_telefon,
        "eltern_telefax": r.eltern_telefax,
        "bundesland_kuerzel": r.bundesland_kuerzel,
        "betrieb_name": r.betrieb_name,
        "ausbildung_von": _fmt_date(r.ausbildung_von),
        "ausbildung_bis": _fmt_date(r.ausbildung_bis),
        "betrieb_kreis": r.betrieb_kreis,
        "betrieb_plz_ort": _combine(r.betrieb_plz, r.betrieb_ort),
        "betrieb_strasse": r.betrieb_strasse,
        "betrieb_telefon": r.betrieb_telefon,
        "betrieb_fax": r.betrieb_fax,
        "betrieb_email": r.betrieb_email,
        "beruf": r.beruf,
        "fachrichtung": r.fachrichtung,
        "letzte_schule_kurzform": r.letzte_schule_kurzform,
        "jahr_verlassen": r.jahr_verlassen,
        "klassenstufe": r.klassenstufe,
        "allgemeinbildender_abschluss": r.allgemeinbildender_abschluss,
        "foerderzentrum": r.foerderzentrum,
        "zeugnis_geprueft_am": _fmt_date(r.zeugnis_geprueft_am),
        "bos_fos_beruf": r.bos_fos_beruf,
        "qualifizierungsnachweise_am": _fmt_date(r.qualifizierungsnachweise_am),
        # Rohwerte fuer Checkbox-Vergleich:
        "geschlecht": r.geschlecht,
        "daz_bedarf": r.daz_bedarf,
        "konfession": r.konfession,
        "foerderbedarf": r.foerderbedarf,
        "eltern_ist_vater": r.eltern_ist_vater,
        "eltern_ist_mutter": r.eltern_ist_mutter,
        "eltern_ist_ansprechpartner": r.eltern_ist_ansprechpartner,
        "eltern_hauptwohnsitz": r.eltern_hauptwohnsitz,
        "betrieb_kammer": r.betrieb_kammer,
        "praktikant": r.praktikant,
        "umschueler": r.umschueler,
        "umschulungsvertrag_vorhanden": r.umschulungsvertrag_vorhanden,
        "kostenuebernahme_vorhanden": r.kostenuebernahme_vorhanden,
        "mit_abschluss_beendet": r.mit_abschluss_beendet,
        "art_abschluss_letzte_schule": r.art_abschluss_letzte_schule,
        "lrs": r.lrs,
        "esa_5_jahre_englisch": r.esa_5_jahre_englisch,
        "esa_englisch_ausreichend": r.esa_englisch_ausreichend,
        "zweite_fremdsprache": r.zweite_fremdsprache,
    }


def _build_overlay(r) -> io.BytesIO:
    """Erzeugt ein 2-seitiges PDF nur mit dem Text-/Kreuzchen-Overlay fuer
    eine Registrierung, spaeter per merge_page auf die Vorlage gelegt.
    """
    values = _field_values(r)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

    for seite in (1, 2):
        for field_page, x, y, attr, fontsize in TEXT_FIELDS:
            if field_page != seite:
                continue
            value = values.get(attr)
            if value:
                c.setFont("Helvetica", fontsize)
                c.drawString(x, PAGE_HEIGHT - y + 1.5, str(value))
        for field_page, x, y, attr, expected in CHECKBOX_FIELDS:
            if field_page != seite:
                continue
            if values.get(attr) == expected:
                c.setFont("Helvetica-Bold", 9)
                c.drawString(x, PAGE_HEIGHT - y + 1.5, "X")
        c.showPage()

    c.save()
    buf.seek(0)
    return buf


def build_stammdatenblatt_pdf(regs) -> io.BytesIO:
    """Wirft FileNotFoundError, wenn keine Vorlage hochgeladen wurde.
    Ein PDF mit 2 Seiten je Registrierung, in der Reihenfolge von `regs`.
    """
    path = vorlagen.vorlage_path("stammdatenblatt")
    if not path.exists():
        raise FileNotFoundError("Stammdatenblatt-Vorlage wurde noch nicht hochgeladen.")

    if len(PdfReader(str(path)).pages) < 2:
        raise ValueError("Stammdatenblatt-Vorlage hat weniger als 2 Seiten.")

    writer = PdfWriter()
    for r in regs:
        # Frischer Reader je Registrierung: pypdf haelt beim wiederholten
        # append() desselben Reader-Objekts intern dieselben geklonten
        # PageObjects vor, wodurch sich die Overlays mehrerer SuS auf
        # denselben Seiten summiert haetten statt getrennt zu bleiben.
        reader = PdfReader(str(path))
        writer.append(reader)
        idx = len(writer.pages) - 2
        overlay = PdfReader(_build_overlay(r))
        writer.pages[idx].merge_page(overlay.pages[0])
        writer.pages[idx + 1].merge_page(overlay.pages[1])

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf
