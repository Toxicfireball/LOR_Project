# 1) Start from a slim Python image
FROM python:3.12-slim

# 2) Install the OS-level dependencies that Pillow (and many Django apps) need.
#    We include zlib1g-dev so that Pillow can compile PNG support;
#    libjpeg-dev for JPEG support; and libfreetype6-dev if you ever use Pillow's font routines.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
       build-essential \
       zlib1g-dev \
       libjpeg-dev \
       libfreetype6-dev && \
    rm -rf /var/lib/apt/lists/*

# 3) Create a virtualenv in /opt/venv, then install Python dependencies
#    We copy only requirements.txt first to take advantage of Docker’s layer cache.
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt

# 4) Copy the rest of your code into /app (including manage.py, your apps, etc.)
COPY . .

# 5) Ensure /opt/venv is on PATH, and expose port 8000
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE 8000

# 6) Finally, run Gunicorn to serve your Django project.
#    Replace “LOR_Website.wsgi:application” with the correct dotted path to your WSGI app if needed.
CMD ["gunicorn", "LOR_Website.wsgi:application", "--bind", "0.0.0.0:8000"]
