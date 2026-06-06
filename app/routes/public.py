"""Öffentliche Routen.

Aktuell nur die Startseite. Die eigentliche Anmeldung läuft seit dem
Wechsel zu Fluent Forms (auf der WordPress-Seite) nicht mehr hier.
"""
from flask import Blueprint, render_template

bp = Blueprint("public", __name__)


@bp.route("/")
def index():
    return render_template("index.html")
