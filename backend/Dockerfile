# Contexte de build : la racine du dépôt (l'image a besoin de backend/ et de
# eptinjs/backend/). Construire avec : docker build -f backend/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=injs_lmd.settings \
    PORT=8001

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Le module eptinjs vit hors de backend/ : on le place hors de /app pour qu'un
# montage de volume sur /app (docker-compose) ne le masque pas. Les settings
# ajoutent /eptinjs/backend au sys.path.
COPY eptinjs/backend /eptinjs/backend

RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /app/staticfiles /app/media \
    && DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8001

ENTRYPOINT ["/app/entrypoint.sh"]
