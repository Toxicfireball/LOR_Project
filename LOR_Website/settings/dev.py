from .base import *



ALLOWED_HOSTS = ['localhost', '127.0.0.1']

INSTALLED_APPS += [
    'django_browser_reload',
]

MIDDLEWARE += [
    'django_browser_reload.middleware.BrowserReloadMiddleware',
]

# Templates in dev: show errors inline
TEMPLATES[0]['OPTIONS']['debug'] = True
# after load_dotenv…
NODE_BIN_PATH = os.environ.get("NODE_BIN_PATH", "node")
NPM_BIN_PATH  = os.environ.get("NPM_BIN_PATH",  "npm")