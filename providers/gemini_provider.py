import time

from google import genai
from google.genai import types
from .base import ModelProvider
from settings import secrets

_client = None
DEFAULT_THINKING_BUDGET = 4000
TRANSIENT_RETRIES = 3
TRANSIENT_BACKOFF_SECONDS = (3, 8, 15)


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=secrets.require_secret("GEMINI_API_KEY"))
    return _client


class GeminiProvider(ModelProvider):
    def __init__(self, model: str = "gemini-3.5-flash"):
        self.model = model

    @property
    def name(self) -> str:
        return f"Gemini ({self.model})"

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        wants_json = "json" in f"{system}\n{user}".lower()
        thinking_budget = min(DEFAULT_THINKING_BUDGET, max_tokens // 3)
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.3,
            max_output_tokens=max_tokens,
            response_mime_type="application/json" if wants_json else None,
            thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
        )

        last_error = None
        for attempt in range(1, TRANSIENT_RETRIES + 1):
            try:
                response = _get_client().models.generate_content(
                    model=self.model,
                    contents=user,
                    config=config,
                )
                break
            except Exception as exc:
                last_error = exc
                if not _is_transient_error(exc) or attempt == TRANSIENT_RETRIES:
                    raise
                delay = TRANSIENT_BACKOFF_SECONDS[attempt - 1]
                print(
                    f"  [Gemini/{self.model}] transient error: {exc}. "
                    f"Retrying in {delay}s ({attempt}/{TRANSIENT_RETRIES})..."
                )
                time.sleep(delay)
        else:
            raise last_error

        return response.text.strip()


def _is_transient_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "503",
            "unavailable",
            "high demand",
            "temporarily",
            "try again later",
            "deadline exceeded",
            "rate limit",
            "resource exhausted",
        )
    )
