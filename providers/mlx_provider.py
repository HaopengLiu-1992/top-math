import requests
from .base import ModelProvider

MLX_SERVER_URL = "http://localhost:8000"


def is_available() -> bool:
    try:
        r = requests.get(f"{MLX_SERVER_URL}/health", timeout=2)
        return r.status_code == 200 and r.json().get("status") == "ok"
    except Exception:
        return False


class MLXProvider(ModelProvider):
    def __init__(self, server_url: str = MLX_SERVER_URL, max_tokens: int = 4000):
        self.server_url = server_url
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return "Local MLX (Qwen)"

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        # Combine system + user into a single prompt since the MLX server
        # takes a plain prompt string
        combined = f"{system}\n\n{user}"

        response = requests.post(
            f"{self.server_url}/stream",
            json={
                "prompt": combined,
                "max_tokens": max_tokens,
                "temp": 0.3,   # lower temp for more deterministic JSON output
                "top_p": 0.9,
            },
            stream=True,
            timeout=120,
        )
        response.raise_for_status()

        chunks = []
        for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                chunks.append(chunk)

        return "".join(chunks).strip()
