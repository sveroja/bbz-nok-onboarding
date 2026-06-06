#!/bin/sh
set -e

# Beim ersten Start (oder wenn die DB fehlt) init-db ausführen.
# init-db ist idempotent: legt Tabellen nur an, wenn sie fehlen,
# und Standardnutzer nur, wenn sie noch nicht existieren.
echo "[entrypoint] Initialisiere Datenbank (idempotent)..."
flask --app run.py init-db

# Eigentliches Kommando (CMD aus dem Dockerfile) ausführen
echo "[entrypoint] Starte: $@"
exec "$@"
