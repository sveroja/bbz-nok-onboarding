"""CLI-Befehle für die Flask-App.

    flask --app run.py init-db
    flask --app run.py create-user <username> <admin|teacher>
    flask --app run.py sync-fluentform
"""
import os
import getpass

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import User, PlzRule


def register_cli(app):
    app.cli.add_command(init_db)
    app.cli.add_command(create_user)
    app.cli.add_command(sync_fluentform)


@click.command("init-db")
@with_appcontext
def init_db():
    """Legt Tabellen und Standardnutzer an.

    Passwörter werden aus den ENV-Variablen
    ADMIN_PASSWORD / TEACHER_PASSWORD gelesen.
    """
    db.create_all()
    click.echo("Tabellen angelegt.")

    admin_pw = os.environ.get("ADMIN_PASSWORD")
    teacher_pw = os.environ.get("TEACHER_PASSWORD")

    if not admin_pw or not teacher_pw:
        click.echo(
            "WARNUNG: ADMIN_PASSWORD oder TEACHER_PASSWORD nicht in .env gesetzt. "
            "Es werden keine Standardnutzer angelegt.",
            err=True,
        )
    else:
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", role="admin")
            admin.set_password(admin_pw)
            db.session.add(admin)
            click.echo("Admin-Nutzer 'admin' angelegt.")

        if not User.query.filter_by(username="lehrer").first():
            teacher = User(username="lehrer", role="teacher")
            teacher.set_password(teacher_pw)
            db.session.add(teacher)
            click.echo("Lehrer-Nutzer 'lehrer' angelegt.")

    if not PlzRule.query.filter_by(active=True).first():
        rule = PlzRule(
            reference_plz=os.environ.get("REFERENCE_PLZ", "24768"),
            active=True,
        )
        db.session.add(rule)
        click.echo("Standard-PLZ-Regel angelegt.")

    db.session.commit()
    click.echo("Datenbank initialisiert.")


@click.command("create-user")
@click.argument("username")
@click.argument("role", type=click.Choice(["admin", "teacher"]))
@with_appcontext
def create_user(username, role):
    """Legt einen neuen Nutzer an. Passwort wird interaktiv abgefragt."""
    if User.query.filter_by(username=username).first():
        click.echo(f"Nutzer '{username}' existiert bereits.", err=True)
        return

    password = getpass.getpass("Passwort: ")
    password2 = getpass.getpass("Passwort wiederholen: ")
    if password != password2:
        click.echo("Passwörter stimmen nicht überein.", err=True)
        return
    if len(password) < 8:
        click.echo("Passwort muss mindestens 8 Zeichen haben.", err=True)
        return

    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Nutzer '{username}' ({role}) angelegt.")


@click.command("sync-fluentform")
@with_appcontext
def sync_fluentform():
    """Holt neue Anmeldungen aus Fluent Forms (WordPress) ab."""
    from .fluentform import sync_submissions

    try:
        result = sync_submissions()
    except RuntimeError as exc:
        click.echo(f"FEHLER: {exc}", err=True)
        raise click.Abort()
    except Exception as exc:
        click.echo(f"FEHLER beim Sync: {exc}", err=True)
        raise click.Abort()

    click.echo(
        f"Sync fertig: {result['fetched']} geholt, "
        f"{result['created']} neu angelegt, "
        f"{result['skipped']} bereits vorhanden (übersprungen), "
        f"{result['errors']} Fehler."
    )
