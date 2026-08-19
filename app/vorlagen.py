"""Verwaltung der Export-Vorlagen: Stammdatenblatt-PDF, Klassenbuch-xlsx,
DaZ-xlsx. Liegen in instance/vorlagen/ (admin-hochladbar, persistent uebers
Docker-Volume, absichtlich nie im Git-Repo - siehe .gitignore).
"""
from pathlib import Path

import openpyxl
from flask import current_app
from pypdf import PdfReader

VORLAGEN = {
    "stammdatenblatt": {
        "filename": "stammdatenblatt.pdf",
        "label": "Stammdatenblatt (PDF)",
        "ext": "pdf",
    },
    "klassenbuch": {
        "filename": "klassenbuch.xlsx",
        "label": "WebUntis (xlsx)",
        "ext": "xlsx",
    },
    "daz": {
        "filename": "daz.xlsx",
        "label": "DaZ-Statistik (xlsx)",
        "ext": "xlsx",
    },
}


def _vorlagen_dir() -> Path:
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    instance_dir = Path(uri.replace("sqlite:///", "")).parent
    return instance_dir / "vorlagen"


def vorlage_path(key: str) -> Path:
    return _vorlagen_dir() / VORLAGEN[key]["filename"]


def has_vorlage(key: str) -> bool:
    return vorlage_path(key).exists()


def save_vorlage(key: str, file_storage) -> None:
    """Prueft, dass die Datei wirklich zum erwarteten Typ passt (PDF/XLSX
    lassen sich oeffnen), bevor sie gespeichert wird. Wirft ValueError
    bei ungueltigen Dateien.
    """
    ext = VORLAGEN[key]["ext"]
    try:
        if ext == "xlsx":
            openpyxl.load_workbook(file_storage.stream)
        else:
            PdfReader(file_storage.stream)
    except Exception:
        raise ValueError(f"Datei ist keine gültige {ext.upper()}-Datei.")

    file_storage.stream.seek(0)
    _vorlagen_dir().mkdir(parents=True, exist_ok=True)
    file_storage.save(vorlage_path(key))


def delete_vorlage(key: str) -> None:
    path = vorlage_path(key)
    if path.exists():
        path.unlink()
