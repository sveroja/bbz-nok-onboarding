"""Logo-Branding: Upload/Speichern/Ausliefern des Admin-Logos.

Liegt in instance/logo.png - das Verzeichnis ist ueber das Docker-Volume
persistent (uebersteht Rebuilds), anders als app/static/.
"""
from pathlib import Path

from flask import current_app
from PIL import Image, UnidentifiedImageError

LOGO_FILENAME = "logo.png"


def _instance_dir() -> Path:
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    return Path(uri.replace("sqlite:///", "")).parent


def logo_path() -> Path:
    return _instance_dir() / LOGO_FILENAME


def has_logo() -> bool:
    return logo_path().exists()


def save_logo(file_storage) -> None:
    """Prueft per Pillow, ob die Datei wirklich ein Bild ist, und speichert
    sie normalisiert als PNG (verwirft dabei ggf. eingebettete Payloads).
    Wirft ValueError bei ungueltigen Dateien.
    """
    try:
        Image.open(file_storage.stream).verify()
        # verify() macht das Image-Objekt danach unbrauchbar - fuer den
        # eigentlichen Save muss die Datei neu geoeffnet werden.
        file_storage.stream.seek(0)
        image = Image.open(file_storage.stream).convert("RGBA")
    except (UnidentifiedImageError, OSError):
        raise ValueError("Datei ist kein gültiges Bild.")

    _instance_dir().mkdir(parents=True, exist_ok=True)
    image.save(logo_path(), format="PNG")


def delete_logo() -> None:
    path = logo_path()
    if path.exists():
        path.unlink()
