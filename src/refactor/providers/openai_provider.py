"""OpenAI provider for translations."""

import os
import json
import sys
from typing import List, Dict, Tuple
import openai
from .base import TranslationProvider


class OpenAIProvider(TranslationProvider):
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
            batch_size: Batch size (optional, or OPENAI_BATCH_SIZE env var, default: 10)
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
        self.batch_size = self._get_int_param("batch_size", "OPENAI_BATCH_SIZE", kwargs, default=10)

    def list_models(self) -> List[str]:
        """List available GPT models."""
        try:
            models = self.client.models.list()
            # Filter GPT models
            gpt_models = [m.id for m in models.data if "gpt" in m.id.lower()]
            return sorted(gpt_models)
        except Exception as e:
            print(f"Error listing models: {e}", file=sys.stderr)
            return []

    def translate_batch(self, items: List[Dict], languages: List[Tuple[str, str]]) -> List[Dict]:
        """Translate items using OpenAI API."""
        prompt = self.build_prompt(items, languages)

        # Build request parameters
        messages = [
            {"role": "system", "content": "You are a translation assistant for Laravel i18n. Return valid JSON only."},
            {"role": "user", "content": prompt},
        ]

        params = {"model": self.model, "messages": messages, "response_format": {"type": "json_object"}}

        # Add optional parameters if provided
        if self.temperature is not None:
            params["temperature"] = self.temperature
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens

        try:
            response = self.client.chat.completions.create(**params)
            result = json.loads(response.choices[0].message.content)
            return result.get("items", [])
        except json.JSONDecodeError as e:
            print(f"Error parsing response JSON: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Error calling OpenAI API: {e}", file=sys.stderr)
            return []
