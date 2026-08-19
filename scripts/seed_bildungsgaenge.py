"""Einmaliges Befuellen der Abteilung/Bildungsgang-Tabellen mit den echten
Daten von https://www.bbz-nok.de/bildungsangebote/berufsfelder/.

Ausfuehren im Container:
    docker compose exec app env PYTHONPATH=/app python scripts/seed_bildungsgaenge.py

Idempotent: legt Abteilungen/Bildungsgaenge nur an, wenn sie noch nicht
existieren (per Code). `code` muss exakt dem VALUE des "Beruf"-Dropdowns in
Fluent Forms entsprechen (Label dort = `name`).
"""
from app import create_app
from app.extensions import db
from app.models import Abteilung, Bildungsgang

# (Name, Code) je Abteilung. Code = Value im Fluent-Forms-Dropdown.
DATEN = {
    "Elektrotechnik": [
        ("Elektroniker/-in – Fachrichtung Energie- und Gebäudetechnik", "elektroniker_energie_gebaeudetechnik"),
        ("Elektroniker/-in – Fachrichtung Gebäudesystemintegration", "elektroniker_gebaeudesystemintegration"),
        ("Industrieelektriker/-in", "industrieelektriker"),
        ("Elektroniker/-in für Betriebstechnik", "elektroniker_betriebstechnik"),
        ("Fachinformatiker/-in", "fachinformatiker"),
        ("IT-System-Elektroniker/-in", "it_system_elektroniker"),
        ("Kaufmann/-frau für IT-System-Management", "kaufmann_it_system_management"),
        ("Kaufmann/-frau für Digitalisierungsmanagement", "kaufmann_digitalisierungsmanagement"),
        ("Informationselektroniker/-in", "informationselektroniker"),
    ],
    "Hochbau": [
        ("Maurer/-in", "maurer"),
        ("Zimmerer/-in", "zimmerer"),
        ("Hochbaufacharbeiter/-in", "hochbaufacharbeiter"),
        ("Ausbaufacharbeiter/-in", "ausbaufacharbeiter"),
        ("Tischler/-in", "tischler"),
        ("Beton- und Stahlbetonbauer/-in", "beton_stahlbetonbauer"),
        ("Holzmechaniker/-in", "holzmechaniker"),
        ("Holz- und Bautenschützer/-in", "holz_bautenschuetzer"),
    ],
    "Tiefbau": [
        ("Bautechnischer Konstrukteur/Bautechnische Konstrukteurin – Fachrichtung Tief-, Verkehrswege- und Landschaftsbau", "bautechnischer_konstrukteur"),
        ("Straßenbauer/-in", "strassenbauer"),
        ("Kanalbauer/-in", "kanalbauer"),
        ("Tiefbaufacharbeiter/-in", "tiefbaufacharbeiter"),
        ("Straßenwärter/-in", "strassenwaerter"),
    ],
    "Landmaschinen-, Anlagen- & Klimatechnik": [
        ("Klempner/-in", "klempner"),
        ("Anlagenmechaniker/-in für Sanitär-, Heizungs- und Klimatechnik", "anlagenmechaniker_shk"),
        ("Land- und Baumaschinenmechatroniker/-in", "land_baumaschinenmechatroniker"),
        ("Mechatroniker/-in für Kältetechnik", "mechatroniker_kaeltetechnik"),
        ("Technischer Systemplaner/Technische Systemplanerin – Fachrichtung Versorgungs- und Ausrüstungstechnik (VAT)", "techn_systemplaner_vat"),
        ("Technischer Systemplaner/Technische Systemplanerin – Fachrichtung Elektrotechnische Systeme (ETS)", "techn_systemplaner_ets"),
    ],
    "Landwirtschaft und Hauswirtschaft": [
        ("Landwirt/-in", "landwirt"),
        ("Fachkraft Agrarservice", "fachkraft_agrarservice"),
        ("Fachschule für Landwirtschaft", "fachschule_landwirtschaft"),
        ("Fischwirt/-in", "fischwirt"),
        ("Fachoberschule Agrar", "fachoberschule_agrar"),
        ("Ländl.-hauswirtschaftl. Betriebsleiter/-in", "laendl_hauswirtschaftl_betriebsleiter"),
        ("Wirtschafter/-in der ländl. Hauswirtschaft", "wirtschafter_laendl_hauswirtschaft"),
        ("Staatlich geprüfte/r Wirtschafter/-in des Landbaus", "staatl_gepr_wirtschafter_landbau"),
        ("Staatlich geprüfte/r Wirtschafter/-in des Landbaus, Schwerpunkt ökologischer Landbau", "staatl_gepr_wirtschafter_landbau_oekolog"),
        ("Staatlich geprüfte/r Agrarbetriebswirt/-in", "staatl_gepr_agrarbetriebswirt"),
        ("Staatlich geprüfte/r Wirtschafter/-in der ländlichen Hauswirtschaft", "staatl_gepr_wirtschafter_laendl_hauswirtschaft"),
    ],
    "Metalltechnik": [
        ("Industriemechaniker/-in", "industriemechaniker"),
        ("Konstruktionsmechaniker/-in", "konstruktionsmechaniker"),
        ("Werkzeugmechaniker/-in", "werkzeugmechaniker"),
        ("Zerspanungsmechaniker/-in", "zerspanungsmechaniker"),
        ("Kraftfahrzeugmechatroniker/-in – Schwerpunkt Personenkraftwagentechnik", "kfz_mechatroniker_pkw"),
        ("Kraftfahrzeugmechatroniker/-in – Schwerpunkt Nutzfahrzeugtechnik", "kfz_mechatroniker_nfz"),
        ("Kraftfahrzeugmechatroniker/-in – Schwerpunkt Karosserietechnik", "kfz_mechatroniker_karosserietechnik"),
        ("Karosserie- und Fahrzeugbaumechaniker/-in – Fachrichtung Karosserie- und Fahrzeugbautechnik", "karosserie_fahrzeugbaumechaniker_bautechnik"),
        ("Karosserie- und Fahrzeugbaumechaniker/-in – Fachrichtung Karosserieinstandhaltungstechnik", "karosserie_fahrzeugbaumechaniker_instandhaltung"),
        ("Karosserie- und Fahrzeugbaumechaniker/-in – Fachrichtung Caravan- und Reisemobiltechnik", "karosserie_fahrzeugbaumechaniker_caravan"),
        ("Metallbauer/-in – Fachrichtung Nutzfahrzeugbau", "metallbauer_nutzfahrzeugbau"),
    ],
    "Nahrung, Gestaltung, Körperpflege": [
        ("Bäcker/-in", "baecker"),
        ("Fachverkäufer/-in im Lebensmittelhandwerk – Schwerpunkte Bäckerei, Konditorei", "fachverkaeufer_lebensmittelhandwerk_baeckerei_konditorei"),
        ("Fachverkäufer/-in im Lebensmittelhandwerk – Schwerpunkt Fleischerei", "fachverkaeufer_lebensmittelhandwerk_fleischerei"),
        ("Fleischer/-in", "fleischer"),
        ("Friseur/-in", "friseur"),
        ("Maler/-in und Lackierer/-in – Fachrichtung Gestaltung und Instandhaltung", "maler_lackierer_gestaltung_instandhaltung"),
        ("Maler/-in und Lackierer/-in – Fachrichtung Bauten- und Korrosionsschutz", "maler_lackierer_bauten_korrosionsschutz"),
        ("Maler/-in und Lackierer/-in – Fachrichtung Energieeffizienz- und Gestaltungstechnik", "maler_lackierer_energieeffizienz_gestaltungstechnik"),
        ("Raumausstatter/-in", "raumausstatter"),
        ("Sattler/-in – Fachrichtung Fahrzeugsattlerei", "sattler_fahrzeugsattlerei"),
        ("Sattler/-in – Fachrichtung Reitsportsattlerei", "sattler_reitsportsattlerei"),
        ("Polsterer/-in", "polsterer"),
        ("Polster- und Dekorationsnäher/-in", "polster_dekorationsnaeher"),
    ],
}


def seed():
    app = create_app()
    with app.app_context():
        for abteilung_name, berufe in DATEN.items():
            abteilung = Abteilung.query.filter_by(name=abteilung_name).first()
            if abteilung is None:
                abteilung = Abteilung(name=abteilung_name)
                db.session.add(abteilung)
                db.session.flush()
                print(f"Abteilung angelegt: {abteilung_name}")

            for name, code in berufe:
                bildungsgang = Bildungsgang.query.filter_by(code=code).first()
                if bildungsgang is None:
                    db.session.add(Bildungsgang(name=name, code=code, abteilung_id=abteilung.id))
                    print(f"  Bildungsgang angelegt: {name} ({code})")
                else:
                    if bildungsgang.name != name:
                        bildungsgang.name = name
                    if bildungsgang.abteilung_id is None:
                        bildungsgang.abteilung_id = abteilung.id

        db.session.commit()
        print("Fertig.")


if __name__ == "__main__":
    seed()
