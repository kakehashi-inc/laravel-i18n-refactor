"""Base class for AI translation providers."""

import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from ..mods.prompt_builder import PromptBuilder


class BaseProvider(ABC):
    """Base class for AI translation providers."""

    def __init__(self, **kwargs):
        """
        Initialize provider with configuration.

        Args:
            **kwargs: Provider-specific configuration including:
                - model: Model name
                - api_key: API key
                - list_models: Boolean flag for model listing mode
                - summary: Application summary for better translation context
                - Other provider-specific parameters
        """
        self.kwargs = kwargs
        self.summary = kwargs.get("summary")
        # Initialize PromptBuilder with summary
        self.prompt_builder = PromptBuilder(summary=self.summary)

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
