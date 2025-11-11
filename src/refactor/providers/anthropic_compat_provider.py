"""Anthropic-compatible provider for translations (e.g., MiniMax M2)."""

from typing import List
import anthropic
from .anthropic_provider import AnthropicProvider


class AnthropicCompatProvider(AnthropicProvider):
    """Anthropic-compatible API provider (MiniMax M2, etc.)."""

    def __init__(self, **kwargs):
        """
        Initialize Anthropic-compatible provider.

        Args:
            model: Model name (required unless list_models=True)
            api_base: API base URL (required, or ANTHROPIC_COMPAT_API_BASE env var)
            api_key: API key (optional for some services, or ANTHROPIC_COMPAT_API_KEY env var)
            temperature: Sampling temperature (optional, or ANTHROPIC_COMPAT_TEMPERATURE env var)
            max_tokens: Maximum tokens (optional, or ANTHROPIC_COMPAT_MAX_TOKENS env var, default: 4096)
            list_models: If True, skip validation for model listing
        """
        # Don't call parent __init__ yet as we need to override client initialization
        # Call grandparent (BaseProvider) __init__ instead
        # pylint: disable=bad-super-call
        super(AnthropicProvider, self).__init__(**kwargs)

        # Model (required)
        self.model = self._get_param("model", "ANTHROPIC_COMPAT_MODEL", kwargs)
        if not self.model and not kwargs.get("list_models"):
            raise ValueError("Model required (--model or ANTHROPIC_COMPAT_MODEL env var)")

        # API base URL (required)
        self.api_base = self._get_param("api_base", "ANTHROPIC_COMPAT_API_BASE", kwargs)
        if not self.api_base:
            raise ValueError("API base URL required (--api-base or ANTHROPIC_COMPAT_API_BASE env var)")

        # API key (optional for some services)
        # If not provided, use a dummy key to ensure compatibility
        self.api_key = self._get_param("api_key", "ANTHROPIC_COMPAT_API_KEY", kwargs)
        if not self.api_key:
            self.api_key = "sk-ant-no-key-required"

        # Initialize client with custom base URL
        self.client = anthropic.Anthropic(api_key=self.api_key, base_url=self.api_base)

        # Generation parameters
        self.temperature = self._get_float_param("temperature", "ANTHROPIC_COMPAT_TEMPERATURE", kwargs)
        # Anthropic API requires max_tokens, set default
        self.max_tokens = self._get_int_param("max_tokens", "ANTHROPIC_COMPAT_MAX_TOKENS", kwargs, default=4096)

    def list_models(self) -> List[str]:
        """List available models from the endpoint."""
        try:
            models = self.client.models.list()
            if models.data is None:
                return []
            return [model.id for model in models.data]
        except Exception:  # pylint: disable=broad-except
            # Most Anthropic-compatible endpoints don't provide model listing
            # Return empty list as fallback
            return []
