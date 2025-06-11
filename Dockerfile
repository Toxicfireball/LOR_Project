# syntax=docker/dockerfile:1

# ─── Stage 1: Build Tailwind ──────────────────────────────────────
FROM node:18-alpine AS node-build

WORKDIR /app/theme/static_src

# Copy **all** Tailwind sources+config
COPY theme/static_src/ .

# Install & build your CSS/JS
RUN npm ci
RUN npm run build


# ─── Stage 2: Python & Django ────────────────────────────────────
FROM python:3.12.0-alpine3.18

# Envs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=LOR_Website.settings.prod \
    ALLOWED_HOSTS=lorbuilder.com,www.lorbuilder.com

# 1) Install build deps, create venv & pip install, THEN
# 2) Uninstall build deps to free up memory in the same layer
RUN apk update \
 && apk add --no-cache build-base zlib-dev jpeg-dev freetype-dev curl \
 && python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt \
 && apk del build-base \
 && rm -rf /var/cache/apk/*

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy your Django code
COPY . .

# Pull in the already-built Tailwind assets
COPY --from=node-build /app/theme/static_src/dist ./theme/static_src/dist

# Only run migrations + collectstatic (no more tailwind build here)
RUN python manage.py migrate --noinput \
 && python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn","LOR_Website.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--timeout","120"]
