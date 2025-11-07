"""Anthropic-compatible provider for translations (e.g., MiniMax M2)."""

import json
import sys
from typing import List, Dict, Tuple
import anthropic
from .base import TranslationProvider


class AnthropicCompatProvider(TranslationProvider):
    """Anthropic-compatible API provider (MiniMax M2, etc.)."""

    def __init__(self, **kwargs):
        """
        Initialize Anthropic-compatible provider.

        Args:
            model: Model name (required unless list_models=True)
            api_base: API base URL (required, or ANTHROPIC_COMPAT_API_BASE env var)
            api_key: API key (required, or ANTHROPIC_COMPAT_API_KEY env var)
            temperature: Sampling temperature (optional, or ANTHROPIC_COMPAT_TEMPERATURE env var)
            max_tokens: Maximum tokens (optional, or ANTHROPIC_COMPAT_MAX_TOKENS env var, default: 4096)
            list_models: If True, skip validation for model listing
        """
        super().__init__(**kwargs)

        # Model (required)
        self.model = self._get_param("model", "ANTHROPIC_COMPAT_MODEL", kwargs)
        if not self.model and not kwargs.get("list_models"):
            raise ValueError("Model required (--model or ANTHROPIC_COMPAT_MODEL env var)")

        # API base URL (required)
        self.api_base = self._get_param("api_base", "ANTHROPIC_COMPAT_API_BASE", kwargs)
        if not self.api_base:
            raise ValueError("API base URL required (--api-base or ANTHROPIC_COMPAT_API_BASE env var)")

        # API key (required)
        self.api_key = self._get_param("api_key", "ANTHROPIC_COMPAT_API_KEY", kwargs)
        if not self.api_key and not kwargs.get("list_models"):
            raise ValueError("API key required (--api-key or ANTHROPIC_COMPAT_API_KEY env var)")

        # Initialize client with custom base URL
        self.client = anthropic.Anthropic(api_key=self.api_key, base_url=self.api_base)

        # Generation parameters
        self.temperature = self._get_float_param("temperature", "ANTHROPIC_COMPAT_TEMPERATURE", kwargs)
        # Anthropic API requires max_tokens, set default
        self.max_tokens = self._get_int_param("max_tokens", "ANTHROPIC_COMPAT_MAX_TOKENS", kwargs, default=4096)

    def list_models(self) -> List[str]:
        """List available models from the endpoint."""
        # Most Anthropic-compatible endpoints don't provide model listing
        # Return common known models for reference
        print("Note: Model listing may not be supported by all Anthropic-compatible endpoints", file=sys.stderr)
        return ["abab7-chat-preview", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]

    def translate_batch(self, items: List[Dict], languages: List[Tuple[str, str]]) -> List[Dict]:
        """Translate items using Anthropic-compatible API."""
        prompt = self.build_prompt(items, languages)

        # Build request parameters
        params = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": self.max_tokens}

        # Add optional parameters if provided
        if self.temperature is not None:
            params["temperature"] = self.temperature

        try:
            response = self.client.messages.create(**params)
            # Anthropic API returns text content
            content = response.content[0].text
            result = json.loads(content)
            return result.get("items", [])
        except json.JSONDecodeError as e:
            print(f"Error parsing response JSON: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Error calling Anthropic-compatible API: {e}", file=sys.stderr)
            return []
