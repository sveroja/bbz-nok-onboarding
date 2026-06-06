"""Decorators für Rollenprüfung."""
from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(*roles: str):
    """Verlangt, dass current_user eine der angegebenen Rollen hat.

    Beispiel:
        @role_required("admin")
        def view(): ...

        @role_required("admin", "teacher")
        def view(): ...

    Annahme: Vorher wurde bereits @login_required aufgerufen (sonst 401).
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
