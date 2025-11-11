"""OpenAI provider for translations."""

import sys
from typing import List, Dict, Tuple
import openai
from .base_provider import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI GPT provider for translations."""

    def __init__(self, **kwargs):
        """
        Initialize OpenAI provider.

        Args:
            model: Model name (required unless list_models=True)
            api_key: OpenAI API key (or OPENAI_API_KEY env var)
            organization: Organization ID (optional, or OPENAI_ORGANIZATION env var)
            temperature: Sampling temperature (optional, or OPENAI_TEMPERATURE env var)
            max_tokens: Maximum tokens (optional, or OPENAI_MAX_TOKENS env var)
            list_models: If True, skip validation for model listing
        """
        super().__init__(**kwargs)

        # Model (required)
        self.model = self._get_param("model", "OPENAI_MODEL", kwargs)
        if not self.model and not kwargs.get("list_models"):
            raise ValueError("Model required (--model or OPENAI_MODEL env var)")

        # API key (required)
        self.api_key = self._get_param("api_key", "OPENAI_API_KEY", kwargs)
        if not self.api_key and not kwargs.get("list_models"):
            raise ValueError("API key required (--api-key or OPENAI_API_KEY env var)")

        # Initialize client
        self.client = openai.OpenAI(api_key=self.api_key)

        # Organization (optional)
        self.organization = self._get_param("organization", "OPENAI_ORGANIZATION", kwargs)

        # Generation parameters (optional)
        self.temperature = self._get_float_param("temperature", "OPENAI_TEMPERATURE", kwargs)
        self.max_tokens = self._get_int_param("max_tokens", "OPENAI_MAX_TOKENS", kwargs)

    def list_models(self) -> List[str]:
        """List available GPT models."""
        try:
            models = self.client.models.list()
            if models.data is None:
                return []
            return [model.id for model in models.data]
        except Exception:  # pylint: disable=broad-except
            # Handle potential API errors
            return []

    def translate_batch(self, items: List[Dict], languages: List[Tuple[str, str]]) -> List[Dict]:
        """Translate items using OpenAI API."""
        prompt = self.prompt_builder.build_prompt(items, languages)

        # Build request parameters
        messages = [
            {"role": "system", "content": "You are a translation assistant for Laravel i18n."},
            {"role": "user", "content": prompt},
        ]

        params = {"model": self.model, "messages": messages}

        # Add optional parameters if provided
        if self.temperature is not None:
            params["temperature"] = self.temperature
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens

        try:
            response = self.client.chat.completions.create(**params)
            content = response.choices[0].message.content
            # Parse XML response
            return self.prompt_builder.parse_xml_responses(content, items, languages)
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error calling OpenAI API: {e}", file=sys.stderr)
            return []
