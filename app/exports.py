"""Export-Generierung: Klassen-LK-Excel, Klassenbuch-Import, DaZ-Import,
Stammdatenblatt-PDF. Nutzt die admin-hochgeladenen Vorlagen aus vorlagen.py.
"""
import io
from datetime import date
from typing import Optional

import openpyxl
from openpyxl.styles import Alignment, Font
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from . import branding, vorlagen
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
    from .models import Bildungsgang  # lokaler Import, zirkulaer sonst

    beruf_namen = {
        b.code: b.name for b in Bildungsgang.query.all() if b.code
    }

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Anmeldungen"

    headers = [
        "Nachname", "Vorname", "Geburtsdatum", "Beruf", "Zug",
        "Straße", "PLZ", "Ort", "Telefon", "E-Mail",
        "Eltern/Ansprechpartner", "Eltern-Telefon",
        "Betrieb", "Betrieb E-Mail", "Betrieb Ort",
        "Status", "PLZ-Prüfung", "Eingegangen am",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    klasse_cache = {}
    for r in regs:
        eff_klasse = _effektive_klasse(r, klasse_cache)
        ws.append([
            r.nachname, r.vorname,
            r.geburtsdatum.strftime("%d.%m.%Y") if r.geburtsdatum else None,
            beruf_namen.get(r.beruf, r.beruf), eff_klasse.name if eff_klasse else None,
            r.strasse, r.plz, r.ort, r.telefon, r.email,
            f"{r.eltern_vorname or ''} {r.eltern_nachname or ''}".strip() or None,
            r.eltern_telefon,
            r.betrieb_name, r.betrieb_email, _combine(r.betrieb_plz, r.betrieb_ort),
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

_KB_DATE_FORMAT = "DD.MM.YYYY"
_KB_DATE_COLUMNS = (4, 6, 7)  # Geburtsdatum, erster Schultag, letzter Schultag
_KB_CENTER_COLUMNS = (3, 4, 5, 6, 7)  # Klasse, Geburtsdatum, Geschlecht, Schultage
_KB_LEFT_COLUMNS = (1, 2, 8)  # Name, Vorname, Email


def letzter_schultag(ausbildung_bis: Optional[date]) -> Optional[date]:
    """Letzter Schultag = Ende des Schulhalbjahres, in dem die Ausbildung
    endet: der naechste 31.01. bzw. 31.07. am oder nach `ausbildung_bis`.
    Ohne Ausbildungsende -> None.
    """
    if not ausbildung_bis:
        return None
    y = ausbildung_bis.year
    for kandidat in (date(y, 1, 31), date(y, 7, 31), date(y + 1, 1, 31)):
        if kandidat >= ausbildung_bis:
            return kandidat
    return date(y + 1, 7, 31)


def build_klassenbuch_excel(
    regs, erster_schultag: Optional[date],
) -> io.BytesIO:
    """Wirft FileNotFoundError, wenn keine Vorlage hochgeladen wurde.

    "erster Schultag" ist ein einheitliches Datum fuer den ganzen Export
    (aus den "Gemeinsamen Daten" der Klasse). "letzter Schultag" wird pro
    SuS aus dem Ausbildungsende (`ausbildung_bis`) berechnet - fehlt das,
    bleibt die Zelle leer.

    Die Vorlage bringt uneinheitliche Zell-Formate mit (mal dd/mm/yyyy, mal
    mm-dd-yy, lila Schrift in Zeile 2, Excel-"Tabelle" nur ueber A1:H2).
    Deshalb werden die geschriebenen Datenzeilen hier bewusst normalisiert:
    einheitliches deutsches Datumsformat, Standard-Schrift, und die
    Tabellen-Range wird auf alle Zeilen ausgedehnt (sonst greift die
    Zeilen-Streifung/Faerbung nur auf die erste Zeile).
    """
    path = vorlagen.vorlage_path("klassenbuch")
    if not path.exists():
        raise FileNotFoundError("Klassenbuch-Vorlage wurde noch nicht hochgeladen.")

    wb = openpyxl.load_workbook(path)
    ws = wb["Schüler"]

    first_data_row = 2  # Zeile 1 = Kopfzeile der Vorlage
    row = first_data_row
    klasse_cache = {}
    for r in regs:
        eff_klasse = _effektive_klasse(r, klasse_cache)
        ws.cell(row=row, column=1, value=r.nachname)
        ws.cell(row=row, column=2, value=r.vorname)
        ws.cell(row=row, column=3, value=eff_klasse.name if eff_klasse else None)
        ws.cell(row=row, column=4, value=r.geburtsdatum)
        ws.cell(row=row, column=5, value=GESCHLECHT_KURZFORM.get(r.geschlecht, ""))
        ws.cell(row=row, column=6, value=erster_schultag)
        ws.cell(row=row, column=7, value=letzter_schultag(r.ausbildung_bis))
        ws.cell(row=row, column=8, value=r.email)

        for col in range(1, 9):
            cell = ws.cell(row=row, column=col)
            cell.font = Font()  # Vorlagen-Eigenheiten (lila Schrift) entfernen
            if col in _KB_DATE_COLUMNS:
                cell.number_format = _KB_DATE_FORMAT
            # Die Vorlage setzt das Horizontal-Alignment nicht fuer jede
            # Zeile gleich (z.B. fehlt es in Zeile 3) - ohne explizites
            # Alignment faellt Excel bei Datumswerten auf rechtsbuendig
            # zurueck, was neben den sonst zentrierten Zeilen seltsam
            # aussieht. Deshalb hier fest vorgeben statt von der Vorlage
            # zu erben.
            if col in _KB_CENTER_COLUMNS:
                cell.alignment = Alignment(horizontal="center")
            elif col in _KB_LEFT_COLUMNS:
                cell.alignment = Alignment(horizontal="left")
        row += 1

    last_data_row = row - 1
    if last_data_row >= first_data_row:
        for table in ws.tables.values():
            table.ref = f"A1:H{last_data_row}"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# DaZ-Import (schreibt in die admin-hochgeladene Vorlage, nur daz_bedarf=True)
# ---------------------------------------------------------------------------

def aktuelles_schuljahr(heute: Optional[date] = None) -> str:
    """'2026/27' - Schuljahr beginnt im August. Vor August gehoert das
    aktuelle Kalenderjahr noch zum vorigen Schuljahr.
    """
    heute = heute or date.today()
    start = heute.year if heute.month >= 8 else heute.year - 1
    return f"{start}/{str(start + 1)[-2:]}"


def build_daz_excel(regs) -> io.BytesIO:
    """Wirft FileNotFoundError, wenn keine Vorlage hochgeladen wurde.

    Abteilung wird automatisch aus der admin-gepflegten Zuordnung
    Bildungsgang -> Abteilung ermittelt. Schuljahr aus dem Datum.
    """
    from .models import Bildungsgang  # lokaler Import, zirkulaer sonst

    path = vorlagen.vorlage_path("daz")
    if not path.exists():
        raise FileNotFoundError("DaZ-Vorlage wurde noch nicht hochgeladen.")

    abteilung = None
    for r in regs:
        if r.beruf:
            eintrag = Bildungsgang.query.filter_by(code=r.beruf).first()
            if eintrag and eintrag.abteilung:
                abteilung = eintrag.abteilung.name
                break

    wb = openpyxl.load_workbook(path)
    ws = wb["Tabelle1"]

    ws["B1"] = abteilung
    ws["B4"] = aktuelles_schuljahr()

    row = 13  # Zeile 12 = Kopfzeile der Vorlage
    klasse_cache = {}
    for r in regs:
        if not r.daz_bedarf:
            continue
        eff_klasse = _effektive_klasse(r, klasse_cache)
        ws.cell(row=row, column=1, value=eff_klasse.name if eff_klasse else None)
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
# Office365-Import (schreibt in die admin-hochgeladene Vorlage)
# ---------------------------------------------------------------------------

BUNDESLAND_NAMEN = {
    "BW": "Baden-Württemberg",
    "BY": "Bayern",
    "BE": "Berlin",
    "BB": "Brandenburg",
    "HB": "Bremen",
    "HH": "Hamburg",
    "HE": "Hessen",
    "MV": "Mecklenburg-Vorpommern",
    "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen",
    "RP": "Rheinland-Pfalz",
    "SL": "Saarland",
    "SN": "Sachsen",
    "ST": "Sachsen-Anhalt",
    "SH": "Schleswig-Holstein",
    "TH": "Thüringen",
}


def _bundesland_name(kuerzel: Optional[str]) -> Optional[str]:
    """Voller Bundesland-Name zum Kuerzel - unbekannte/leere Werte (z.B.
    Freitext-Tippfehler) werden unveraendert durchgereicht statt verworfen.
    """
    if not kuerzel:
        return None
    return BUNDESLAND_NAMEN.get(kuerzel.strip().upper(), kuerzel)


def build_office365_excel(regs) -> io.BytesIO:
    """Wirft FileNotFoundError, wenn keine Vorlage hochgeladen wurde.

    Spalte A (Benutzername) und D (Anzeigename) sind in der Vorlage bereits
    Formeln auf Basis von B/C - die bleiben unangetastet, hier werden nur
    die uebrigen ("gruenen") Spalten befuellt. Erste Tabellenzeile der
    Vorlage (unabhaengig vom Blattnamen) = Kopfzeile, Daten ab Zeile 2.
    """
    path = vorlagen.vorlage_path("office365")
    if not path.exists():
        raise FileNotFoundError("Office365-Vorlage wurde noch nicht hochgeladen.")

    from .models import Bildungsgang  # lokaler Import, zirkulaer sonst

    wb = openpyxl.load_workbook(path)
    ws = wb.worksheets[0]

    abteilung_cache = {}

    def _abteilung(beruf):
        if beruf not in abteilung_cache:
            eintrag = Bildungsgang.query.filter_by(code=beruf).first()
            abteilung_cache[beruf] = eintrag.abteilung.name if eintrag and eintrag.abteilung else None
        return abteilung_cache[beruf]

    row = 2  # Zeile 1 = Kopfzeile der Vorlage
    for r in regs:
        ws.cell(row=row, column=2, value=r.vorname)
        ws.cell(row=row, column=3, value=r.nachname)
        ws.cell(row=row, column=5, value="Schüler")
        ws.cell(row=row, column=6, value=_abteilung(r.beruf))
        ws.cell(row=row, column=12, value=r.strasse)
        ws.cell(row=row, column=13, value=r.ort)
        ws.cell(row=row, column=14, value=_bundesland_name(r.bundesland_kuerzel))
        ws.cell(row=row, column=15, value=r.plz)
        ws.cell(row=row, column=16, value="Deutschland")
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


def _ist_zug(klasse) -> bool:
    """Klasse mit Buchstaben-Suffix (ELI026a) = Zug, ohne (ELI026) = die
    unaufgeteilte Klasse eines einzuegigen Bildungsgangs.
    """
    return bool(klasse) and klasse.name[-1:].isalpha()


def _basis_klasse_fuer_beruf(beruf, _cache=None):
    """Die unaufgeteilte Klasse (ohne a/b/c-Suffix) eines einzuegigen
    Bildungsgangs - fuer Anmeldungen, die keinem Zug zugeordnet sind. Nur
    eindeutig, wenn genau eine solche Klasse den Bildungsgang abdeckt.
    """
    if not beruf:
        return None
    if _cache is not None and beruf in _cache:
        return _cache[beruf]
    from .models import Klasse, KlasseBildungsgang  # lokal, zirkulaer sonst
    treffer = [
        k for k in Klasse.query.join(KlasseBildungsgang)
        .filter(KlasseBildungsgang.bildungsgang == beruf).all()
        if not _ist_zug(k)
    ]
    ergebnis = treffer[0] if len(treffer) == 1 else None
    if _cache is not None:
        _cache[beruf] = ergebnis
    return ergebnis


def _effektive_klasse(r, _cache=None):
    """Zug der Anmeldung oder - wenn keiner zugeordnet - die unaufgeteilte
    Klasse des (einzuegigen) Bildungsgangs.
    """
    return r.zug or _basis_klasse_fuer_beruf(r.beruf, _cache)


def _field_values(r, eff_klasse=None) -> dict:
    return {
        "hauptlistennummer": r.hauptlistennummer,
        "aufnahmedatum": _fmt_date(r.aufnahmedatum),
        "zug_name": eff_klasse.name if eff_klasse else None,
        "zug_lehrkraft": eff_klasse.zustaendige_lehrkraft if eff_klasse else None,
        # Eintrittsdatum: primaer pro Anmeldung, sonst die "Gemeinsamen
        # Daten" der Klasse/des Zugs.
        "eintrittsdatum": _fmt_date(
            r.eintrittsdatum or (eff_klasse.eintrittsdatum if eff_klasse else None)
        ),
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
        # Zelle unter "Foerderschwerpunkt:" / rechts von "Art:" - primaer der
        # Foerderschwerpunkt, sonst die (Frei-)Angabe foerderbedarf_art.
        "foerderschwerpunkt_art": r.foerderschwerpunkt or r.foerderbedarf_art,
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


def _build_overlay(r, klasse_cache=None) -> io.BytesIO:
    """Erzeugt ein 2-seitiges PDF nur mit dem Text-/Kreuzchen-Overlay fuer
    eine Registrierung, spaeter per merge_page auf die Vorlage gelegt.
    """
    values = _field_values(r, _effektive_klasse(r, klasse_cache))
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
        for entry in CHECKBOX_FIELDS:
            field_page, x, y, attr, expected, *rest = entry
            if field_page != seite:
                continue
            if values.get(attr) == expected:
                # optionale 6. Spalte: kleinere Schrift fuer enge Kaestchen
                c.setFont("Helvetica-Bold", rest[0] if rest else 9)
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
    klasse_cache = {}
    for r in regs:
        # Frischer Reader je Registrierung: pypdf haelt beim wiederholten
        # append() desselben Reader-Objekts intern dieselben geklonten
        # PageObjects vor, wodurch sich die Overlays mehrerer SuS auf
        # denselben Seiten summiert haetten statt getrennt zu bleiben.
        reader = PdfReader(str(path))
        writer.append(reader)
        idx = len(writer.pages) - 2
        overlay = PdfReader(_build_overlay(r, klasse_cache))
        writer.pages[idx].merge_page(overlay.pages[0])
        writer.pages[idx + 1].merge_page(overlay.pages[1])

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Namensschilder / Tischkarten (A4, 1 Spalte / 4 Zeilen, 3 Faltmarken -
# Stehaufsteller mit Standfuessen oben/unten, Vorname + Nachname je auf
# einer der beiden mittleren, schraeg stehenden Flaechen)
# ---------------------------------------------------------------------------

_NS_ROWS = 4              # Zeilen = Faltmarken (3) + 1
_NS_MARGIN = 20           # Rand je Zeile (pt)
_NS_LOGO_MAX_H = 46       # max. Logo-Hoehe (pt)
_NS_NAME_START = 40       # Start-Schriftgroesse fuer den Namen
_NS_NAME_MIN = 12


def _ns_fit_size(text, max_width) -> int:
    """Groesste Helvetica-Bold-Groesse, bei der `text` in max_width passt."""
    size = _NS_NAME_START
    while size > _NS_NAME_MIN and stringWidth(text, "Helvetica-Bold", size) > max_width:
        size -= 1
    return size


def _ns_draw_row(c, y0, row_h, logo, text, rotate180):
    """Eine Inhaltszeile (volle Blattbreite, Hoehe `row_h`): Logo oben
    links, darunter der Name fett zentriert - optional um 180 Grad gedreht.

    Gedreht wird die OBERE der beiden Inhaltszeilen (Vorname): Nach dem
    Falten zum Stehaufsteller (Zeile 1 + 4 = flache Standfuesse auf dem
    Tisch, Zeile 2 + 3 = die beiden schraegen, zur Faltkante hin
    ansteigenden Flaechen) liest sich eine zur Faltkante hin ansteigende
    Flaeche nur dann richtig herum, wenn ihr Text zur Kante hin "oben" hat -
    bei Zeile 2 ist das die 180-Grad-gedrehte Richtung, bei Zeile 3 (die
    andersherum ansteigt) die normale. Je nachdem, ob die Lehrkraft die SuS
    duzt oder siezt, drehen die SuS das fertig gefaltete Schild einfach um
    180 Grad um die Hochachse - dann zeigt wahlweise Vorname oder Nachname
    nach vorn.
    """
    c.saveState()
    cx, cy = PAGE_WIDTH / 2, y0 + row_h / 2
    c.translate(cx, cy)
    if rotate180:
        c.rotate(180)
    half_w, half_h = PAGE_WIDTH / 2, row_h / 2
    margin = min(_NS_MARGIN, half_h * 0.25)
    left = -half_w + margin
    top = half_h - margin

    logo_h = 0.0
    if logo is not None:
        iw, ih = logo.getSize()
        h, w = _NS_LOGO_MAX_H, _NS_LOGO_MAX_H * iw / ih
        max_h_row = row_h * 0.4
        if h > max_h_row:
            h, w = max_h_row, max_h_row * iw / ih
        max_w = half_w * 2 * 0.35
        if w > max_w:
            w, h = max_w, max_w * ih / iw
        c.drawImage(logo, left, top - h, width=w, height=h,
                    mask="auto", preserveAspectRatio=True)
        logo_h = h + 10

    size = _ns_fit_size(text or "—", half_w * 2 - 2 * margin)
    bereich_oben = top - logo_h
    bereich_unten = -half_h + margin
    y = (bereich_oben + bereich_unten) / 2 - size * 0.35
    c.setFont("Helvetica-Bold", size)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(0, y, text or "—")
    c.restoreState()


def build_namensschilder_pdf(regs) -> io.BytesIO:
    """Ein A4-Blatt je Anmeldung, 1 Spalte / 4 Zeilen (3 Faltmarken):
    Zeile 1 und 4 bleiben leer und liegen gefaltet als Standfuesse flach
    auf dem Tisch; Zeile 2 (Vorname, 180 Grad gedreht) und Zeile 3
    (Nachname) bilden die beiden schraegen Flaechen des Aufstellers
    dazwischen. Siehe `_ns_draw_row` fuer die Falt-/Drehlogik.
    """
    row_h = PAGE_HEIGHT / _NS_ROWS
    logo = ImageReader(str(branding.logo_path())) if branding.has_logo() else None

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    for r in regs:
        vorname = (r.vorname or "").strip()
        nachname = (r.nachname or "").strip()

        # Faltmarken: gestrichelt ueber die volle Breite + Ticks an den
        # Kanten, an jeder der 3 Zeilengrenzen.
        for i in range(1, _NS_ROWS):
            y = row_h * i
            c.saveState()
            c.setStrokeColorRGB(0.6, 0.6, 0.6)
            c.setLineWidth(0.7)
            c.setDash(3, 3)
            c.line(18, y, PAGE_WIDTH - 18, y)
            c.setDash()
            c.line(0, y, 16, y)
            c.line(PAGE_WIDTH, y, PAGE_WIDTH - 16, y)
            c.setFont("Helvetica", 6)
            c.setFillColorRGB(0.55, 0.55, 0.55)
            c.drawCentredString(PAGE_WIDTH / 2, y + 3, "hier falten")
            c.restoreState()

        # Zeile 3 (Nachname, normal) und Zeile 2 (Vorname, 180 Grad).
        _ns_draw_row(c, row_h * 1, row_h, logo, nachname, rotate180=False)
        _ns_draw_row(c, row_h * 2, row_h, logo, vorname, rotate180=True)
        c.showPage()

    c.save()
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Erklaerung Umschueler (admin-hochgeladenes PDF MIT echtem AcroForm -
# Feldwerte statt Koordinaten-Overlay)
# ---------------------------------------------------------------------------

def _strasse_plz_ort(strasse, plz, ort) -> Optional[str]:
    teile = [t for t in (strasse, _combine(plz, ort)) if t]
    return ", ".join(teile) or None


def build_umschueler_erklaerung_pdf(regs) -> io.BytesIO:
    """Ein ausgefuelltes Exemplar der "Erklaerung fuer die Uebernahme der
    Beitraege fuer Umschueler/-innen" je Umschueler (r.umschueler == True)
    in `regs`. Die Vorlage hat ein echtes AcroForm (18 Felder) - daher
    Feldwerte statt Koordinaten-Overlay wie beim Stammdatenblatt.

    Nicht aus unseren Daten ableitbare Felder bleiben leer (von Hand zu
    ergaenzen): "ausscheidender Soldat"/BFD-Foerderung (Ja/Nein-Kaestchen),
    Traeger der Massnahme + dessen Anschrift, Massnahmennummer,
    Dienst-/Firmenstempel und Ort/Datum/Unterschrift.

    Wirft FileNotFoundError, wenn keine Vorlage hochgeladen wurde, und
    ValueError, wenn `regs` keine Umschueler/-innen enthaelt.
    """
    path = vorlagen.vorlage_path("umschueler_erklaerung")
    if not path.exists():
        raise FileNotFoundError(
            "Vorlage 'Erklärung Umschüler' wurde noch nicht hochgeladen."
        )

    umschueler_regs = [r for r in regs if r.umschueler]
    if not umschueler_regs:
        raise ValueError("Keine Umschüler/-innen in der Auswahl.")

    from .models import Bildungsgang  # lokaler Import, zirkulaer sonst
    beruf_namen = {b.code: b.name for b in Bildungsgang.query.all() if b.code}

    writer = PdfWriter()
    for r in umschueler_regs:
        # Frischer Reader je Registrierung (siehe Stammdatenblatt-Kommentar
        # weiter oben): sonst teilen sich mehrere Anmeldungen dieselben
        # geklonten Formularfeld-Objekte.
        reader = PdfReader(str(path))
        writer.append(reader)
        page = writer.pages[-1]

        beruf_text = beruf_namen.get(r.beruf, r.beruf)
        if r.fachrichtung:
            beruf_text = _combine(beruf_text, f"({r.fachrichtung})")

        werte = {
            "Name Vorname": _combine(r.nachname and f"{r.nachname},", r.vorname),
            "Geburtsdatum": _fmt_date(r.geburtsdatum),
            "Straße PLZ Wohnort": _strasse_plz_ort(r.strasse, r.plz, r.ort),
            "Umschulungsbetrieb": r.betrieb_name,
            "Straße PLZ Ort": _strasse_plz_ort(
                r.betrieb_strasse, r.betrieb_plz, r.betrieb_ort
            ),
            "Telefonische Erreichbarkeit über": r.betrieb_telefon,
            "Umschulungsberuf": beruf_text,
            "Datum Umschulungsbeginn": _fmt_date(r.ausbildung_von),
            "Datum Umschulungsende": _fmt_date(r.ausbildung_bis),
        }
        werte = {k: v for k, v in werte.items() if v}
        writer.update_page_form_field_values(page, werte)

    if writer.get_fields():
        writer.set_need_appearances_writer(True)

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf
