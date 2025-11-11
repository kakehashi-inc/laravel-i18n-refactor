"""Anthropic provider for translations."""

import sys
from typing import List, Dict, Tuple
import anthropic
from anthropic.types import TextBlock
from .base_provider import BaseProvider


class AnthropicProvider(BaseProvider):
    """Anthropic provider for translations."""

    def __init__(self, **kwargs):
        """
        Initialize Anthropic provider.

        Args:
            model: Model name (required unless list_models=True)
            api_key: Anthropic API key (or ANTHROPIC_API_KEY env var)
            temperature: Sampling temperature (optional, or ANTHROPIC_TEMPERATURE env var)
            max_tokens: Maximum tokens (optional, or ANTHROPIC_MAX_TOKENS env var, default: 4096)
            list_models: If True, skip validation for model listing
        """
        super().__init__(**kwargs)

        # Model (required)
        self.model = self._get_param("model", "ANTHROPIC_MODEL", kwargs)
        if not self.model and not kwargs.get("list_models"):
            raise ValueError("Model required (--model or ANTHROPIC_MODEL env var)")

        # API key (required)
        self.api_key = self._get_param("api_key", "ANTHROPIC_API_KEY", kwargs)
        if not self.api_key and not kwargs.get("list_models"):
            raise ValueError("API key required (--api-key or ANTHROPIC_API_KEY env var)")

        # Initialize client
        self.client = anthropic.Anthropic(api_key=self.api_key)

        # Generation parameters
        self.temperature = self._get_float_param("temperature", "ANTHROPIC_TEMPERATURE", kwargs)
        # Anthropic requires max_tokens, set default
        self.max_tokens = self._get_int_param("max_tokens", "ANTHROPIC_MAX_TOKENS", kwargs, default=4096)

    def list_models(self) -> List[str]:
        """List available Anthropic models."""
        try:
            models = self.client.models.list()
            if models.data is None:
                return []
            return [model.id for model in models.data]
        except Exception:  # pylint: disable=broad-except
            # Handle potential API errors
            return []

    def translate_batch(self, items: List[Dict], languages: List[Tuple[str, str]]) -> List[Dict]:
        """Translate items using Anthropic API."""
        prompt = self.prompt_builder.build_prompt(items, languages)

        # Build request parameters
        params = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Add optional parameters if provided
        if self.temperature is not None:
            params["temperature"] = self.temperature

        try:
            response = self.client.messages.create(**params)

            # Extract translation from response content
            # Handle both TextBlock and ThinkingBlock (newer models may include thinking process)
            content_text = ""
            for content_block in response.content:
                if isinstance(content_block, TextBlock):
                    content_text = content_block.text
                    break  # Use the first text block
                # Skip other types (e.g., ThinkingBlock)
                continue

            if not content_text:
                print("Error: No text content found in Anthropic API response", file=sys.stderr)
                return []

            # Parse XML response
            return self.prompt_builder.parse_xml_responses(content_text, items, languages)
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error calling Anthropic API: {e}", file=sys.stderr)
            return []
