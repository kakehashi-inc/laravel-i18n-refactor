"""Ollama provider for local model translations."""

import sys
from typing import List, Dict, Tuple
import ollama
from .base_provider import BaseProvider


class OllamaProvider(BaseProvider):
    """Ollama provider for local model translations."""

    def __init__(self, **kwargs):
        """
        Initialize Ollama provider.

        Args:
            model: Model name (required unless list_models=True)
            api_base: Ollama server URL (optional, or OLLAMA_HOST env var, default: http://localhost:11434)
            temperature: Sampling temperature (optional, or OLLAMA_TEMPERATURE env var)
            max_tokens: Maximum tokens (optional, or OLLAMA_MAX_TOKENS env var)
            num_ctx: Context window size (optional, or OLLAMA_NUM_CTX env var)
            top_p: Nucleus sampling (optional, or OLLAMA_TOP_P env var)
            top_k: Top-k sampling (optional, or OLLAMA_TOP_K env var)
            repeat_penalty: Repetition penalty (optional, or OLLAMA_REPEAT_PENALTY env var)
            list_models: If True, skip validation for model listing
        """
        super().__init__(**kwargs)

        # Model (required)
        self.model = self._get_param("model", "OLLAMA_MODEL", kwargs)
        if not self.model and not kwargs.get("list_models"):
            raise ValueError("Model required (--model or OLLAMA_MODEL env var)")

        # API base URL (optional, with default)
        host = self._get_param("api_base", "OLLAMA_HOST", kwargs, default="http://localhost:11434")
        self.client = ollama.Client(host=host)

        # Build options dictionary
        self.options = {}

        temperature = self._get_float_param("temperature", "OLLAMA_TEMPERATURE", kwargs)
        if temperature is not None:
            self.options["temperature"] = temperature

        max_tokens = self._get_int_param("max_tokens", "OLLAMA_MAX_TOKENS", kwargs)
        if max_tokens is not None:
            self.options["num_predict"] = max_tokens

        num_ctx = self._get_int_param("num_ctx", "OLLAMA_NUM_CTX", kwargs)
        if num_ctx is not None:
            self.options["num_ctx"] = num_ctx

        top_p = self._get_float_param("top_p", "OLLAMA_TOP_P", kwargs)
        if top_p is not None:
            self.options["top_p"] = top_p

        top_k = self._get_int_param("top_k", "OLLAMA_TOP_K", kwargs)
        if top_k is not None:
            self.options["top_k"] = top_k

        repeat_penalty = self._get_float_param("repeat_penalty", "OLLAMA_REPEAT_PENALTY", kwargs)
        if repeat_penalty is not None:
            self.options["repeat_penalty"] = repeat_penalty

    def list_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            response = self.client.list()
            # pylint: disable=no-member
            return [m.model for m in response.models if m.model]  # type: ignore[attr-defined]
        except Exception:  # pylint: disable=broad-except
            # Handle potential API errors
            return []

    def translate_batch(self, items: List[Dict], languages: List[Tuple[str, str]]) -> List[Dict]:
        """Translate items using Ollama."""
        prompt = self.prompt_builder.build_prompt(items, languages)

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options=self.options if self.options else None,
            )

            content = response["response"]
            # Parse XML response
            return self.prompt_builder.parse_xml_responses(content, items, languages)
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error calling Ollama API: {e}", file=sys.stderr)
            return []
