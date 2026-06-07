"""Teacher-Bereich: Anmeldungen ansehen, prüfen, löschen, exportieren, syncen."""
import csv
import io

from flask import (
    Blueprint, render_template, redirect, url_for, flash, send_file
)
from flask_login import login_required

from ..extensions import db, limiter
from ..models import Registration
from ..decorators import role_required
from ..forms import ActionForm
from ..fluentform import sync_submissions

bp = Blueprint("teacher", __name__, url_prefix="/teacher")


@bp.route("/")
@login_required
@role_required("teacher", "admin")
def dashboard():
    return render_template("teacher_dashboard.html")


@bp.route("/registrations")
@login_required
@role_required("teacher", "admin")
def registrations():
    regs = (
        Registration.query
        .order_by(Registration.created_at.desc())
        .all()
    )
    # ActionForm einmal für CSRF-Token in jedem Zeilen-Button
    action_form = ActionForm()
    return render_template(
        "teacher_registrations.html",
        regs=regs,
        action_form=action_form,
    )


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


@bp.route("/export")
@login_required
@role_required("teacher", "admin")
def export():
    regs = Registration.query.order_by(Registration.created_at.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "id", "erstellt_am", "vorname", "nachname", "geburtsdatum",
        "strasse", "plz", "ort", "plz_ok", "status",
    ])
    for r in regs:
        plz_ok_str = {True: "ja", False: "nein", None: "unklar"}[r.plz_ok]
        writer.writerow([
            r.id,
            r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            r.vorname,
            r.nachname,
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
