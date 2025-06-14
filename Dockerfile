# ─── Python + Tailwind in one stage ───────────────────────────────
FROM python:3.12.0-alpine3.18

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=LOR_Website.settings.prod \
    ALLOWED_HOSTS=lorbuilder.com,www.lorbuilder.com


# 1) Install Node & npm
RUN apk update \
 && apk add --no-cache nodejs npm \
 && rm -rf /var/cache/apk/*

# 2) Symlink nodejs → node (this will always run now)
RUN ln -sf /usr/bin/nodejs /usr/bin/node

# 3) Export the paths so django-tailwind picks them up
ENV NODE_BIN_PATH=/usr/bin/node \
    NPM_BIN_PATH=/usr/bin/npm

WORKDIR /app

# 4) Set up your Python venv & install deps
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

# 5) Copy code & build your assets
COPY . .
# sanity check: this should now print a Node version
RUN node -v && npm -v

# 6) Run migrations, Tailwind, collectstatic
RUN python manage.py migrate --noinput \
 && python manage.py tailwind install \
 && python manage.py tailwind build \
 && python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn","LOR_Website.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--timeout","120"]
