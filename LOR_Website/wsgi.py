"""
WSGI config for LOR_Website project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

import os

ENV = os.getenv('ENVIRONMENT', 'local').lower()
if ENV in ('prod', 'production'):
    module = 'LOR_Website.settings.prod'
else:
    module = 'LOR_Website.settings.dev'

os.environ.setdefault('DJANGO_SETTINGS_MODULE', module)

application = get_wsgi_application()
