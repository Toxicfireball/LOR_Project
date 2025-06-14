from .base import *
import os


_raw = os.environ.get("ALLOWED_HOSTS", None)
if _raw:
    ALLOWED_HOSTS = _raw.split(",")
else:
    ALLOWED_HOSTS = [
        "lorbuilder.com",
        "www.lorbuilder.com",
        "localhost",
        "127.0.0.1",
    ]

CSRF_TRUSTED_ORIGINS = [
    "https://lorbuilder.com",
    "https://www.lorbuilder.com",
]
# Tell django-tailwind which app holds your tailwind config
TAILWIND_APP_NAME = "theme"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE  = True
import os

# after your other settings…
NODE_BIN_PATH = os.environ.get("NODE_BIN_PATH", "node")
NPM_BIN_PATH  = os.environ.get("NPM_BIN_PATH",  "npm")
