from providers.base import ModelProvider


def get_default_provider() -> ModelProvider:
    from providers.deepseek_provider import DeepSeekProvider

    return DeepSeekProvider()
