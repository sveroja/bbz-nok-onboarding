"""Admin-Bereich: PLZ-Regel verwalten."""
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required

from ..extensions import db
from ..models import PlzRule
from ..decorators import role_required
from ..forms import PlzRuleForm

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
