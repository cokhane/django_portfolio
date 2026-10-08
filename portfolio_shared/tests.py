"""Tests for the shared environment-settings helpers."""

import os
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from portfolio_shared.env import (
    DEV_SECRET_KEY,
    allowed_hosts,
    debug_enabled,
    environment_settings,
    secret_key,
)


class DebugEnabledTests(SimpleTestCase):
    """Debug must be opt-in, never the default."""

    @patch.dict(os.environ, {}, clear=True)
    def test_defaults_to_off(self):
        """An unset DJANGO_DEBUG means debug is off."""
        self.assertFalse(debug_enabled())

    @patch.dict(os.environ, {"DJANGO_DEBUG": "1"})
    def test_enabled_by_explicit_opt_in(self):
        """DJANGO_DEBUG=1 turns debug on."""
        self.assertTrue(debug_enabled())

    @patch.dict(os.environ, {"DJANGO_DEBUG": "true"})
    def test_only_the_literal_one_enables_it(self):
        """Any other value leaves debug off rather than guessing."""
        self.assertFalse(debug_enabled())


class SecretKeyTests(SimpleTestCase):
    """The signing key must never silently fall back in production."""

    @patch.dict(os.environ, {"DJANGO_SECRET_KEY": "a-real-key"})
    def test_returns_the_configured_key(self):
        """A configured key is used as-is."""
        self.assertEqual(secret_key(debug=False), "a-real-key")

    @patch.dict(os.environ, {}, clear=True)
    def test_refuses_to_start_without_a_key_when_debug_is_off(self):
        """Production without a key raises instead of using the dev literal."""
        with self.assertRaises(ImproperlyConfigured):
            secret_key(debug=False)

    @patch.dict(os.environ, {}, clear=True)
    def test_falls_back_only_in_debug(self):
        """Local development still works with no configuration."""
        self.assertEqual(secret_key(debug=True), DEV_SECRET_KEY)


class AllowedHostsTests(SimpleTestCase):
    """The host allowlist is loopback-only until configured."""

    @patch.dict(os.environ, {}, clear=True)
    def test_defaults_to_loopback(self):
        """No configuration means only local hosts are served."""
        self.assertEqual(allowed_hosts(), ["127.0.0.1", "localhost"])

    @patch.dict(os.environ, {"DJANGO_ALLOWED_HOSTS": "a.com, b.com ,"})
    def test_splits_and_strips_entries(self):
        """Whitespace and empty entries are discarded."""
        self.assertEqual(allowed_hosts(), ["a.com", "b.com"])


class EnvironmentSettingsTests(SimpleTestCase):
    """The three settings are derived together, so they cannot drift apart."""

    @patch.dict(os.environ, {"DJANGO_DEBUG": "1"}, clear=True)
    @patch("portfolio_shared.env.load_dotenv")
    def test_derives_all_three_from_the_environment(self, _load):
        """One call yields debug, the key and the hosts."""
        settings = environment_settings(Path("/srv/app/backend"))

        self.assertTrue(settings.debug)
        self.assertEqual(settings.secret_key, DEV_SECRET_KEY)
        self.assertEqual(settings.allowed_hosts, ["127.0.0.1", "localhost"])

    @patch.dict(os.environ, {"DJANGO_DEBUG": "1"}, clear=True)
    @patch("portfolio_shared.env.load_dotenv")
    def test_reads_the_env_file_beside_the_project(self, load):
        """Both projects share one .env, one level above each of them."""
        environment_settings(Path("/srv/app/backend"))

        load.assert_called_once_with(Path("/srv/app/.env"))

    @patch.dict(os.environ, {}, clear=True)
    @patch("portfolio_shared.env.load_dotenv")
    def test_the_key_is_derived_from_the_resolved_debug_value(self, _load):
        """Debug off with no key must raise rather than sign with the literal.

        This is the ordering that made the block worth owning here: the key's
        fallback depends on debug, so debug has to be resolved first. Stated
        once, it cannot be got wrong in only one of the two projects.
        """
        with self.assertRaises(ImproperlyConfigured):
            environment_settings(Path("/srv/app/backend"))

    @patch.dict(os.environ, {"DJANGO_DEBUG": "1"}, clear=True)
    @patch("portfolio_shared.env.load_dotenv")
    def test_unpacks_in_the_order_settings_modules_expect(self, _load):
        """Both settings modules unpack positionally; the order is the API."""
        debug, key, hosts = environment_settings(Path("/srv/app/backend"))

        self.assertEqual((debug, key, hosts),
                         (True, DEV_SECRET_KEY, ["127.0.0.1", "localhost"]))
