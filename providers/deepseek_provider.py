import requests

from .base import ModelProvider
from settings import secrets

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider(ModelProvider):
    def __init__(
        self,
        model: str = "deepseek-v4-flash",
        base_url: str = DEEPSEEK_BASE_URL,
        thinking_enabled: bool = False,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.thinking_enabled = thinking_enabled

    @property
    def name(self) -> str:
        return f"DeepSeek ({self.model})"

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        wants_json = "json" in f"{system}\n{user}".lower()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "thinking": {"type": "enabled" if self.thinking_enabled else "disabled"},
        }
        if wants_json:
            payload["response_format"] = {"type": "json_object"}

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {secrets.require_secret('DEEPSEEK_API_KEY')}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
