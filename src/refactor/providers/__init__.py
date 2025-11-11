"""AI providers for translation."""

from .base_provider import BaseProvider


def get_provider(provider_name: str, **kwargs) -> BaseProvider:
    """
    Factory function to get provider instance.

    Args:
        provider_name: Name of the provider ('openai', 'claude', 'gemini', 'openai-compat', 'ollama')
        **kwargs: Provider-specific arguments

    Returns:
        Provider instance

    Raises:
        ValueError: If provider name is unknown
        ImportError: If provider library is not installed
    """
    if provider_name == "openai":
        try:
            from .openai_provider import OpenAIProvider

            return OpenAIProvider(**kwargs)
        except ImportError as e:
            raise ImportError("OpenAI provider requires 'openai' library. Install with: pip install 'laravel-i18n-refactor[translate-openai]'") from e

    elif provider_name == "anthropic":
        try:
            from .anthropic_provider import AnthropicProvider

            return AnthropicProvider(**kwargs)
        except ImportError as e:
            raise ImportError("Anthropic provider requires 'anthropic' library. Install with: pip install 'laravel-i18n-refactor[translate-claude]'") from e

    elif provider_name == "gemini":
        try:
            from .gemini_provider import GeminiProvider

            return GeminiProvider(**kwargs)
        except ImportError as e:
            raise ImportError("Gemini provider requires 'google-genai' library. Install with: pip install 'laravel-i18n-refactor[translate-gemini]'") from e

    elif provider_name == "openai-compat":
        try:
            from .openai_compat_provider import OpenAICompatProvider

            return OpenAICompatProvider(**kwargs)
        except ImportError as e:
            raise ImportError(
                "OpenAI-compatible provider requires 'openai' library. Install with: pip install 'laravel-i18n-refactor[translate-openai]'"
            ) from e

    elif provider_name == "ollama":
        try:
            from .ollama_provider import OllamaProvider

            return OllamaProvider(**kwargs)
        except ImportError as e:
            raise ImportError("Ollama provider requires 'ollama' library. Install with: pip install 'laravel-i18n-refactor[translate-ollama]'") from e

    elif provider_name == "anthropic-compat":
        try:
            from .anthropic_compat_provider import AnthropicCompatProvider

            return AnthropicCompatProvider(**kwargs)
        except ImportError as e:
            raise ImportError(
                "Anthropic-compatible provider requires 'anthropic' library. Install with: pip install 'laravel-i18n-refactor[translate-claude]'"
            ) from e

    else:
        raise ValueError(f"Unknown provider: {provider_name}")


__all__ = ["get_provider", "BaseProvider"]
