# ─── Python + Tailwind in one stage ───────────────────────────────
FROM python:3.12.0-alpine3.18

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=LOR_Website.settings.prod \
    ALLOWED_HOSTS=lorbuilder.com,www.lorbuilder.com

# …

# 1) Install Node & build tools
RUN apk update \
 && apk add --no-cache \
      nodejs npm \
      build-base zlib-dev jpeg-dev freetype-dev curl \
 && ln -sf /usr/bin/nodejs /usr/bin/node \
 && rm -rf /var/cache/apk/*

# 2) Tell django-tailwind where to find them:
ENV NODE_BIN_PATH=/usr/bin/node \
    NPM_BIN_PATH=/usr/bin/npm

WORKDIR /app

# 3) Python & dependencies
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

# 4) Copy code & build assets
COPY . .
RUN python manage.py migrate --noinput \
 && python manage.py tailwind install \
 && python manage.py tailwind build \
 && python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "LOR_Website.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]

