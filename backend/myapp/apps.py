"""App configuration for the portfolio content app."""

from django.apps import AppConfig


class MyappConfig(AppConfig):
    """App config for the portfolio content models and API."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'
