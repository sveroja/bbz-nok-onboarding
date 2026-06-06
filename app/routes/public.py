"""Öffentliche Routen: Index und mehrstufige Anmeldung."""
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, redirect, url_for, session, flash, current_app
)

from ..extensions import db
from ..models import Registration, PlzRule
from ..forms import RegisterStep1Form, RegisterStep2Form, SummarySubmitForm
from ..plz import check_plz_against_rule

bp = Blueprint("public", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/register/step/1", methods=["GET", "POST"])
def register_step1():
    form = RegisterStep1Form()
    if form.validate_on_submit():
        session["registration"] = {
            "vorname": form.vorname.data.strip(),
            "nachname": form.nachname.data.strip(),
            "geburtsdatum": form.geburtsdatum.data.isoformat(),
        }
        return redirect(url_for("public.register_step2"))
    return render_template("register_step1.html", form=form)


@bp.route("/register/step/2", methods=["GET", "POST"])
def register_step2():
    if "registration" not in session:
        return redirect(url_for("public.register_step1"))

    form = RegisterStep2Form()
    if form.validate_on_submit():
        reg = session["registration"]
        reg.update({
            "strasse": form.strasse.data.strip(),
            "plz": form.plz.data.strip(),
            "ort": form.ort.data.strip(),
        })
        session["registration"] = reg
        return redirect(url_for("public.register_summary"))
    return render_template("register_step2.html", form=form)


@bp.route("/register/summary", methods=["GET", "POST"])
def register_summary():
    reg = session.get("registration")
    if not reg:
        return redirect(url_for("public.register_step1"))

    form = SummarySubmitForm()
    if form.validate_on_submit():
        rule = PlzRule.query.filter_by(active=True).first()
        plz_ok = check_plz_against_rule(reg["plz"], rule)

        new_reg = Registration(
            vorname=reg["vorname"],
            nachname=reg["nachname"],
            geburtsdatum=datetime.fromisoformat(reg["geburtsdatum"]).date(),
            strasse=reg["strasse"],
            plz=reg["plz"],
            ort=reg["ort"],
            plz_ok=plz_ok,
            plz_checked_at=datetime.now(timezone.utc),
        )
        db.session.add(new_reg)
        db.session.commit()

        session.pop("registration", None)
        return render_template("register_done.html", plz_ok=plz_ok)

    return render_template("register_summary.html", reg=reg, form=form)
