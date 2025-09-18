import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# settings.py (at the very top, above everything else)
import bleach

# keep a reference to the real clean()
_orig_bleach_clean = bleach.clean

def clean_with_styles(text, *args, styles=None, **kwargs):
    # drop the unsupported `styles=` argument
    return _orig_bleach_clean(text, *args, **kwargs)

# replace bleach.clean globally
bleach.clean = clean_with_styles


# ─── Base directory ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

# ─── SECURITY ───────────────────────────────────────────────────────────────────
SECRET_KEY = 'django-insecure-wm5ej4&6+ve6-#=t396=l68%@fb+r2fev*(a0_&$00@evg_5a&'
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY is required")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local").lower()

DEBUG = ENVIRONMENT == "local"
# ─── INSTALLED APPS ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Django
    "nested_admin", 
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_select2',

    # Tailwind + theme

    'tailwind',
    'theme',

    # Your apps
    'home',
    'accounts',
    'campaigns',
    'characters.apps.CharactersConfig',
    
    "django_summernote",
]
X_FRAME_OPTIONS = "SAMEORIGIN"
TAILWIND_APP_NAME = "theme"
SUMMERNOTE_CONFIG = {
    # Use an <iframe> so your site’s CSS won’t bleed into the editor
    "iframe": True,
    "summernote": {
            'base_css': (),     # don’t inject BS3 CSS
    'base_js': (),      # don’t inject BS3 JS
        "width": "100%",
        "height": "400px",
        # You can customize the toolbar here if you like:
        "toolbar": [
            ["style", ["style"]],
            ["font", ["bold", "italic", "underline", "clear"]],
            ["fontname", ["fontname"]],
            ["fontsize", ["fontsize"]],
            ["color", ["color"]],
            ["para", ["ul", "ol", "paragraph"]],
            ["table", ["table"]],
            ["insert", ["link", "picture", "video"]],
            ["view", ["fullscreen", "codeview", "help"]],
        ],
    },
}
# ─── MIDDLEWARE ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',           # ← WhiteNoise
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
import os

# after load_dotenv…
NODE_BIN_PATH = os.environ.get("NODE_BIN_PATH", "node")
NPM_BIN_PATH  = os.environ.get("NPM_BIN_PATH",  "npm")

ROOT_URLCONF = 'LOR_Website.urls'
WSGI_APPLICATION = 'LOR_Website.wsgi.application'

# ─── TEMPLATES ──────────────────────────────────────────────────────────────────
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

# ─── DATABASE ───────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL must be set")

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=True,
    )
}

# ─── INTERNATIONALIZATION ────────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ─── STATIC & MEDIA ──────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR.parent / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
