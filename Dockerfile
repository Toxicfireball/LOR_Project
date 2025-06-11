# ─── Stage 1: Build Tailwind assets ─────────────────────────────────────────────
FROM node:18-alpine AS node-build
WORKDIR /app

# cache npm install
COPY theme/package.json theme/package-lock.json ./theme/
RUN cd theme && npm ci

# copy everything and build Tailwind via django-tailwind CLI
COPY . .
# install django-tailwind CLI if you haven't yet: 
# pip install django-tailwind  (we'll do that in the next stage)
RUN cd theme && npm run build

# ─── Stage 2: Python & Django ─────────────────────────────────────────────────
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED   1
ENV DJANGO_SETTINGS_MODULE=LOR_Website.settings.prod
ENV ALLOWED_HOSTS=lorbuilder.com,www.lorbuilder.com
# system deps for Pillow, etc.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      zlib1g-dev libjpeg-dev libfreetype6-dev \
      curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# create venv & install
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

# copy source
COPY . .

# bring in built Tailwind assets
COPY --from=node-build /app/theme/static_src/dist ./theme/static_src/dist

# Django setup: migrate, Tailwind build, collectstatic
RUN python manage.py migrate --noinput \
 && python manage.py tailwind install \
 && python manage.py tailwind build \
 && python manage.py collectstatic --noinput

EXPOSE 8000

# use Gunicorn with JSON‐array form
CMD ["gunicorn","LOR_Website.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--timeout","120"]

