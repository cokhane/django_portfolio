"""Settings for the portfolio frontend.

This project renders the public site and owns no data of its own: it has
no database, no auth and no admin. Every piece of content is fetched from
the backend API over HTTP (see `ui/api.py`).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from portfolio_shared.env import allowed_hosts, debug_enabled, secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR.parent / ".env")

DEBUG = debug_enabled()
SECRET_KEY = secret_key(debug=DEBUG)
ALLOWED_HOSTS = allowed_hosts()

# Where the backend API lives, and how long to wait for it.
PORTFOLIO_API_BASE_URL = os.environ.get(
    "PORTFOLIO_API_BASE_URL", "http://127.0.0.1:8001"
).rstrip("/")
PORTFOLIO_API_TIMEOUT = float(os.environ.get("PORTFOLIO_API_TIMEOUT", "5.0"))

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "ui",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "frontend_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "frontend_site.wsgi.application"

# No DATABASES: this project is a pure API consumer.
DATABASES = {}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
