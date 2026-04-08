import os
import anthropic
from .base import ModelProvider

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


class AnthropicProvider(ModelProvider):
    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.model = model

    @property
    def name(self) -> str:
        return f"Claude ({self.model})"

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        response = _get_client().messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text.strip()
