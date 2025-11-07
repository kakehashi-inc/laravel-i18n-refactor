"""OpenAI-compatible provider for translations."""

import json
import sys
from typing import List, Dict, Tuple
import openai
from .base import TranslationProvider


class OpenAICompatProvider(TranslationProvider):
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
        super().__init__(**kwargs)

        # Model (required)
        self.model = self._get_param("model", "OPENAI_COMPAT_MODEL", kwargs)
        if not self.model and not kwargs.get("list_models"):
            raise ValueError("Model required (--model or OPENAI_COMPAT_MODEL env var)")

        # API base URL (required)
        self.api_base = self._get_param("api_base", "OPENAI_COMPAT_API_BASE", kwargs)
        if not self.api_base:
            raise ValueError("API base URL required (--api-base or OPENAI_COMPAT_API_BASE env var)")

        # API key (optional, some servers don't require it)
        self.api_key = self._get_param("api_key", "OPENAI_COMPAT_API_KEY", kwargs) or "dummy"

        # Initialize client
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.api_base)

        # Generation parameters (optional)
        self.temperature = self._get_float_param("temperature", "OPENAI_COMPAT_TEMPERATURE", kwargs)
        self.max_tokens = self._get_int_param("max_tokens", "OPENAI_COMPAT_MAX_TOKENS", kwargs)

    def list_models(self) -> List[str]:
        """List available models from the endpoint."""
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception as e:
            print(f"Error listing models: {e}", file=sys.stderr)
            print("Note: Some OpenAI-compatible endpoints may not support model listing", file=sys.stderr)
            return []

    def translate_batch(self, items: List[Dict], languages: List[Tuple[str, str]]) -> List[Dict]:
        """Translate items using OpenAI-compatible API."""
        prompt = self.build_prompt(items, languages)

        # Build request parameters
        messages = [
            {"role": "system", "content": "You are a translation assistant for Laravel i18n. Return valid JSON only."},
            {"role": "user", "content": prompt},
        ]

        params = {"model": self.model, "messages": messages}

        # Add optional parameters if provided
        if self.temperature is not None:
            params["temperature"] = self.temperature
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens

        # Try to use JSON mode if supported
        try:
            params["response_format"] = {"type": "json_object"}
        except Exception:
            # Some endpoints may not support JSON mode
            pass

        try:
            response = self.client.chat.completions.create(**params)
            result = json.loads(response.choices[0].message.content)
            return result.get("items", [])
        except json.JSONDecodeError as e:
            print(f"Error parsing response JSON: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Error calling OpenAI-compatible API: {e}", file=sys.stderr)
            return []
