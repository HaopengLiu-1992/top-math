import os
from google import genai
from google.genai import types
from .base import ModelProvider

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


class GeminiProvider(ModelProvider):
    def __init__(self, model: str = "gemini-3.1-flash-lite-preview"):
        self.model = model

    @property
    def name(self) -> str:
        return f"Gemini ({self.model})"

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        response = _get_client().models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.3,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text.strip()
