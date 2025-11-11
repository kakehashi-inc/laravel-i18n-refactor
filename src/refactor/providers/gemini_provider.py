"""Google Gemini provider for translations."""

import os
import sys
from typing import List, Dict, Tuple
from google import genai
from google.genai import types
from .base_provider import BaseProvider


class GeminiProvider(BaseProvider):
    """Google Gemini provider for translations."""

    def __init__(self, **kwargs):
        """
        Initialize Gemini provider.

        Args:
            model: Model name (required unless list_models=True)
            api_key: Google API key (or GOOGLE_API_KEY/GEMINI_API_KEY env var)
            temperature: Sampling temperature (optional, or GEMINI_TEMPERATURE env var)
            max_tokens: Maximum output tokens (optional, or GEMINI_MAX_TOKENS env var)
            top_p: Nucleus sampling parameter (optional, or GEMINI_TOP_P env var)
            top_k: Top-k sampling parameter (optional, or GEMINI_TOP_K env var)
            list_models: If True, skip validation for model listing
        """
        super().__init__(**kwargs)

        # Model (required)
        self.model = self._get_param("model", "GEMINI_MODEL", kwargs)
        if not self.model and not kwargs.get("list_models"):
            raise ValueError("Model required (--model or GEMINI_MODEL env var)")

        # API key (required) - try both GEMINI_API_KEY and GOOGLE_API_KEY
        self.api_key = kwargs.get("api_key")
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not self.api_key and not kwargs.get("list_models"):
            raise ValueError("API key required (--api-key or GEMINI_API_KEY/GOOGLE_API_KEY env var)")

        # Initialize client
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

        # Generation config
        self.generation_config = {}

        temperature = self._get_float_param("temperature", "GEMINI_TEMPERATURE", kwargs)
        if temperature is not None:
            self.generation_config["temperature"] = temperature

        max_tokens = self._get_int_param("max_tokens", "GEMINI_MAX_TOKENS", kwargs)
        if max_tokens is not None:
            self.generation_config["max_output_tokens"] = max_tokens

        top_p = self._get_float_param("top_p", "GEMINI_TOP_P", kwargs)
        if top_p is not None:
            self.generation_config["top_p"] = top_p

        top_k = self._get_int_param("top_k", "GEMINI_TOP_K", kwargs)
        if top_k is not None:
            self.generation_config["top_k"] = top_k

    def list_models(self) -> List[str]:
        """List available Gemini models."""
        if not self.client:
            return []
        try:
            # List models that support generateContent
            models = list(self.client.models.list())
            result = []
            for m in models:
                if hasattr(m, "name") and m.name:
                    # Convert model name to string and remove 'models/' prefix
                    if isinstance(m.name, str):
                        model_name = m.name.replace("models/", "")
                    else:
                        model_name = str(m.name)
                    supported_methods = getattr(m, "supported_generation_methods", [])
                    if supported_methods and "generateContent" in supported_methods:
                        result.append(model_name)
            return result
        except Exception:  # pylint: disable=broad-except
            # Handle potential API errors
            return []

    def translate_batch(self, items: List[Dict], languages: List[Tuple[str, str]]) -> List[Dict]:
        """Translate items using Gemini API."""
        if not self.client:
            print("Error: Gemini client not initialized", file=sys.stderr)
            return []

        prompt = self.prompt_builder.build_prompt(items, languages)

        try:
            # Build generation config
            if self.generation_config:
                config = types.GenerateContentConfig(**self.generation_config)
            else:
                config = None

            # Use client.models.generate_content
            response = self.client.models.generate_content(model=self.model, contents=prompt, config=config)

            # Extract response text
            if not response.text:
                print("Error: No text in response", file=sys.stderr)
                return []

            content = response.text.strip()
            # Parse XML response
            return self.prompt_builder.parse_xml_responses(content, items, languages)
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error calling Gemini API: {e}", file=sys.stderr)
            return []
