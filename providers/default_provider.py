from providers.base import ModelProvider
from providers.gemini_provider import GeminiProvider


def get_default_provider() -> ModelProvider:
    return GeminiProvider()
