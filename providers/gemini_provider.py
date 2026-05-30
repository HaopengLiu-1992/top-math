import os
from google import genai
from google.genai import types
from .base import ModelProvider

_client = None
DEFAULT_THINKING_BUDGET = 512


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


class GeminiProvider(ModelProvider):
    def __init__(self, model: str = "gemini-3.5-flash"):
        self.model = model

    @property
    def name(self) -> str:
        return f"Gemini ({self.model})"

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        wants_json = "json" in f"{system}\n{user}".lower()
        thinking_budget = min(DEFAULT_THINKING_BUDGET, max_tokens // 4)
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.3,
            max_output_tokens=max_tokens,
            response_mime_type="application/json" if wants_json else None,
            thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
        )

        response = _get_client().models.generate_content(
            model=self.model,
            contents=user,
            config=config,
        )
        return response.text.strip()
