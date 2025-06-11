from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

INSTALLED_APPS += [
    'django_browser_reload',
]

MIDDLEWARE += [
    'django_browser_reload.middleware.BrowserReloadMiddleware',
]

# Templates in dev: show errors inline
TEMPLATES[0]['OPTIONS']['debug'] = True
