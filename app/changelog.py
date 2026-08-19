"""Release-Historie fuer die Startseite: liest 'git log' zur Laufzeit aus.

Braucht .git im Image (siehe .dockerignore) - zeigt dadurch automatisch
genau den Stand, der gerade laeuft, ohne separaten Build-Schritt.
"""
import logging
import subprocess

from .config import BASE_DIR

logger = logging.getLogger(__name__)


def recent_commits(limit: int = 8) -> list[dict]:
    """[{hash, date, message}, ...], neueste zuerst. Leere Liste bei Fehler
    (z.B. .git fehlt) - Startseite soll dadurch nie kaputtgehen.
    """
    try:
        result = subprocess.run(
            ["git", "log", f"-n{limit}", "--date=short",
             "--pretty=format:%h|%ad|%s"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except Exception:
        logger.warning("Konnte Git-Historie nicht lesen.", exc_info=True)
        return []

    commits = []
    for line in result.stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            commits.append({"hash": parts[0], "date": parts[1], "message": parts[2]})
    return commits
