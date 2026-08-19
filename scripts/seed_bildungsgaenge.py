"""Einmaliges Befuellen der Abteilung/Bildungsgang-Tabellen mit den echten
Daten von https://www.bbz-nok.de/bildungsangebote/berufsfelder/.

Ausfuehren im Container:
    docker compose exec app env PYTHONPATH=/app python scripts/seed_bildungsgaenge.py

Idempotent: legt Abteilungen/Bildungsgaenge nur an, wenn sie noch nicht
existieren (per Name). Die 6 bereits gegen Fluent Forms verifizierten
Bildungsgang-Bezeichnungen bleiben unveraendert (siehe Kommentare unten) -
NICHT durch die kuerzere Webseiten-Formulierung ersetzen.
"""
from app import create_app
from app.extensions import db
from app.models import Abteilung, Bildungsgang

DATEN = {
    "Elektrotechnik": [
        "Elektroniker/Elektronikerin für Energie- und Gebäudetechnik",  # verifiziert (Fluent Forms)
        "Elektroniker/-in Gebäudesystemintegration",
        "Industrieelektriker/-in",
        "Elektroniker/Elektronikerin für Betriebstechnik",  # verifiziert (Fluent Forms)
        "Fachinformatiker/Fachinformatikerin",  # verifiziert (Fluent Forms)
        "IT-Systemelektroniker/IT-Systemelektronikerin",  # verifiziert (Fluent Forms)
        "IT-Systemkaufmann/frau",
        "Informatikkaufmann/frau",
        "Informationselektroniker/Informationselektronikerin",  # verifiziert (Fluent Forms)
        "Elektriker/Elektrikerin Fachrichtung Betriebstechnik",  # verifiziert (Fluent Forms)
    ],
    "Hochbau": [
        "Maurer/in",
        "Zimmerer/in",
        "Hochbaufacharbeiter/in",
        "Ausbaufacharbeiter/in",
        "Tischler/in",
        "Beton- und Stahlbetonbauer/in",
        "Holzmechaniker/in",
        "Holz- und Bautenschützer/in",
        "Staatlich geprüfte/r Techniker/in der Fachrichtung Bautechnik (Schwerpunkt Tiefbau)",
    ],
    "Tiefbau": [
        "Bautechnische/r Konstrukteur/in",
        "Straßenbauer/in",
        "Kanalbauer/in",
        "Tiefbaufacharbeiter/in",
        "Straßenwärter/in",
    ],
    "Landmaschinen-, Anlagen- & Klimatechnik": [
        "Klempner/in",
        "Anlagenmechaniker/in – Sanitär-, Heizungs- und Klimatechnik",
        "Land- und Baumaschinenmechatroniker",
        "Mechatroniker/in für Kältetechnik",
        "Technische/r Systemplaner/in – Versorgungs- und Ausrüstungstechnik (VAT)",
        "Technische/r Systemplaner/in – Elektrotechnische Systeme (ETS)",
    ],
    "Landwirtschaft und Hauswirtschaft": [
        "Landwirt/in",
        "Fachkraft Agrarservice",
        "Fachschule für Landwirtschaft",
        "Fischwirt/in",
        "Ländl.-hauswirtschaftl. Betriebsleiter/in",
        "Wirtschafter/in der ländl. Hauswirtschaft",
        "Staatlich geprüfte/r Wirtschafter/in des Landbaus",
        "Staatlich geprüfte/r Wirtschafter/in des Landbaus Schwerpunkt ökologischer Landbau",
        "Staatlich geprüfte/r Agrarbetriebswirt/in",
        "Fachoberschule Agrar",
        "Staatlich geprüfte/r Wirtschafter/in der ländlichen Hauswirtschaft",
        "Staatliche geprüfte/r ländliche-hauswirtschaftliche/r Betriebsleiter/in",
    ],
    "Metalltechnik": [
        "Industriemechaniker/in",
        "Konstruktionsmechaniker",
        "Werkzeugmechaniker/in",
        "Zerspanungsmechaniker",
        "Kraftfahrzeugmechatroniker Fachrichtung PKW",
        "Kraftfahrzeugmechatroniker Fachrichtung NFZ",
        "Karosserie- und Fahrzeugbaumechaniker mit der Fachrichtung Karosserie- und Fahrzeugbautechnik",
        "Karosserie- und Fahrzeugbaumechaniker mit der Fachrichtung Karosserieinstandhaltungstechnik",
        "Kraftfahrzeugmechatroniker mit dem Schwerpunkt Karosserietechnik",
        "Metallbauer in der Fachrichtung Nutzfahrzeugbau",
        "Karosserie- und Fahrzeugbaumechaniker mit der Fachrichtung Caravan- und Reisemobiltechnik",
    ],
    "Nahrung, Gestaltung, Körperpflege": [
        "Bäcker/in",
        "Fachverkäufer/in – Nahrungsmittelhandwerk (Bäckerei/Konditorei)",
        "Fleischer/in",
        "Fachverkäufer/in im Nahrungsmittelhandwerk (Fleischerei)",
        "Maler/in und Lackierer/in Fachrichtung Gestaltung und Instandhaltung",
        "Maler/in und Lackierer/in Fachrichtung Ausbautechnik und Oberflächengestaltung",
        "Maler/in und Lackierer/in Fachrichtung Bauten- und Korrosionsschutz",
        "Maler/in und Lackierer/in Fachrichtung Energieeffizienz und Gestaltungstechnik",
        "Friseur/in",
        "Raumausstatter/in",
        "Reitsportsattler/in",
        "KFZ-Sattler/in",
        "Polsterer/Polsterin",
        "Polster- & Dekorationsnäher/in",
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

            for beruf in berufe:
                bildungsgang = Bildungsgang.query.filter_by(name=beruf).first()
                if bildungsgang is None:
                    db.session.add(Bildungsgang(name=beruf, abteilung_id=abteilung.id))
                    print(f"  Bildungsgang angelegt: {beruf}")
                elif bildungsgang.abteilung_id is None:
                    bildungsgang.abteilung_id = abteilung.id
                    print(f"  Bildungsgang '{beruf}' -> Abteilung '{abteilung_name}' nachgetragen")

        db.session.commit()
        print("Fertig.")


if __name__ == "__main__":
    seed()
