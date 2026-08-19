"""Öffentliche Routen.

Aktuell nur die Startseite. Die eigentliche Anmeldung läuft seit dem
Wechsel zu Fluent Forms (auf der WordPress-Seite) nicht mehr hier.
"""
from flask import Blueprint, render_template, send_file, abort

from .. import branding

bp = Blueprint("public", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/logo")
def logo():
    if not branding.has_logo():
        abort(404)
    return send_file(branding.logo_path(), mimetype="image/png")
