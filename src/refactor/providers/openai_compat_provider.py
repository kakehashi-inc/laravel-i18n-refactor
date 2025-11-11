"""OpenAI-compatible provider for translations."""

from typing import List
import openai
from .openai_provider import OpenAIProvider


class OpenAICompatProvider(OpenAIProvider):
    """OpenAI-compatible API provider (LM Studio, LocalAI, etc.)."""

    def __init__(self, **kwargs):
        """
        Initialize OpenAI-compatible provider.

        Args:
            model: Model name (required unless list_models=True)
            api_base: API base URL (required, or OPENAI_COMPAT_API_BASE env var)
            api_key: API key (optional, or OPENAI_COMPAT_API_KEY env var)
            temperature: Sampling temperature (optional, or OPENAI_COMPAT_TEMPERATURE env var)
            max_tokens: Maximum tokens (optional, or OPENAI_COMPAT_MAX_TOKENS env var)
            list_models: If True, skip validation for model listing
        """
        # Don't call parent __init__ yet as we need to override client initialization
        # Call grandparent (BaseProvider) __init__ instead
        # pylint: disable=bad-super-call
        super(OpenAIProvider, self).__init__(**kwargs)

        # Model (required)
        self.model = self._get_param("model", "OPENAI_COMPAT_MODEL", kwargs)
        if not self.model and not kwargs.get("list_models"):
            raise ValueError("Model required (--model or OPENAI_COMPAT_MODEL env var)")

        # API base URL (required)
        self.api_base = self._get_param("api_base", "OPENAI_COMPAT_API_BASE", kwargs)
        if not self.api_base:
            raise ValueError("API base URL required (--api-base or OPENAI_COMPAT_API_BASE env var)")

        # API key (optional, some servers don't require it)
        # If not provided, use a dummy key to bypass OpenAI client validation
        self.api_key = self._get_param("api_key", "OPENAI_COMPAT_API_KEY", kwargs)
        if not self.api_key:
            self.api_key = "sk-no-key-required"

        # Initialize client
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.api_base)

        # Organization (optional)
        self.organization = None

        # Generation parameters (optional)
        self.temperature = self._get_float_param("temperature", "OPENAI_COMPAT_TEMPERATURE", kwargs)
        self.max_tokens = self._get_int_param("max_tokens", "OPENAI_COMPAT_MAX_TOKENS", kwargs)

    def list_models(self) -> List[str]:
        """List available models from the endpoint."""
        try:
            models = self.client.models.list()
            if models.data is None:
                return []
            return [model.id for model in models.data]
        except Exception:  # pylint: disable=broad-except
            # Some OpenAI-compatible endpoints may not support model listing
            return []
