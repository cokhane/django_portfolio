"""Environment-driven settings shared by both Django projects.

Both projects read the same three environment variables, with the same
fail-closed rules. Defining that contract twice is how the two copies drift,
so it lives here and each project's ``settings.py`` calls into it.
"""

import os
from typing import NamedTuple

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

DEV_SECRET_KEY = "django-insecure-dev-only-not-for-production"

_MISSING_KEY_HELP = (
    "DJANGO_SECRET_KEY is not set and DEBUG is off. Refusing to start with a "
    "publicly known key. Generate one with: python -c 'from "
    "django.core.management.utils import get_random_secret_key; "
    "print(get_random_secret_key())'"
)


def debug_enabled():
    """Return whether debug mode is on.

    Off unless explicitly enabled, so a deployment that forgets to configure
    anything fails closed rather than exposing tracebacks.
    """
    return os.environ.get("DJANGO_DEBUG", "0") == "1"


def secret_key(*, debug):
    """Return the signing key.

    Outside debug mode a real key is mandatory: falling back to the shared
    development literal would silently sign cookies with a key that is
    committed to a public repository.
    """
    configured = os.environ.get("DJANGO_SECRET_KEY")
    if configured:
        return configured
    if not debug:
        raise ImproperlyConfigured(_MISSING_KEY_HELP)
    return DEV_SECRET_KEY


def allowed_hosts():
    """Return the host allowlist, defaulting to loopback only."""
    raw = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
    return [host.strip() for host in raw.split(",") if host.strip()]


class EnvironmentSettings(NamedTuple):
    """The three settings both projects derive from the environment."""

    debug: bool
    secret_key: str
    allowed_hosts: list[str]


def environment_settings(base_dir):
    """Load the shared ``.env`` and derive every setting that depends on it.

    The ORDER is the contract, which is why this is one function and not three
    calls at each call site: the signing key's fallback behaviour depends on
    whether debug is on, so debug has to be resolved first. Restating that
    sequence in each project's ``settings.py`` is exactly how the two copies
    drift apart -- the thing this module exists to prevent.

    Args:
        base_dir: the project's own directory. The ``.env`` is read from its
            parent, since both projects share one file at the repository root.
    """
    load_dotenv(base_dir.parent / ".env")
    debug = debug_enabled()
    return EnvironmentSettings(debug, secret_key(debug=debug), allowed_hosts())
