"""Anthropic Claude provider for translations."""

import json
import sys
from typing import List, Dict, Tuple
import anthropic
from .base import TranslationProvider


class ClaudeProvider(TranslationProvider):
    """Anthropic Claude provider for translations."""

    def __init__(self, **kwargs):
        """
        Initialize Claude provider.

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
        # Claude requires max_tokens, set default
        self.max_tokens = self._get_int_param("max_tokens", "ANTHROPIC_MAX_TOKENS", kwargs, default=4096)

    def list_models(self) -> List[str]:
        """List available Claude models."""
        # Anthropic API doesn't provide model listing endpoint
        return ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-2.1", "claude-2.0", "claude-instant-1.2"]

    def translate_batch(self, items: List[Dict], languages: List[Tuple[str, str]]) -> List[Dict]:
        """Translate items using Claude API."""
        prompt = self.build_prompt(items, languages)

        # Build request parameters
        params = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": self.max_tokens}

        # Add optional parameters if provided
        if self.temperature is not None:
            params["temperature"] = self.temperature

        try:
            response = self.client.messages.create(**params)
            # Claude returns text content
            content = response.content[0].text
            result = json.loads(content)
            return result.get("items", [])
        except json.JSONDecodeError as e:
            print(f"Error parsing response JSON: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Error calling Claude API: {e}", file=sys.stderr)
            return []
