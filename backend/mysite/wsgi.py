"""WSGI config for the portfolio API service.

Exposes the WSGI callable as a module-level variable named ``application``.
Run it with the project root as the working directory, e.g.
``gunicorn --chdir backend mysite.wsgi``. Static files are served by the web
server from ``STATIC_ROOT`` after ``manage.py collectstatic``, not from here.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

application = get_wsgi_application()
