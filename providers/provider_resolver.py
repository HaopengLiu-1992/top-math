from providers.base import ModelProvider


def resolve_provider(choice: str) -> ModelProvider:
    if choice.startswith("Local"):
        from providers.mlx_provider import MLXProvider
        return MLXProvider()
    if choice.startswith("DeepSeek"):
        from providers.deepseek_provider import DeepSeekProvider
        return DeepSeekProvider()
    if choice.startswith("Gemini"):
        from providers.gemini_provider import GeminiProvider
        return GeminiProvider()
    from providers.anthropic_provider import AnthropicProvider
    return AnthropicProvider()
