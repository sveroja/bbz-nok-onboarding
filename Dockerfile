# Schlankes Image; slim reicht, da wir keine Native-Builds brauchen.
FROM python:3.12-slim

# Best-Practice ENV-Vars
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Non-root user für die App
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

# Erst nur requirements – nutzt den Docker-Layer-Cache
COPY requirements.txt .
RUN pip install -r requirements.txt

# App-Code
COPY . .

# Entrypoint ausführbar machen
RUN chmod +x /app/docker/entrypoint.sh

# instance/ gehört dem App-User (für SQLite-DB)
RUN mkdir -p /app/instance && chown -R app:app /app

USER app

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "app:create_app()"]
