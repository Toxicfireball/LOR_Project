# ── Stage 1: Build Tailwind CSS ─────────────────────────────────────────────
FROM public.ecr.aws/docker/library/node:20-alpine AS tailwind-builder

WORKDIR /app/theme/static_src

# 1) Copy only the package files so Docker can cache npm ci
COPY theme/static_src/package.json theme/static_src/package-lock.json ./

# 2) Install your Tailwind/NPM deps
RUN npm ci

# 3) Copy the rest of your Tailwind source
COPY theme/static_src ./

# 4) Build your CSS into the project’s static folder
#    - input:  src/styles.css
#    - output: ../../static/css/tailwind.css   (→ /app/static/css/tailwind.css)
RUN npx tailwindcss \
      -i src/styles.css \
      -o ../../static/css/tailwind.css \
      --minify

# ── Stage 2: Build Django app ───────────────────────────────────────────────

FROM public.ecr.aws/docker/library/python:3.12.7-alpine3.20


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=LOR_Website.settings.prod \
    ALLOWED_HOSTS=lorbuilder.com,www.lorbuilder.com

# 1) System deps (no Node here)
RUN apk update \
 && apk add --no-cache \
      build-base zlib-dev jpeg-dev freetype-dev curl \
 && rm -rf /var/cache/apk/*

WORKDIR /app

# 2) Python venv & pip install
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

# 3) Copy in your code AND the prebuilt CSS
COPY . .
# The previous stage wrote /app/static/css/tailwind.css
# So static/css/tailwind.css now exists in this image too.

# 4) Migrate & collectstatic (no tailwind build step here!)
RUN python manage.py migrate --noinput \
 && python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn","LOR_Website.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--timeout","120"]
