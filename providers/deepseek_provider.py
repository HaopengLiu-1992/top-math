import requests

from .base import ModelProvider
from settings import secrets

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekProvider(ModelProvider):
    def __init__(
        self,
        model: str = "deepseek-v4-flash",
        base_url: str = DEEPSEEK_BASE_URL,
        thinking_enabled: bool = True,
        reasoning_effort: str = "high",
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.thinking_enabled = thinking_enabled
        self.reasoning_effort = reasoning_effort

    @property
    def name(self) -> str:
        return f"DeepSeek ({self.model})"

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        wants_json = "json" in f"{system}\n{user}".lower()
        # Structured tasks still benefit from reasoning; callers should provide
        # enough output budget for both reasoning and the final JSON response.
        use_thinking = self.thinking_enabled
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "thinking": {"type": "enabled" if use_thinking else "disabled"},
        }
        if use_thinking:
            payload["reasoning_effort"] = self.reasoning_effort
        else:
            payload["temperature"] = 0.3
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
        content = response.json()["choices"][0]["message"].get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("DeepSeek returned an empty response content.")
        return content.strip()
