"""Google Gemini provider for translations."""

import sys
from typing import List, Dict, Tuple
import google.generativeai as genai
from .base import TranslationProvider


class GeminiProvider(TranslationProvider):
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
            import os

            self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not self.api_key and not kwargs.get("list_models"):
            raise ValueError("API key required (--api-key or GEMINI_API_KEY/GOOGLE_API_KEY env var)")

        # Configure API
        if self.api_key:
            genai.configure(api_key=self.api_key)  # type: ignore

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
        try:
            models = genai.list_models()  # type: ignore
            # Filter models that support generateContent
            return [m.name.replace("models/", "") for m in models if "generateContent" in m.supported_generation_methods]
        except (ValueError, RuntimeError, ConnectionError) as e:
            print(f"Error listing models: {e}", file=sys.stderr)
            return []

    def translate_batch(self, items: List[Dict], languages: List[Tuple[str, str]]) -> List[Dict]:
        """Translate items using Gemini API."""
        prompt = self.build_prompt(items, languages)

        try:
            # Convert dict to proper GenerationConfig if needed
            generation_config = self.generation_config if self.generation_config else None
            model = genai.GenerativeModel(model_name=self.model, generation_config=generation_config)  # type: ignore

            response = model.generate_content(prompt)

            # Extract response text
            content = response.text.strip()
            # Parse XML response
            return self.parse_xml_responses(content, items, languages)
        except (ValueError, RuntimeError, ConnectionError) as e:
            print(f"Error calling Gemini API: {e}", file=sys.stderr)
            return []
