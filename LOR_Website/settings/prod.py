from .base import *
import os

DEBUG = False

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

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE  = True
