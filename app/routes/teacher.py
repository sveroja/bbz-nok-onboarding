"""Teacher-Bereich: Anmeldungen ansehen, prüfen, löschen, exportieren, syncen."""
import csv
import io
import re
from collections import defaultdict
from datetime import date, datetime

from flask import (
    Blueprint, current_app, render_template, redirect, request, session,
    url_for, flash, send_file,
)
from flask_login import login_required, current_user

from .. import exports
from ..extensions import db, limiter
from ..models import Abteilung, Bildungsgang, Registration, Klasse, KlasseBildungsgang
from ..decorators import role_required
from ..forms import ActionForm, KlasseForm, RegistrationLKForm
from ..fluentform import sync_submissions, delete_remote_submission

bp = Blueprint("teacher", __name__, url_prefix="/teacher")

SESSION_KLASSE_KEY = "aktive_klasse_id"  # None/fehlt = noch nicht gewaehlt, 0 = "alle"


def _ist_unterklasse(klasse) -> bool:
    """Nur Klassen mit Buchstaben-Suffix (z.B. "ausbau26a") sind ein
    waehlbarer Zug - eine unaufgeteilte Basis-Klasse ("ausbau26") ist noch
    kein Zug, sondern erst der Container fuer die spaeter angelegten
    Unterklassen.
    """
    return klasse.name[-1:].isalpha()


def _beruf_to_klassen_map(klassen):
    """{Bildungsgang: [Klasse, ...]} - fuer die Zug-Auswahl je Anmeldung."""
    mapping = defaultdict(list)
    for k in klassen:
        for kb in k.bildungsgaenge:
            mapping[kb.bildungsgang].append(k)
    return mapping


def _zug_vorschlaege(regs, beruf_to_klassen, klassen):
    """{Registration.id: Klasse.id} - Vorschlag fuer die Zug-Vorauswahl, wenn
    die LK vor Ort laut Aufnahmebogen (zug_bool/zug_value) schon einen Zug
    (a-d) vergeben hat. Nur ein Vorschlag fuers Dropdown, setzt reg.zug_id
    nicht - die tatsaechliche Zuordnung bleibt eine manuelle LK-Aktion.
    Match ueber die dokumentierte Namenskonvention "...a"/"...b"/... (siehe
    README, Abschnitt Klassen/Zuege verwalten).
    """
    vorschlaege = {}
    for r in regs:
        if r.zug_id or not r.zug_bool or not r.zug_value:
            continue
        passende_klassen = beruf_to_klassen.get(r.beruf) or klassen
        for k in passende_klassen:
            if k.name.lower().endswith(r.zug_value.strip().lower()):
                vorschlaege[r.id] = k.id
                break
    return vorschlaege


def _find_duplicate_ids():
    """IDs aller Anmeldungen, die mit mind. einer anderen in Vorname+
    Nachname+Geburtsdatum uebereinstimmen (Verdacht: SuS hat das
    WP-Formular versehentlich zweimal separat ausgefuellt - hat jeweils
    eine eigene external_id, wird von der normalen Dublettenerkennung
    beim Sync nicht erfasst). Rein informativ, loescht/blockiert nichts.
    """
    key_to_ids = defaultdict(list)
    rows = Registration.query.with_entities(
        Registration.id, Registration.vorname, Registration.nachname,
        Registration.geburtsdatum,
    ).all()
    for reg_id, vorname, nachname, geburtsdatum in rows:
        if vorname and nachname and geburtsdatum:
            key = (vorname.strip().lower(), nachname.strip().lower(), geburtsdatum)
            key_to_ids[key].append(reg_id)

    dup_ids = set()
    for ids in key_to_ids.values():
        if len(ids) > 1:
            dup_ids.update(ids)
    return dup_ids


def _current_filtered_regs():
    """Anmeldungen nach demselben Filter wie die aktuelle Uebersicht:
    aktiver Bereich (Session) + optionaler Zug-Filter. Wird von der
    Uebersicht UND allen Export-Routen genutzt, damit ein Export immer
    exakt das exportiert, was gerade sichtbar ist.

    `request.values` statt `request.args`, damit die Export-Formulare den
    Zug-Filter auch per POST mitschicken koennen. Zusaetzlich: wenn
    `reg_ids` uebergeben werden (Zeilen-Auswahl per Checkbox in der
    Uebersicht), wird die Ergebnismenge darauf eingeschraenkt - nie ueber
    den Klasse/Zug-Filter hinaus.
    """
    zug_filter = request.values.get("zug_id", type=int)
    aktive_klasse_id = session.get(SESSION_KLASSE_KEY) or None
    aktive_klasse = db.session.get(Klasse, aktive_klasse_id) if aktive_klasse_id else None

    query = Registration.query.order_by(Registration.created_at.desc())
    if aktive_klasse is not None:
        bildungsgaenge = {kb.bildungsgang for kb in aktive_klasse.bildungsgaenge}
        query = query.filter(Registration.beruf.in_(bildungsgaenge))
    if zug_filter:
        query = query.filter(Registration.zug_id == zug_filter)

    reg_ids = request.values.getlist("reg_ids", type=int)
    if reg_ids:
        query = query.filter(Registration.id.in_(reg_ids))
    return query.all(), aktive_klasse, zug_filter


def _klassen_suffix(aktive_klasse, zug_filter):
    """'_ELI026a' fuer Export-Dateinamen (leer, wenn keine Klasse im Kontext)."""
    k = _gemeinsame_klasse(aktive_klasse, zug_filter)
    if not k:
        return ""
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", k.name).strip("-")
    return f"_{safe}" if safe else ""


def _gemeinsame_klasse(aktive_klasse, zug_filter):
    """Klasse, deren "gemeinsame Daten" (Klassenlehrer, erster/letzter
    Schultag) fuer die aktuelle Ansicht gelten: der gefilterte Zug, sonst
    der gewaehlte Bereich. Bei mehrzuegigen Bildungsgaengen hat jeder Zug
    eigene Daten - daher zuerst der Zug-Filter.
    """
    if zug_filter:
        k = db.session.get(Klasse, zug_filter)
        if k is not None:
            return k
    return aktive_klasse


@bp.route("/")
@login_required
@role_required("teacher", "admin")
def dashboard():
    return render_template("teacher_dashboard.html")


@bp.route("/bereich", methods=["GET", "POST"])
@login_required
@role_required("teacher", "admin")
def bereich():
    """Auswahlseite: LK waehlt eine Klasse (filtert die Anmeldungen auf deren
    Bildungsgaenge) oder "alle anzeigen". Bleibt sticky in der Session, bis
    hier erneut wird gewechselt wird.
    """
    if request.method == "POST":
        klasse_id = request.form.get("klasse_id", type=int)
        session[SESSION_KLASSE_KEY] = klasse_id or 0
        return redirect(url_for("teacher.registrations"))

    klassen = Klasse.query.order_by(Klasse.name).all()
    return render_template("teacher_bereich.html", klassen=klassen)


@bp.route("/registrations")
@login_required
@role_required("teacher", "admin")
def registrations():
    # Teacher muss erst einen Bereich waehlen; Admin sieht per Default alles.
    if current_user.role == "teacher" and SESSION_KLASSE_KEY not in session:
        return redirect(url_for("teacher.bereich"))

    regs, aktive_klasse, zug_filter = _current_filtered_regs()
    klassen = [k for k in Klasse.query.order_by(Klasse.name).all() if _ist_unterklasse(k)]
    beruf_to_klassen = _beruf_to_klassen_map(klassen)
    duplicate_ids = _find_duplicate_ids()
    beruf_namen = {b.code: b.name for b in Bildungsgang.query.all() if b.code}
    zug_vorschlaege = _zug_vorschlaege(regs, beruf_to_klassen, klassen)

    # Wie lange existiert das Original noch bei Fluent Forms? (Frist aus der
    # .env, da nicht per API abrufbar.) Nur fuer synchronisierte Anmeldungen.
    retention = current_app.config.get("FLUENTFORM_RETENTION_DAYS", 0)
    wp_rest_tage = {}
    if retention:
        heute = date.today()
        for r in regs:
            if r.external_id and r.created_at:
                wp_rest_tage[r.id] = retention - (heute - r.created_at.date()).days

    # ActionForm einmal für CSRF-Token in jedem Zeilen-Button
    action_form = ActionForm()
    return render_template(
        "teacher_registrations.html",
        regs=regs,
        action_form=action_form,
        klassen=klassen,
        beruf_to_klassen=beruf_to_klassen,
        beruf_namen=beruf_namen,
        zug_vorschlaege=zug_vorschlaege,
        zug_filter=zug_filter,
        aktive_klasse=aktive_klasse,
        gemeinsame_klasse=_gemeinsame_klasse(aktive_klasse, zug_filter),
        duplicate_ids=duplicate_ids,
        wp_rest_tage=wp_rest_tage,
        heute=date.today().isoformat(),
    )


@bp.route("/registrations/<int:reg_id>/zug", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def assign_zug(reg_id):
    form = ActionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage (CSRF).", "error")
        return redirect(url_for("teacher.registrations"))

    reg = db.session.get(Registration, reg_id)
    if reg is None:
        flash("Datensatz nicht gefunden.", "error")
        return redirect(url_for("teacher.registrations"))

    zug_id = request.form.get("zug_id", type=int)
    if zug_id:
        klasse = db.session.get(Klasse, zug_id)
        if klasse is None:
            flash("Klasse nicht gefunden.", "error")
            return redirect(url_for("teacher.registrations"))
        reg.zug_id = klasse.id
        flash(f"Zug '{klasse.name}' zugeordnet.", "success")
    else:
        reg.zug_id = None
        flash("Zug-Zuordnung entfernt.", "success")

    db.session.commit()
    return redirect(url_for("teacher.registrations"))


@bp.route("/registrations/<int:reg_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("teacher", "admin")
def edit_registration(reg_id):
    """Klassendaten (Sektion 1) + DaZ-Sprachniveau - stehen nicht/nicht
    vollstaendig im Aufnahmebogen, werden von der LK hier nachgepflegt.
    """
    reg = db.session.get(Registration, reg_id)
    if reg is None:
        flash("Datensatz nicht gefunden.", "error")
        return redirect(url_for("teacher.registrations"))

    form = RegistrationLKForm(
        obj=reg, zeugnis_geprueft=reg.zeugnis_geprueft_am is not None
    )
    if form.validate_on_submit():
        reg.hauptlistennummer = form.hauptlistennummer.data or None
        reg.aufnahmedatum = form.aufnahmedatum.data
        reg.eintrittsdatum = form.eintrittsdatum.data
        reg.sprachniveau = form.sprachniveau.data or None
        reg.sprachniveau_nachweis = form.sprachniveau_nachweis.data
        # "Zeugnis geprüft"-Haken -> Datum auf heute setzen bzw. loeschen.
        if form.zeugnis_geprueft.data:
            if reg.zeugnis_geprueft_am is None:
                reg.zeugnis_geprueft_am = date.today()
        else:
            reg.zeugnis_geprueft_am = None
        db.session.commit()
        flash("Klassendaten gespeichert.", "success")
        return redirect(url_for("teacher.registrations"))

    return render_template("teacher_registration_edit.html", form=form, reg=reg)


@bp.route("/registrations/<int:reg_id>/check", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def mark_checked(reg_id):
    form = ActionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage (CSRF).", "error")
        return redirect(url_for("teacher.registrations"))

    reg = db.session.get(Registration, reg_id)
    if reg is None:
        flash("Datensatz nicht gefunden.", "error")
        return redirect(url_for("teacher.registrations"))

    reg.status = "checked"
    db.session.commit()
    flash("Als geprüft markiert.", "success")
    return redirect(url_for("teacher.registrations"))


@bp.route("/registrations/<int:reg_id>/delete", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def delete(reg_id):
    """Loescht den Datensatz unwiderruflich - bei manuell erfassten
    Anmeldungen nur lokal, bei synchronisierten (external_id vorhanden)
    zusaetzlich die Original-Submission bei Fluent Forms (WordPress).
    Schlaegt die WP-Loeschung fehl, bleibt der lokale Datensatz erhalten
    (kein inkonsistenter Zwischenzustand), Fehler wird angezeigt.
    """
    form = ActionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage (CSRF).", "error")
        return redirect(url_for("teacher.registrations"))

    reg = db.session.get(Registration, reg_id)
    if reg is None:
        flash("Datensatz nicht gefunden.", "error")
        return redirect(url_for("teacher.registrations"))

    if reg.external_id:
        try:
            delete_remote_submission(reg.external_id)
        except RuntimeError as exc:
            flash(f"Löschen nicht möglich: {exc}", "error")
            return redirect(url_for("teacher.registrations"))
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Löschen fehlgeschlagen für Submission %s", reg.external_id
            )
            flash(
                "Löschen fehlgeschlagen (siehe Server-Log). "
                "Datensatz wurde NICHT gelöscht.", "error",
            )
            return redirect(url_for("teacher.registrations"))

    db.session.delete(reg)
    db.session.commit()
    flash("Datensatz wurde gelöscht.", "success")
    return redirect(url_for("teacher.registrations"))


@bp.route("/klassen", methods=["GET", "POST"])
@login_required
@role_required("teacher", "admin")
def klassen():
    form = KlasseForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        if Klasse.query.filter_by(name=name).first():
            flash(f"Klasse '{name}' existiert bereits.", "error")
        else:
            klasse = Klasse(
                name=name,
                zustaendige_lehrkraft=(form.zustaendige_lehrkraft.data or "").strip() or None,
            )
            db.session.add(klasse)
            db.session.flush()  # klasse.id fuer die Verknuepfungen
            for bildungsgang in form.bildungsgaenge.data:
                db.session.add(KlasseBildungsgang(
                    klasse_id=klasse.id, bildungsgang=bildungsgang
                ))
            db.session.commit()
            flash(f"Klasse '{name}' angelegt.", "success")
            return redirect(url_for("teacher.klassen"))

    alle_klassen = Klasse.query.order_by(Klasse.name).all()

    # Bildungsgang-Checkboxen im Formular nach Abteilung gruppieren, damit man
    # sich bei mittlerweile ~70 Berufen nicht mehr durch eine flache Liste
    # suchen muss. Gruppierung ueber den Code (= Wert der Checkbox/choices),
    # nicht den Namen - Abgleich mit subfield.data im Template braucht den Code.
    abteilungen = Abteilung.query.order_by(Abteilung.name).all()
    gruppen = [
        (a.name, [b.code for b in sorted(a.bildungsgang, key=lambda b: b.name) if b.code])
        for a in abteilungen
    ]
    ohne_abteilung = [
        b.code for b in Bildungsgang.query.filter_by(abteilung_id=None)
                                            .order_by(Bildungsgang.name).all()
        if b.code
    ]

    return render_template(
        "teacher_klassen.html", form=form, klassen=alle_klassen,
        bildungsgang_gruppen=gruppen, bildungsgang_ohne_abteilung=ohne_abteilung,
    )


@bp.route("/klassen/<int:klasse_id>/gemeinsame-daten", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def update_klasse(klasse_id):
    """Gemeinsame Daten einer Klasse/eines Zugs: Klassenlehrer/in
    (= "Klassenlehrer/in" im Stammdatenblatt) und Eintrittsdatum (= erster
    Schultag). Gepflegt im Block "Gemeinsame Daten" der Anmeldungsuebersicht.
    """
    form = ActionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage (CSRF).", "error")
        return redirect(url_for("teacher.registrations"))

    klasse = db.session.get(Klasse, klasse_id)
    if klasse is None:
        flash("Klasse nicht gefunden.", "error")
        return redirect(url_for("teacher.registrations"))

    klasse.zustaendige_lehrkraft = (
        request.form.get("zustaendige_lehrkraft", "").strip() or None
    )
    raw = request.form.get("eintrittsdatum", "").strip()
    if not raw:
        klasse.eintrittsdatum = None
    else:
        try:
            klasse.eintrittsdatum = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Ungültiges Datum beim Eintrittsdatum.", "error")
            return redirect(url_for("teacher.registrations"))

    db.session.commit()
    flash(f"Gemeinsame Daten für '{klasse.name}' gespeichert.", "success")
    return redirect(url_for("teacher.registrations"))


@bp.route("/klassen/<int:klasse_id>/delete", methods=["POST"])
@login_required
@role_required("teacher", "admin")
def delete_klasse(klasse_id):
    form = ActionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage (CSRF).", "error")
        return redirect(url_for("teacher.klassen"))

    klasse = db.session.get(Klasse, klasse_id)
    if klasse is None:
        flash("Klasse nicht gefunden.", "error")
        return redirect(url_for("teacher.klassen"))

    db.session.delete(klasse)
    db.session.commit()
    flash(f"Klasse '{klasse.name}' gelöscht.", "success")
    return redirect(url_for("teacher.klassen"))


@bp.route("/export", methods=["GET", "POST"])
@login_required
@role_required("teacher", "admin")
def export():
    regs, _aktive_klasse, _zug_filter = _current_filtered_regs()
    beruf_namen = {b.code: b.name for b in Bildungsgang.query.all() if b.code}

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "id", "erstellt_am", "vorname", "nachname", "beruf", "zug",
        "geburtsdatum", "strasse", "plz", "ort", "plz_ok", "status",
    ])
    for r in regs:
        plz_ok_str = {True: "ja", False: "nein", None: "unklar"}[r.plz_ok]
        writer.writerow([
            r.id,
            r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            r.vorname,
            r.nachname,
            beruf_namen.get(r.beruf, r.beruf),
            r.zug.name if r.zug else "",
            r.geburtsdatum.isoformat() if r.geburtsdatum else "",
            r.strasse,
            r.plz,
            r.ort,
            plz_ok_str,
            r.status,
        ])

    # utf-8-sig damit Excel die Umlaute korrekt erkennt
    data = output.getvalue().encode("utf-8-sig")
    return send_file(
        io.BytesIO(data),
        as_attachment=True,
        download_name="anmeldungen.csv",
        mimetype="text/csv; charset=utf-8",
    )


@bp.route("/export/klassen-lk", methods=["GET", "POST"])
@login_required
@role_required("teacher", "admin")
def export_klassen_lk():
    regs, aktive_klasse, zug_filter = _current_filtered_regs()
    buf = exports.build_klassen_lk_excel(regs)
    name = f"anmeldungen_klassen-lk{_klassen_suffix(aktive_klasse, zug_filter)}.xlsx"
    return send_file(
        buf, as_attachment=True, download_name=name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/export/klassenbuch", methods=["GET", "POST"])
@login_required
@role_required("teacher", "admin")
def export_klassenbuch():
    regs, aktive_klasse, zug_filter = _current_filtered_regs()
    gem_klasse = _gemeinsame_klasse(aktive_klasse, zug_filter)

    # Erster Schultag = Eintrittsdatum aus den "Gemeinsamen Daten" der Klasse
    # (bzw. des gefilterten Zugs); ein mitgeschickter Wert (Override) sticht.
    # Der letzte Schultag steht pro SuS an der Anmeldung.
    raw = request.values.get("eintrittsdatum", "").strip()
    if raw:
        try:
            erster_schultag = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            erster_schultag = None
    else:
        erster_schultag = getattr(gem_klasse, "eintrittsdatum", None)

    if not erster_schultag:
        flash(
            "Bitte zuerst unter 'Gemeinsame Daten' das Eintrittsdatum "
            "(erster Schultag) der Klasse eintragen.", "error",
        )
        return redirect(url_for("teacher.registrations"))

    try:
        buf = exports.build_klassenbuch_excel(regs, erster_schultag)
    except FileNotFoundError as exc:
        flash(f"{exc} Siehe Admin → Export-Vorlagen.", "error")
        return redirect(url_for("teacher.registrations"))

    name = f"webuntis{_klassen_suffix(aktive_klasse, zug_filter)}.xlsx"
    return send_file(
        buf, as_attachment=True, download_name=name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/export/daz", methods=["GET", "POST"])
@login_required
@role_required("teacher", "admin")
def export_daz():
    regs, aktive_klasse, zug_filter = _current_filtered_regs()
    try:
        buf = exports.build_daz_excel(regs)
    except FileNotFoundError as exc:
        flash(f"{exc} Siehe Admin → Export-Vorlagen.", "error")
        return redirect(url_for("teacher.registrations"))

    name = f"daz_statistik{_klassen_suffix(aktive_klasse, zug_filter)}.xlsx"
    return send_file(
        buf, as_attachment=True, download_name=name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/export/stammdatenblatt", methods=["GET", "POST"])
@login_required
@role_required("teacher", "admin")
def export_stammdatenblatt():
    regs, _aktive_klasse, _zug_filter = _current_filtered_regs()
    try:
        buf = exports.build_stammdatenblatt_pdf(regs)
    except (FileNotFoundError, ValueError) as exc:
        flash(f"{exc} Siehe Admin → Export-Vorlagen.", "error")
        return redirect(url_for("teacher.registrations"))

    return send_file(
        buf, as_attachment=True, download_name="stammdatenblaetter.pdf",
        mimetype="application/pdf",
    )


@bp.route("/export/namensschilder", methods=["GET", "POST"])
@login_required
@role_required("teacher", "admin")
def export_namensschilder():
    regs, _aktive_klasse, _zug_filter = _current_filtered_regs()
    if not regs:
        flash("Keine Anmeldungen für den Namensschild-Export.", "error")
        return redirect(url_for("teacher.registrations"))

    buf = exports.build_namensschilder_pdf(regs)
    return send_file(
        buf, as_attachment=True, download_name="namensschilder.pdf",
        mimetype="application/pdf",
    )


@bp.route("/sync", methods=["POST"])
@login_required
@role_required("teacher", "admin")
@limiter.limit("6 per minute")
def sync():
    """Manueller Sync-Trigger aus dem UI."""
    form = ActionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage (CSRF).", "error")
        return redirect(url_for("teacher.registrations"))

    try:
        result = sync_submissions()
    except RuntimeError as exc:
        # Konfiguration fehlt o.ä. - klare Meldung an LK
        flash(f"Sync nicht möglich: {exc}", "error")
        return redirect(url_for("teacher.registrations"))
    except Exception:
        # Netzwerk/API-Fehler - generische Meldung, Details ins Log
        import logging
        logging.getLogger(__name__).exception("Sync fehlgeschlagen")
        flash("Sync fehlgeschlagen. Details siehe Server-Log.", "error")
        return redirect(url_for("teacher.registrations"))

    msg_parts = []
    if result["created"]:
        msg_parts.append(f"{result['created']} neu")
    if result["skipped"]:
        msg_parts.append(f"{result['skipped']} schon vorhanden")
    if result["errors"]:
        msg_parts.append(f"{result['errors']} Fehler")
    if not msg_parts:
        msg_parts.append("nichts Neues")

    flash("Sync: " + ", ".join(msg_parts) + ".",
          "warning" if result["errors"] else "success")
    return redirect(url_for("teacher.registrations"))
