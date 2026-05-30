from providers.base import ModelProvider


def get_default_provider() -> ModelProvider:
    from providers.gemini_provider import GeminiProvider

    return GeminiProvider()
