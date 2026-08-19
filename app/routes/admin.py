"""Admin-Bereich: PLZ-Regel, Logo-Branding verwalten."""
from flask import Blueprint, render_template, redirect, request, url_for, flash
from flask_login import login_required

from .. import branding, vorlagen
from ..extensions import db
from ..models import Abteilung, Bildungsgang, BildungsgangKreis, PlzRule
from ..decorators import role_required
from ..forms import (
    AbteilungForm, ActionForm, BildungsgangForm, BildungsgangKreisForm,
    PlzRuleForm, LogoForm, VorlageForm,
)

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


@bp.route("/kreise")
@login_required
@role_required("admin")
def kreise_view():
    konfiguriert = {
        bk.bildungsgang
        for bk in BildungsgangKreis.query.with_entities(BildungsgangKreis.bildungsgang).distinct()
    }
    bildungsgaenge = [b.name for b in Bildungsgang.query.order_by(Bildungsgang.name).all()]
    return render_template(
        "admin_kreise.html",
        bildungsgaenge=bildungsgaenge,
        konfiguriert=konfiguriert,
    )


@bp.route("/kreise/<bildungsgang>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def kreise_bildungsgang(bildungsgang):
    if not Bildungsgang.query.filter_by(name=bildungsgang).first():
        flash("Unbekannter Bildungsgang.", "error")
        return redirect(url_for("admin.kreise_view"))

    form = BildungsgangKreisForm()
    bestehende = BildungsgangKreis.query.filter_by(bildungsgang=bildungsgang).all()

    if form.validate_on_submit():
        for bk in bestehende:
            db.session.delete(bk)
        for kreis in form.kreise.data:
            db.session.add(BildungsgangKreis(bildungsgang=bildungsgang, kreis=kreis))
        db.session.commit()
        flash(f"Kreise für '{bildungsgang}' gespeichert.", "success")
        return redirect(url_for("admin.kreise_view"))

    if request.method == "GET":
        form.kreise.data = [bk.kreis for bk in bestehende]

    return render_template(
        "admin_kreise_bildungsgang.html", form=form, bildungsgang=bildungsgang,
    )


@bp.route("/bildungsgaenge")
@login_required
@role_required("admin")
def bildungsgaenge_view():
    """Uebersicht aller Bildungsgaenge, gruppiert nach Abteilung. Ersetzt die
    frueher fest im Code hinterlegte BILDUNGSGANG_CHOICES-Liste.
    """
    abteilungen_liste = Abteilung.query.order_by(Abteilung.name).all()
    ohne_abteilung = (
        Bildungsgang.query.filter_by(abteilung_id=None).order_by(Bildungsgang.name).all()
    )
    return render_template(
        "admin_bildungsgaenge.html",
        abteilungen=abteilungen_liste,
        ohne_abteilung=ohne_abteilung,
        abteilung_form=AbteilungForm(),
        bildungsgang_form=BildungsgangForm(),
        action_form=ActionForm(),
    )


@bp.route("/abteilungen/hinzufuegen", methods=["POST"])
@login_required
@role_required("admin")
def abteilung_hinzufuegen():
    form = AbteilungForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        if Abteilung.query.filter_by(name=name).first():
            flash(f"Abteilung '{name}' existiert bereits.", "error")
        else:
            db.session.add(Abteilung(name=name))
            db.session.commit()
            flash(f"Abteilung '{name}' angelegt.", "success")
    else:
        for error in form.name.errors:
            flash(error, "error")
    return redirect(url_for("admin.bildungsgaenge_view"))


@bp.route("/abteilungen/<int:abteilung_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def abteilung_delete(abteilung_id):
    form = ActionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage (CSRF).", "error")
        return redirect(url_for("admin.bildungsgaenge_view"))

    abteilung = db.session.get(Abteilung, abteilung_id)
    if abteilung is None:
        flash("Abteilung nicht gefunden.", "error")
        return redirect(url_for("admin.bildungsgaenge_view"))

    if Bildungsgang.query.filter_by(abteilung_id=abteilung_id).first():
        flash(
            f"Abteilung '{abteilung.name}' hat noch zugeordnete Bildungsgänge - "
            "erst diese umhängen oder löschen.", "error",
        )
        return redirect(url_for("admin.bildungsgaenge_view"))

    db.session.delete(abteilung)
    db.session.commit()
    flash(f"Abteilung '{abteilung.name}' gelöscht.", "success")
    return redirect(url_for("admin.bildungsgaenge_view"))


@bp.route("/bildungsgaenge/hinzufuegen", methods=["POST"])
@login_required
@role_required("admin")
def bildungsgang_hinzufuegen():
    form = BildungsgangForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        if Bildungsgang.query.filter_by(name=name).first():
            flash(f"Bildungsgang '{name}' existiert bereits.", "error")
        else:
            abteilung_id = form.abteilung_id.data if form.abteilung_id.raw_data and form.abteilung_id.raw_data[0] else None
            db.session.add(Bildungsgang(name=name, abteilung_id=abteilung_id))
            db.session.commit()
            flash(f"Bildungsgang '{name}' angelegt.", "success")
    else:
        for error in form.name.errors:
            flash(error, "error")
    return redirect(url_for("admin.bildungsgaenge_view"))


@bp.route("/bildungsgaenge/<int:bildungsgang_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def bildungsgang_delete(bildungsgang_id):
    form = ActionForm()
    if not form.validate_on_submit():
        flash("Ungültige Anfrage (CSRF).", "error")
        return redirect(url_for("admin.bildungsgaenge_view"))

    bildungsgang = db.session.get(Bildungsgang, bildungsgang_id)
    if bildungsgang is None:
        flash("Bildungsgang nicht gefunden.", "error")
        return redirect(url_for("admin.bildungsgaenge_view"))

    db.session.delete(bildungsgang)
    db.session.commit()
    flash(f"Bildungsgang '{bildungsgang.name}' gelöscht.", "success")
    return redirect(url_for("admin.bildungsgaenge_view"))


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
