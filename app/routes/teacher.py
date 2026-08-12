"""Teacher-Bereich: Anmeldungen ansehen, prüfen, löschen, exportieren, syncen."""
import csv
import io
from collections import defaultdict
from datetime import datetime

from flask import (
    Blueprint, render_template, redirect, request, session, url_for, flash, send_file
)
from flask_login import login_required, current_user

from .. import exports
from ..extensions import db, limiter
from ..models import Registration, Klasse, KlasseBildungsgang
from ..decorators import role_required
from ..forms import ActionForm, KlasseForm, RegistrationLKForm
from ..fluentform import sync_submissions

bp = Blueprint("teacher", __name__, url_prefix="/teacher")

SESSION_KLASSE_KEY = "aktive_klasse_id"  # None/fehlt = noch nicht gewaehlt, 0 = "alle"


def _beruf_to_klassen_map(klassen):
    """{Bildungsgang: [Klasse, ...]} - fuer die Zug-Auswahl je Anmeldung."""
    mapping = defaultdict(list)
    for k in klassen:
        for kb in k.bildungsgaenge:
            mapping[kb.bildungsgang].append(k)
    return mapping


def _current_filtered_regs():
    """Anmeldungen nach demselben Filter wie die aktuelle Uebersicht:
    aktiver Bereich (Session) + optionaler Zug-Query-Parameter. Wird von
    der Uebersicht UND allen Export-Routen genutzt, damit ein Export immer
    exakt das exportiert, was gerade sichtbar ist.
    """
    zug_filter = request.args.get("zug_id", type=int)
    aktive_klasse_id = session.get(SESSION_KLASSE_KEY) or None
    aktive_klasse = db.session.get(Klasse, aktive_klasse_id) if aktive_klasse_id else None

    query = Registration.query.order_by(Registration.created_at.desc())
    if aktive_klasse is not None:
        bildungsgaenge = {kb.bildungsgang for kb in aktive_klasse.bildungsgaenge}
        query = query.filter(Registration.beruf.in_(bildungsgaenge))
    if zug_filter:
        query = query.filter(Registration.zug_id == zug_filter)
    return query.all(), aktive_klasse, zug_filter


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
    klassen = Klasse.query.order_by(Klasse.name).all()
    beruf_to_klassen = _beruf_to_klassen_map(klassen)

    # ActionForm einmal für CSRF-Token in jedem Zeilen-Button
    action_form = ActionForm()
    return render_template(
        "teacher_registrations.html",
        regs=regs,
        action_form=action_form,
        klassen=klassen,
        beruf_to_klassen=beruf_to_klassen,
        zug_filter=zug_filter,
        aktive_klasse=aktive_klasse,
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

    form = RegistrationLKForm(obj=reg)
    if form.validate_on_submit():
        reg.hauptlistennummer = form.hauptlistennummer.data or None
        reg.aufnahmedatum = form.aufnahmedatum.data
        reg.eintrittsdatum = form.eintrittsdatum.data
        reg.sprachniveau = form.sprachniveau.data or None
        reg.sprachniveau_nachweis = form.sprachniveau_nachweis.data
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
    form = ActionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage (CSRF).", "error")
        return redirect(url_for("teacher.registrations"))

    reg = db.session.get(Registration, reg_id)
    if reg is None:
        flash("Datensatz nicht gefunden.", "error")
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
    return render_template("teacher_klassen.html", form=form, klassen=alle_klassen)


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


@bp.route("/export")
@login_required
@role_required("teacher", "admin")
def export():
    regs, _aktive_klasse, _zug_filter = _current_filtered_regs()

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
            r.beruf,
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


@bp.route("/export/klassen-lk")
@login_required
@role_required("teacher", "admin")
def export_klassen_lk():
    regs, _aktive_klasse, _zug_filter = _current_filtered_regs()
    buf = exports.build_klassen_lk_excel(regs)
    return send_file(
        buf, as_attachment=True, download_name="anmeldungen_klassen-lk.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/export/klassenbuch")
@login_required
@role_required("teacher", "admin")
def export_klassenbuch():
    letzter_schultag_raw = request.args.get("letzter_schultag", "").strip()
    try:
        letzter_schultag = datetime.strptime(letzter_schultag_raw, "%Y-%m-%d").date()
    except ValueError:
        flash("Bitte einen gültigen 'letzter Schultag' angeben.", "error")
        return redirect(url_for("teacher.registrations"))

    regs, _aktive_klasse, _zug_filter = _current_filtered_regs()
    try:
        buf = exports.build_klassenbuch_excel(regs, letzter_schultag)
    except FileNotFoundError as exc:
        flash(f"{exc} Siehe Admin → Export-Vorlagen.", "error")
        return redirect(url_for("teacher.registrations"))

    return send_file(
        buf, as_attachment=True, download_name="klassenbuch_import.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/export/daz")
@login_required
@role_required("teacher", "admin")
def export_daz():
    abteilung = request.args.get("abteilung", "").strip()
    schuljahr = request.args.get("schuljahr", "").strip()
    if not abteilung or not schuljahr:
        flash("Bitte Abteilung und Schuljahr angeben.", "error")
        return redirect(url_for("teacher.registrations"))

    regs, _aktive_klasse, _zug_filter = _current_filtered_regs()
    try:
        buf = exports.build_daz_excel(regs, abteilung, schuljahr)
    except FileNotFoundError as exc:
        flash(f"{exc} Siehe Admin → Export-Vorlagen.", "error")
        return redirect(url_for("teacher.registrations"))

    return send_file(
        buf, as_attachment=True, download_name="daz_import.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/export/stammdatenblatt")
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
