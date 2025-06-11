# syntax=docker/dockerfile:1

# ─── Stage 1: Build Tailwind assets ─────────────────────────────
FROM node:18-alpine AS node-build
WORKDIR /app/theme/static_src

# Copy only the npm manifests
COPY theme/static_src/package.json package.json
COPY theme/static_src/package-lock.json package-lock.json

# Install & build
RUN npm ci
RUN npm run build


# ─── Stage 2: Python & Django ────────────────────────────────────
FROM python:3.12.0-alpine3.18
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=LOR_Website.settings.prod \
    ALLOWED_HOSTS=lorbuilder.com,www.lorbuilder.com

# System dependencies for Pillow, etc.
RUN apk update \
 && apk add --no-cache \
      build-base zlib-dev jpeg-dev freetype-dev curl

WORKDIR /app

# Install Python deps in a clean venv
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

# Copy your Django project
COPY . .

# Pull in the built Tailwind assets
COPY --from=node-build /app/theme/static_src/dist ./theme/static_src/dist

# Final Django setup
RUN python manage.py migrate --noinput \
 && python manage.py tailwind install \
 && python manage.py tailwind build \
 && python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn","LOR_Website.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--timeout","120"]
