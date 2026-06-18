import os
import unittest
from unittest.mock import Mock, patch

from providers.deepseek_provider import DeepSeekProvider


class DeepSeekProviderTests(unittest.TestCase):
    def test_complete_sends_openai_compatible_request(self):
        response = Mock()
        response.json.return_value = {
            "choices": [
                {"message": {"content": '{"status":"ok"}'}}
            ]
        }

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
            with patch("settings.secrets._get_streamlit_secret", return_value=None):
                with patch("providers.deepseek_provider.requests.post", return_value=response) as post:
                    result = DeepSeekProvider().complete(
                        "Return JSON only.",
                        'Return {"status":"ok"}',
                        max_tokens=123,
                    )

        self.assertEqual(result, '{"status":"ok"}')
        response.raise_for_status.assert_called_once()
        post.assert_called_once()

        _, kwargs = post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], "deepseek-v4-flash")
        self.assertEqual(kwargs["json"]["max_tokens"], 123)
        self.assertEqual(kwargs["json"]["thinking"], {"type": "enabled"})
        self.assertEqual(kwargs["json"]["reasoning_effort"], "high")
        self.assertNotIn("temperature", kwargs["json"])
        self.assertEqual(kwargs["json"]["response_format"], {"type": "json_object"})

    def test_non_thinking_mode_uses_temperature(self):
        response = Mock()
        response.json.return_value = {
            "choices": [
                {"message": {"content": "OK"}}
            ]
        }

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
            with patch("settings.secrets._get_streamlit_secret", return_value=None):
                with patch("providers.deepseek_provider.requests.post", return_value=response) as post:
                    result = DeepSeekProvider(thinking_enabled=False).complete(
                        "Reply plainly.",
                        "Say OK.",
                        max_tokens=123,
                    )

        self.assertEqual(result, "OK")
        _, kwargs = post.call_args
        self.assertEqual(kwargs["json"]["thinking"], {"type": "disabled"})
        self.assertEqual(kwargs["json"]["temperature"], 0.3)
        self.assertNotIn("reasoning_effort", kwargs["json"])


if __name__ == "__main__":
    unittest.main()
