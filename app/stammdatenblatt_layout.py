"""Koordinaten-Layout fuer das Ausfuellen des Stammdatenblatt-PDFs.

Das PDF hat keine ausfuellbaren Formularfelder (kein AcroForm) - Text wird
daher als Overlay an fest ermittelten Positionen platziert.
Seitengroesse: 595.32 x 841.92 pt (A4). Umrechnung in PDF-Koordinaten
(Ursprung unten links) beim Zeichnen: y_pdf = PAGE_HEIGHT - y.

Format je Eintrag:
  TEXT_FIELDS:      (seite, x, y, attr, fontsize)
  CHECKBOX_FIELDS:  (seite, x, y, attr, erwarteter_wert)

CHECKBOX_FIELDS-Koordinaten sind KEINE Schaetzungen mehr (Label-Ende +
Abstand), sondern per pdfplumber aus den tatsaechlich im PDF gezeichneten
Kaestchen-Rechtecken ermittelt (Mittelpunkt, mit kleinem Nudge nach unten
fuer die Basislinie). Frueher lagen mehrere Kreuze systematisch 8-35pt zu
weit links (z.B. IHK/HK/LWK landeten direkt auf dem Label-Text statt im
Kaestchen), weil "Label-Ende + fester Abstand" bei diesem Formular keine
verlaessliche Heuristik ist - die Kaestchen-Spalten sind teils deutlich
vom zugehoerigen Label abgesetzt.
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
    (1, 452, 100.4, "aufnahmedatum", FONT_SIZE),
    (1, 95, 124.2, "zug_name", 7),  # Box ist schmal ausgelegt, kleinere Schrift
    # Klassenlehrer-Box: x 238-337 (per pdfplumber). Frueher x=235 (vor dem
    # Boxanfang) + Schrift 8 -> lange Namen liefen rechts raus.
    (1, 240, 124.2, "zug_lehrkraft", 7),
    (1, 452, 125.7, "eintrittsdatum", FONT_SIZE),

    # Sektion 2 (Schuelerdaten)
    (1, 121, 184.4, "nachname", FONT_SIZE),
    (1, 410, 184.4, "geburtsland", FONT_SIZE),
    (1, 121, 209.4, "vorname", FONT_SIZE),
    (1, 410, 209.4, "geburtsort", FONT_SIZE),
    (1, 121, 234.3, "geburtsname", FONT_SIZE),
    # Wert-Zellen der 1. Staatsangeh./Muttersprache beginnen erst bei x 312.4
    # (per pdfplumber) - vorher sass der Text auf dem linken Zellenrand.
    (1, 316, 233.6, "staatsangehoerigkeit_1", FONT_SIZE),
    (1, 470, 233.6, "staatsangehoerigkeit_2", FONT_SIZE),
    (1, 121, 259.0, "geburtsdatum", FONT_SIZE),
    (1, 316, 258.5, "muttersprache", FONT_SIZE),
    (1, 475, 258.5, "jahr_des_zuzugs", FONT_SIZE),

    # Sektion 3 (Adresse/Kontakt)
    (1, 90, 341.9, "wohnt_bei", FONT_SIZE),
    (1, 98, 366.3, "strasse", FONT_SIZE),
    # Zelle rechts von "Art:" / direkt unter dem Label "Foerderschwerpunkt:"
    # (x 469-559). Zeigt den Foerderschwerpunkt, ersatzweise foerderbedarf_art.
    (1, 472, 367.0, "foerderschwerpunkt_art", 7),
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
    # jahr_verlassen/klassenstufe: Box-Koordinaten (x0) per pdfplumber
    # verifiziert - lagen vorher deutlich zu weit links (Box beginnt erst
    # bei x=288.9 bzw. x=514.5, nicht direkt hinter dem Fragetext).
    (2, 522, 447.1, "letzte_schule_kurzform", FONT_SIZE),
    (2, 293, 476.1, "jahr_verlassen", FONT_SIZE),
    (2, 519, 476.1, "klassenstufe", FONT_SIZE),
    (2, 386, 565.4, "allgemeinbildender_abschluss", FONT_SIZE),  # eigene Kurzform-Box, nicht die von letzte_schule

    # Sektion 7 (Schulabschluesse am BBZ)
    (2, 383, 650.5, "foerderzentrum", FONT_SIZE),
    (2, 352, 719.0, "zeugnis_geprueft_am", FONT_SIZE),
    (2, 367, 742.1, "bos_fos_beruf", FONT_SIZE),
    (2, 367, 789.3, "qualifizierungsnachweise_am", FONT_SIZE),
]

# (Seite, x, y, Attribut, erwarteter Wert fuer "X")
# x/y = Mittelpunkt des tatsaechlich gezeichneten Kaestchens (per pdfplumber
# aus den Rechteck-/Linien-Koordinaten der Vorlage ermittelt), y zusaetzlich
# +3 fuer die Basislinie (drawString zeichnet ab der Unterkante des "X").
CHECKBOX_FIELDS = [
    # Geschlecht
    (1, 249.8, 154.0, "geschlecht", "maennlich"),
    (1, 348.7, 154.0, "geschlecht", "weiblich"),
    (1, 434.8, 154.0, "geschlecht", "divers"),
    (1, 547.1, 154.0, "geschlecht", "keine_angabe"),
    # DaZ-Bedarf
    (1, 391.4, 281.4, "daz_bedarf", True),
    (1, 456.9, 281.4, "daz_bedarf", False),
    # Konfession (Kaestchen teilt sich die Zelle mit dem Label - eng, aber
    # per Zellgrenzen bestaetigt: ev-Zelle 403.4-423.8, rk 423.8-445.9,
    # isl 445.9-468.0)
    (1, 421, 344.9, "konfession", "ev"),
    (1, 443, 344.9, "konfession", "rk"),
    (1, 465, 344.9, "konfession", "isl"),
    # Foerderbedarf: ja-Zelle x 402.4-423.8 ("ja" endet bei 417.9), nein-Zelle
    # 423.8-445.9 ("nein" fuellt sie fast komplett). Label-Baseline y1 ~366.9
    # -> Layout-y 368.4 (drawString-Baseline = y - 1.5). Kreuz rechts direkt
    # hinter dem Label, etwas groesser (frueher zu weit links / zu hoch).
    (1, 417, 368.4, "foerderbedarf", True, 10),
    (1, 439, 368.4, "foerderbedarf", False, 9),
    # Eltern-Rollen
    (1, 547.1, 468.0, "eltern_ist_vater", True),
    (1, 547.1, 489.5, "eltern_ist_mutter", True),
    (1, 547.1, 510.7, "eltern_ist_ansprechpartner", True),
    (1, 547.1, 532.0, "eltern_hauptwohnsitz", True),
    # Kammer (IHK/HK-Kaestchen liegen NICHT direkt hinter dem Label, sondern
    # deutlich weiter rechts in einer eigenen Spalte, gleiche x wie LWK)
    (1, 457.9, 602.0, "betrieb_kammer", "IHK"),
    (1, 547.1, 602.0, "betrieb_kammer", "LWK"),
    (1, 457.9, 625.5, "betrieb_kammer", "HK"),
    # Praktikant/Umschueler
    (1, 102.4, 767.0, "praktikant", True),
    (1, 196.5, 767.0, "umschueler", True),
    (1, 348.7, 789.0, "umschulungsvertrag_vorhanden", True),
    (1, 524.6, 789.0, "kostenuebernahme_vorhanden", True),
    # Seite 2: alle Kaestchen hier sind Zellen mit dem Label darin (JA/NEIN/
    # VB0x). Koordinaten per pymupdf aus den Zell-Linien + Label-Positionen
    # ermittelt. Layout-y = Label-Baseline(y1) + 1.5, damit das X auf der
    # Textlinie sitzt (vorher lag es ~4pt zu hoch). x = rechte Luecke der
    # Zelle bzw. rechter Rand, wo das Label die Zelle fuellt.
    # Abschluss beendet: JA-Zelle x 424.8-446.9 ("JA" 431.7-439.9),
    # NEIN-Zelle 468.9-491.0 ("NEIN" 470.1-488.4). Baseline y1 504.8.
    (2, 440, 506.3, "mit_abschluss_beendet", True, 9),
    (2, 484, 506.3, "mit_abschluss_beendet", False, 8),
    # Art des Abschlusses: VB01 x 381.3-403.4, VB02 424.8-446.9,
    # VB03 468.9-491.0, VB04 514.5-536.6. Label fuellt die Zelle fast ganz.
    # Baseline y1 533.8.
    (2, 396, 535.3, "art_abschluss_letzte_schule", "VB01", 8),
    (2, 439, 535.3, "art_abschluss_letzte_schule", "VB02", 8),
    (2, 483, 535.3, "art_abschluss_letzte_schule", "VB03", 8),
    (2, 529, 535.3, "art_abschluss_letzte_schule", "VB04", 8),
    # LRS: JA-Zelle x 381.3-403.4 ("JA" 388.3-396.5), NEIN-Zelle 424.8-446.9
    # ("NEIN" 426.5-444.9). Baseline y1 594.1.
    (2, 397, 595.6, "lrs", True, 9),
    (2, 441, 595.6, "lrs", False, 8),
    # ESA-Englisch / 2. Fremdsprache (Abschnitt 7): JA-Zelle x 446.9-468.9
    # ("JA" 453.8-462.0), NEIN-Zelle 491.0-514.5 ("NEIN" 492.2-510.5).
    (2, 463, 673.9, "esa_5_jahre_englisch", True, 9),
    (2, 507, 673.9, "esa_5_jahre_englisch", False, 8),
    (2, 463, 695.3, "esa_englisch_ausreichend", True, 9),
    (2, 507, 695.3, "esa_englisch_ausreichend", False, 8),
    # 2. Fremdsprache (Baseline y1 764.1)
    (2, 463, 765.6, "zweite_fremdsprache", True, 9),
    (2, 507, 765.6, "zweite_fremdsprache", False, 8),
]
