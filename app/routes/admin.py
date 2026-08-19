"""Admin-Bereich: PLZ-Regel, Logo-Branding verwalten."""
import json

from flask import Blueprint, Response, render_template, redirect, request, url_for, flash
from flask_login import login_required

from .. import branding, vorlagen
from ..extensions import db
from ..models import Abteilung, Bildungsgang, BildungsgangKreis, PlzRule
from ..decorators import role_required
from ..forms import (
    AbteilungForm, ActionForm, BildungsgangForm, BildungsgangImportForm,
    BildungsgangKreisForm, PlzRuleForm, LogoForm, VorlageForm,
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
    bildungsgaenge = Bildungsgang.query.order_by(Bildungsgang.name).all()
    return render_template(
        "admin_kreise.html",
        bildungsgaenge=bildungsgaenge,
        konfiguriert=konfiguriert,
    )


@bp.route("/kreise/<code>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def kreise_bildungsgang(code):
    bildungsgang = Bildungsgang.query.filter_by(code=code).first()
    if not bildungsgang:
        flash("Unbekannter Bildungsgang.", "error")
        return redirect(url_for("admin.kreise_view"))

    form = BildungsgangKreisForm()
    bestehende = BildungsgangKreis.query.filter_by(bildungsgang=code).all()

    if form.validate_on_submit():
        for bk in bestehende:
            db.session.delete(bk)
        for kreis in form.kreise.data:
            db.session.add(BildungsgangKreis(bildungsgang=code, kreis=kreis))
        db.session.commit()
        flash(f"Kreise für '{bildungsgang.name}' gespeichert.", "success")
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
        import_form=BildungsgangImportForm(),
        action_form=ActionForm(),
    )


@bp.route("/bildungsgaenge/export")
@login_required
@role_required("admin")
def bildungsgaenge_export():
    """JSON-Export aller Abteilungen/Bildungsgänge - zum Import auf einem
    anderen Server (z.B. Migration Produktiv-/Testinstanz), damit das nicht
    per Hand nachgepflegt werden muss.
    """
    daten = [
        {
            "abteilung": b.abteilung.name if b.abteilung else None,
            "name": b.name,
            "code": b.code,
        }
        for b in Bildungsgang.query.order_by(Bildungsgang.name).all()
    ]
    payload = json.dumps(daten, ensure_ascii=False, indent=2)
    return Response(
        payload,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=bildungsgaenge.json"},
    )


@bp.route("/bildungsgaenge/import", methods=["POST"])
@login_required
@role_required("admin")
def bildungsgaenge_import():
    """Gegenstück zu bildungsgaenge_export. Idempotent per Code: bestehende
    Bildungsgaenge werden aktualisiert (Name/Abteilung), neue angelegt -
    nichts wird geloescht, damit ein Import nie versehentlich Daten
    (Kreise-/Klassen-Zuordnungen haengen am Code) zerstoert.
    """
    form = BildungsgangImportForm()
    if not form.validate_on_submit():
        for error in form.datei.errors:
            flash(error, "error")
        return redirect(url_for("admin.bildungsgaenge_view"))

    try:
        daten = json.load(form.datei.data.stream)
    except (json.JSONDecodeError, UnicodeDecodeError):
        flash("Datei ist kein gültiges JSON.", "error")
        return redirect(url_for("admin.bildungsgaenge_view"))

    if not isinstance(daten, list):
        flash("Unerwartetes JSON-Format (Liste erwartet).", "error")
        return redirect(url_for("admin.bildungsgaenge_view"))

    angelegt = aktualisiert = uebersprungen = 0
    for eintrag in daten:
        if not isinstance(eintrag, dict):
            uebersprungen += 1
            continue
        name = (eintrag.get("name") or "").strip()
        code = (eintrag.get("code") or "").strip()
        abteilung_name = (eintrag.get("abteilung") or "").strip() or None
        if not name or not code:
            uebersprungen += 1
            continue

        abteilung = None
        if abteilung_name:
            abteilung = Abteilung.query.filter_by(name=abteilung_name).first()
            if abteilung is None:
                abteilung = Abteilung(name=abteilung_name)
                db.session.add(abteilung)
                db.session.flush()

        bildungsgang = Bildungsgang.query.filter_by(code=code).first()
        if bildungsgang is None:
            db.session.add(Bildungsgang(
                name=name, code=code,
                abteilung_id=abteilung.id if abteilung else None,
            ))
            angelegt += 1
        else:
            bildungsgang.name = name
            if abteilung is not None:
                bildungsgang.abteilung_id = abteilung.id
            aktualisiert += 1

    db.session.commit()
    flash(
        f"Import fertig: {angelegt} angelegt, {aktualisiert} aktualisiert"
        + (f", {uebersprungen} übersprungen (unvollständig)." if uebersprungen else "."),
        "success",
    )
    return redirect(url_for("admin.bildungsgaenge_view"))


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
        code = form.code.data.strip()
        if Bildungsgang.query.filter_by(name=name).first():
            flash(f"Bildungsgang '{name}' existiert bereits.", "error")
        elif Bildungsgang.query.filter_by(code=code).first():
            flash(f"Code '{code}' wird bereits verwendet.", "error")
        else:
            abteilung_id = form.abteilung_id.data if form.abteilung_id.raw_data and form.abteilung_id.raw_data[0] else None
            db.session.add(Bildungsgang(name=name, code=code, abteilung_id=abteilung_id))
            db.session.commit()
            flash(f"Bildungsgang '{name}' angelegt.", "success")
    else:
        for error in form.name.errors + form.code.errors:
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
