"""Base class for AI translation providers."""

import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import json


class TranslationProvider(ABC):
    """Base class for AI translation providers."""

    def __init__(self, **kwargs):
        """
        Initialize provider with configuration.

        Args:
            **kwargs: Provider-specific configuration including:
                - model: Model name
                - api_key: API key
                - list_models: Boolean flag for model listing mode
                - Other provider-specific parameters
        """
        self.kwargs = kwargs

    def _get_param(self, key: str, env_var: str, kwargs: dict, default: Any = None) -> Any:
        """
        Get parameter with priority: CLI argument > environment variable > default.

        Args:
            key: Parameter key in kwargs
            env_var: Environment variable name
            kwargs: Keyword arguments dictionary
            default: Default value if neither arg nor env var is set

        Returns:
            Parameter value
        """
        # コマンドライン引数を優先
        if key in kwargs and kwargs[key] is not None:
            return kwargs[key]

        # 環境変数にフォールバック
        env_value = os.getenv(env_var)
        if env_value is not None:
            return env_value

        # デフォルト値を返す
        return default

    def _get_int_param(self, key: str, env_var: str, kwargs: dict, default: Optional[int] = None) -> Optional[int]:
        """
        Get integer parameter with type conversion.

        Args:
            key: Parameter key in kwargs
            env_var: Environment variable name
            kwargs: Keyword arguments dictionary
            default: Default value

        Returns:
            Integer parameter value or None
        """
        value = self._get_param(key, env_var, kwargs, None)
        if value is not None:
            try:
                return int(value)
            except (ValueError, TypeError):
                pass
        return default

    def _get_float_param(self, key: str, env_var: str, kwargs: dict, default: Optional[float] = None) -> Optional[float]:
        """
        Get float parameter with type conversion.

        Args:
            key: Parameter key in kwargs
            env_var: Environment variable name
            kwargs: Keyword arguments dictionary
            default: Default value

        Returns:
            Float parameter value or None
        """
        value = self._get_param(key, env_var, kwargs, None)
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
        return default

    @abstractmethod
    def list_models(self) -> List[str]:
        """
        List available models for this provider.

        Returns:
            List of model names
        """
        raise NotImplementedError

    @abstractmethod
    def translate_batch(self, items: List[Dict], languages: List[Tuple[str, str]]) -> List[Dict]:
        """
        Translate a batch of items.

        Args:
            items: List of extracted string items with structure:
                {
                    "text": "original text",
                    "occurrences": [...]
                }
            languages: List of (code, description) tuples, e.g.:
                [("ja", "Japanese"), ("en", "American English")]

        Returns:
            List of items with translations added:
                {
                    "text": "original text",
                    "translations": {
                        "ja": "Japanese translation",
                        "en": "English translation"
                    }
                }
            Or for non-translatable items:
                {
                    "text": "technical-id",
                    "translations": false
                }
        """
        raise NotImplementedError

    def build_prompt(self, items: List[Dict], languages: List[Tuple[str, str]]) -> str:
        """
        Build translation prompt for AI.

        Args:
            items: List of items to translate
            languages: List of target languages

        Returns:
            Formatted prompt string
        """
        lang_specs = "\n".join([f'   - "{code}": {desc}' for code, desc in languages])

        prompt = f"""Translate the following extracted strings for Laravel i18n.

For each item:
1. If the text is meant for user-facing i18n, add translations for these languages:
{lang_specs}
2. If the text is NOT meant for i18n (technical identifiers, dimensions like "600x600",
   CSS class names, code literals, etc.), set "translations": false

Examine the context in "occurrences" → "positions" → "context" to understand usage.

Input items:
{json.dumps(items, ensure_ascii=False, indent=2)}

Return JSON in this exact format:
{{
  "items": [
    {{
      "text": "original text",
      "translations": {{
        "{languages[0][0]}": "translation in {languages[0][1]}",
        "{languages[1][0] if len(languages) > 1 else 'other'}": "translation"
      }}
    }},
    {{
      "text": "technical-id",
      "translations": false
    }}
  ]
}}

IMPORTANT: Return only valid JSON without any markdown formatting or code blocks."""

        return prompt
