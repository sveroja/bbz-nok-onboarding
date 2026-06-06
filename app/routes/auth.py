"""Auth-Routen: Login und Logout."""
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request
)
from flask_login import login_user, logout_user, login_required, current_user

from ..extensions import limiter
from ..models import User
from ..forms import LoginForm

bp = Blueprint("auth", __name__)


def _post_login_redirect(user) -> str:
    """Wohin nach erfolgreichem Login?"""
    # 'next' aus dem GET-Parameter respektieren, aber nur wenn es relativ ist
    next_url = request.args.get("next")
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    if user.role == "admin":
        return url_for("admin.dashboard")
    return url_for("teacher.dashboard")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_post_login_redirect(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Erfolgreich angemeldet.", "success")
            return redirect(_post_login_redirect(user))
        flash("Benutzername oder Passwort falsch.", "error")
    return render_template("login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Abgemeldet.", "info")
    return redirect(url_for("public.index"))
