"""Admin-Bereich: PLZ-Regel, Logo-Branding verwalten."""
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required

from .. import branding, vorlagen
from ..extensions import db
from ..models import PlzRule
from ..decorators import role_required
from ..forms import ActionForm, PlzRuleForm, LogoForm, VorlageForm

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _get_or_create_rule() -> PlzRule:
    rule = PlzRule.query.filter_by(active=True).first()
    if rule is None:
        rule = PlzRule(active=True)
        db.session.add(rule)
        db.session.commit()
    return rule


@bp.route("/")
@login_required
@role_required("admin")
def dashboard():
    rule = _get_or_create_rule()
    return render_template("admin_dashboard.html", plz_rule=rule)


@bp.route("/plz", methods=["GET", "POST"])
@login_required
@role_required("admin")
def plz():
    rule = _get_or_create_rule()
    form = PlzRuleForm(obj=rule)

    if form.validate_on_submit():
        rule.reference_plz = form.reference_plz.data.strip()
        rule.allowed_kreis = (form.allowed_kreis.data or "").strip() or None
        rule.allowed_bezirk = (form.allowed_bezirk.data or "").strip() or None
        db.session.commit()
        flash("PLZ-Regel aktualisiert.", "success")
        return redirect(url_for("admin.plz"))

    return render_template("admin_plz.html", form=form, rule=rule)


@bp.route("/logo", methods=["GET", "POST"])
@login_required
@role_required("admin")
def logo():
    form = LogoForm()
    if form.validate_on_submit():
        try:
            branding.save_logo(form.logo.data)
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            flash("Logo hochgeladen.", "success")
        return redirect(url_for("admin.logo"))

    return render_template("admin_logo.html", form=form, has_logo=branding.has_logo())


@bp.route("/logo/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_logo():
    form = ActionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage (CSRF).", "error")
        return redirect(url_for("admin.logo"))

    branding.delete_logo()
    flash("Logo entfernt.", "success")
    return redirect(url_for("admin.logo"))


@bp.route("/vorlagen")
@login_required
@role_required("admin")
def vorlagen_view():
    form = VorlageForm()
    status = {key: vorlagen.has_vorlage(key) for key in vorlagen.VORLAGEN}
    return render_template(
        "admin_vorlagen.html", form=form, vorlagen=vorlagen.VORLAGEN, status=status
    )


@bp.route("/vorlagen/<key>/upload", methods=["POST"])
@login_required
@role_required("admin")
def upload_vorlage(key):
    if key not in vorlagen.VORLAGEN:
        flash("Unbekannte Vorlage.", "error")
        return redirect(url_for("admin.vorlagen_view"))

    form = VorlageForm()
    if form.validate_on_submit():
        try:
            vorlagen.save_vorlage(key, form.datei.data)
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            flash(f"{vorlagen.VORLAGEN[key]['label']} hochgeladen.", "success")
    else:
        for error in form.datei.errors:
            flash(error, "error")

    return redirect(url_for("admin.vorlagen_view"))


@bp.route("/vorlagen/<key>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_vorlage(key):
    if key not in vorlagen.VORLAGEN:
        flash("Unbekannte Vorlage.", "error")
        return redirect(url_for("admin.vorlagen_view"))

    form = ActionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage (CSRF).", "error")
        return redirect(url_for("admin.vorlagen_view"))

    vorlagen.delete_vorlage(key)
    flash(f"{vorlagen.VORLAGEN[key]['label']} entfernt.", "success")
    return redirect(url_for("admin.vorlagen_view"))
