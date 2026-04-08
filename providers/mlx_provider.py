import requests
from .base import ModelProvider

MLX_SERVER_URL = "http://localhost:8080"


def is_available() -> bool:
    try:
        r = requests.get(f"{MLX_SERVER_URL}/v1/models", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


class MLXProvider(ModelProvider):
    def __init__(self, server_url: str = MLX_SERVER_URL, max_tokens: int = 4000):
        self.server_url = server_url
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return "Local MLX (Qwen3.5-9B)"

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        response = requests.post(
            f"{self.server_url}/v1/chat/completions",
            json={
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
                "top_p": 0.9,
                "extra_body": {"thinking": False},  # skip reasoning trace
            },
            timeout=300,
        )
        response.raise_for_status()
        msg = response.json()["choices"][0]["message"]
        return (msg.get("content") or msg.get("reasoning", "")).strip()
