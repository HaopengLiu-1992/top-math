import os
import unittest
from unittest.mock import patch

from settings import secrets


class SecretsTests(unittest.TestCase):
    def test_get_secret_prefers_streamlit_secret(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "from-env"}, clear=False):
            with patch("settings.secrets._get_streamlit_secret", return_value="from-secrets"):
                self.assertEqual(secrets.get_secret("GEMINI_API_KEY"), "from-secrets")

    def test_get_secret_falls_back_to_environment(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "from-env"}, clear=False):
            with patch("settings.secrets._get_streamlit_secret", return_value=None):
                self.assertEqual(secrets.get_secret("GEMINI_API_KEY"), "from-env")

    def test_auth_required_defaults_to_false(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("settings.secrets._get_streamlit_secret", return_value=None):
                self.assertFalse(secrets.auth_required())

    def test_auth_required_parses_truthy_values(self):
        with patch.dict(os.environ, {"AUTH_REQUIRED": "true"}, clear=True):
            with patch("settings.secrets._get_streamlit_secret", return_value=None):
                self.assertTrue(secrets.auth_required())


if __name__ == "__main__":
    unittest.main()
