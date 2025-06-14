# ─── Python + Tailwind in one stage ───────────────────────────────
FROM python:3.12.0-alpine3.18

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=LOR_Website.settings.prod \
    ALLOWED_HOSTS=lorbuilder.com,www.lorbuilder.com


# ── Stage 1: Build your Tailwind CSS with Node ───────────────────────
FROM node:20-alpine AS tailwind-builder

# 1) Copy only the theme (tailwind) files and install Node deps
WORKDIR /app/theme
COPY theme/package.json theme/package-lock.json ./
RUN npm ci

# 2) Copy the rest of your theme source and build the CSS
COPY theme/ ./
RUN npx tailwindcss \
      -i ./src/styles.css \
      -o ../static/css/tailwind.css \
      --minify

# ── Stage 2: Build your Django app ──────────────────────────────────
FROM python:3.12.0-alpine3.18

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=LOR_Website.settings.prod \
    ALLOWED_HOSTS=lorbuilder.com,www.lorbuilder.com

# 1) System tools (no Node needed here)
RUN apk update \
 && apk add --no-cache \
      build-base zlib-dev jpeg-dev freetype-dev curl \
 && rm -rf /var/cache/apk/*

WORKDIR /app

# 2) Python deps
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

# 3) Copy your Django code + the pre-built CSS from the builder stage
COPY . .
COPY --from=tailwind-builder /app/static/css/tailwind.css static/css/tailwind.css

# 4) Migrate & collectstatic (no Tailwind step here!)
RUN python manage.py migrate --noinput \
 && python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn","LOR_Website.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--timeout","120"]

