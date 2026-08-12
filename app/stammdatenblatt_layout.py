"""Koordinaten-Layout fuer das Ausfuellen des Stammdatenblatt-PDFs.

Das PDF hat keine ausfuellbaren Formularfelder (kein AcroForm) - Text wird
daher als Overlay an fest ermittelten Positionen platziert (per pdfplumber
aus dem Original extrahiert: Label-Endposition + kleiner Abstand).
Seitengroesse: 595.32 x 841.92 pt (A4). Die y-Werte sind die "bottom"-Koordinate der jeweiligen Label-Textzeile aus
pdfplumber (Abstand von der Seitenoberkante), dienen als Basislinie fuer den
neuen Text/das Kreuzchen direkt daneben. Umrechnung in PDF-Koordinaten
(Ursprung unten links) beim Zeichnen: y_pdf = PAGE_HEIGHT - y.

Format je Eintrag:
  TEXT_FIELDS:      (seite, x, y, attr, fontsize)
  CHECKBOX_FIELDS:  (seite, x, y, attr, erwarteter_wert)
"""

PAGE_WIDTH = 595.32
PAGE_HEIGHT = 841.92

FONT_SIZE = 8

# (Seite 1-2, x, y, Attribut, Schriftgroesse)
# x-Werte enthalten bereits +4pt Korrektur ggue. der Label-Endposition,
# damit der Text nicht auf dem linken Kaestchenrand aufsitzt (Runde 2 nach
# visueller Pruefung).
TEXT_FIELDS = [
    # Seite 1 - Sektion 1 (Klassendaten)
    (1, 329, 42.3, "hauptlistennummer", FONT_SIZE),
    (1, 440, 100.4, "aufnahmedatum", FONT_SIZE),
    (1, 80, 124.2, "zug_name", 7),  # Box ist schmal ausgelegt, kleinere Schrift
    (1, 235, 124.2, "zug_lehrkraft", FONT_SIZE),
    (1, 437, 125.7, "eintrittsdatum", FONT_SIZE),

    # Sektion 2 (Schuelerdaten)
    (1, 121, 184.4, "nachname", FONT_SIZE),
    (1, 410, 184.4, "geburtsland", FONT_SIZE),
    (1, 121, 209.4, "vorname", FONT_SIZE),
    (1, 410, 209.4, "geburtsort", FONT_SIZE),
    (1, 121, 234.3, "geburtsname", FONT_SIZE),
    (1, 310, 233.6, "staatsangehoerigkeit_1", FONT_SIZE),
    (1, 470, 233.6, "staatsangehoerigkeit_2", FONT_SIZE),
    (1, 121, 259.0, "geburtsdatum", FONT_SIZE),
    (1, 308, 258.5, "muttersprache", FONT_SIZE),
    (1, 475, 258.5, "jahr_des_zuzugs", FONT_SIZE),

    # Sektion 3 (Adresse/Kontakt)
    (1, 90, 341.9, "wohnt_bei", FONT_SIZE),
    (1, 98, 366.3, "strasse", FONT_SIZE),
    (1, 474, 367.6, "foerderbedarf_art", FONT_SIZE),
    (1, 98, 392.5, "plz_ort", FONT_SIZE),
    (1, 410, 392.5, "kreis", FONT_SIZE),
    (1, 98, 417.5, "telefon", FONT_SIZE),
    (1, 368, 416.8, "email", FONT_SIZE),

    # Sektion 4 (Eltern/Ansprechpartner)
    (1, 144, 470.2, "eltern_nachname", FONT_SIZE),
    (1, 144, 491.4, "eltern_vorname", FONT_SIZE),
    (1, 144, 512.7, "eltern_strasse", FONT_SIZE),
    (1, 144, 533.9, "eltern_plz_ort", FONT_SIZE),
    (1, 144, 555.1, "eltern_telefon", FONT_SIZE),
    (1, 344, 555.1, "eltern_telefax", FONT_SIZE),
    (1, 537, 555.1, "bundesland_kuerzel", 7),

    # Sektion 5 (Ausbildungsverhaeltnis)
    (1, 115, 604.8, "betrieb_name", FONT_SIZE),
    (1, 116, 641.1, "ausbildung_von", FONT_SIZE),
    (1, 266, 641.6, "ausbildung_bis", FONT_SIZE),
    (1, 427, 641.1, "betrieb_kreis", FONT_SIZE),
    (1, 121, 670.0, "betrieb_plz_ort", FONT_SIZE),
    (1, 427, 670.6, "betrieb_strasse", FONT_SIZE),
    (1, 98, 704.8, "betrieb_telefon", FONT_SIZE),
    (1, 269, 703.3, "betrieb_fax", FONT_SIZE),
    (1, 407, 703.3, "betrieb_email", FONT_SIZE),
    (1, 98, 726.8, "beruf", FONT_SIZE),
    (1, 387, 729.2, "fachrichtung", FONT_SIZE),

    # Seite 2 - Sektion 6 (Werdegang)
    (2, 522, 447.1, "letzte_schule_kurzform", FONT_SIZE),
    (2, 281, 476.1, "jahr_verlassen", FONT_SIZE),
    (2, 509, 476.1, "klassenstufe", FONT_SIZE),
    (2, 386, 565.4, "allgemeinbildender_abschluss", FONT_SIZE),  # eigene Kurzform-Box, nicht die von letzte_schule

    # Sektion 7 (Schulabschluesse am BBZ)
    (2, 383, 650.5, "foerderzentrum", FONT_SIZE),
    (2, 352, 719.0, "zeugnis_geprueft_am", FONT_SIZE),
    (2, 367, 742.1, "bos_fos_beruf", FONT_SIZE),
    (2, 367, 789.3, "qualifizierungsnachweise_am", FONT_SIZE),
]

# (Seite, x, y, Attribut, erwarteter Wert fuer "X")
# x liegt jeweils INNERHALB der jeweiligen Kaestchen-Box (Mittelpunkt), nicht
# dahinter - bei den schmalen JA/NEIN-Boxen auf Seite 2 fuehrte "Label-Ende +
# fester Abstand" in Runde 1 dazu, dass das Kreuz neben statt im Kaestchen
# landete.
CHECKBOX_FIELDS = [
    # Geschlecht
    (1, 225, 155.4, "geschlecht", "maennlich"),
    (1, 325, 155.4, "geschlecht", "weiblich"),
    (1, 410, 155.4, "geschlecht", "divers"),
    (1, 524, 155.4, "geschlecht", "keine_angabe"),
    # DaZ-Bedarf
    (1, 375, 284.7, "daz_bedarf", True),
    (1, 449, 283.5, "daz_bedarf", False),
    # Konfession
    (1, 422, 341.9, "konfession", "ev"),
    (1, 443, 341.9, "konfession", "rk"),
    (1, 466, 341.9, "konfession", "isl"),
    # Foerderbedarf
    (1, 421, 366.9, "foerderbedarf", True),
    (1, 448, 366.9, "foerderbedarf", False),
    # Eltern-Rollen
    (1, 538, 470.2, "eltern_ist_vater", True),
    (1, 538, 491.4, "eltern_ist_mutter", True),
    (1, 538, 512.7, "eltern_ist_ansprechpartner", True),
    (1, 538, 533.9, "eltern_hauptwohnsitz", True),
    # Kammer
    (1, 426, 604.8, "betrieb_kammer", "IHK"),
    (1, 512, 604.8, "betrieb_kammer", "LWK"),
    (1, 426, 616.5, "betrieb_kammer", "HK"),
    # Praktikant/Umschueler
    (1, 93, 768.8, "praktikant", True),
    (1, 187, 769.1, "umschueler", True),
    (1, 336, 790.9, "umschulungsvertrag_vorhanden", True),
    (1, 510, 790.9, "kostenuebernahme_vorhanden", True),
    # Seite 2: Abschluss beendet
    (2, 443, 504.8, "mit_abschluss_beendet", True),
    (2, 492, 504.8, "mit_abschluss_beendet", False),
    # Art des Abschlusses (VB01-VB04)
    (2, 404, 533.8, "art_abschluss_letzte_schule", "VB01"),
    (2, 447, 533.8, "art_abschluss_letzte_schule", "VB02"),
    (2, 492, 533.8, "art_abschluss_letzte_schule", "VB03"),
    (2, 537, 533.8, "art_abschluss_letzte_schule", "VB04"),
    # LRS
    (2, 400, 594.1, "lrs", True),
    (2, 449, 594.1, "lrs", False),
    # ESA-Englisch
    (2, 466, 672.4, "esa_5_jahre_englisch", True),
    (2, 514, 672.4, "esa_5_jahre_englisch", False),
    (2, 466, 693.8, "esa_englisch_ausreichend", True),
    (2, 514, 693.8, "esa_englisch_ausreichend", False),
    # 2. Fremdsprache
    (2, 466, 764.1, "zweite_fremdsprache", True),
    (2, 514, 764.1, "zweite_fremdsprache", False),
]
