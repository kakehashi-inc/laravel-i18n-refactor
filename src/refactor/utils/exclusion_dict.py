"""
Exclusion dictionary management utilities.

Handles loading of exclusion dictionaries from files with .gitignore-like syntax.
"""

import re
from pathlib import Path
from typing import List, Tuple


class ExclusionMatcher:
    """
    Matcher for exclusion patterns with .gitignore-like syntax.

    Supports:
    - Exact matches: "word"
    - Wildcards: "word*", "*word", "*word*"
    - Negation: "!pattern" to include despite previous exclusion
    - Comments: "# comment"
    """

    def __init__(self):
        """Initialize matcher with empty patterns."""
        self.patterns: List[Tuple[str, bool]] = []

    def append_from_file(self, file_path: Path) -> "ExclusionMatcher":
        """
        Append exclusion patterns from a file to existing patterns.

        File syntax:
        - Lines starting with # are comments (ignored)
        - Empty lines are ignored
        - Lines starting with ! negate previous exclusions
        - * is a wildcard matching any characters
        - All other lines are treated as patterns

        Args:
            file_path: Path to the exclusion dictionary file

        Returns:
            Self for method chaining
        """
        if not file_path.exists():
            return self

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    # Skip empty lines
                    if not line:
                        continue

                    # Skip comments
                    if line.startswith("#"):
                        continue

                    # Handle negation patterns
                    if line.startswith("!"):
                        pattern = line[1:].strip()
                        if pattern:
                            self.patterns.append((pattern, True))  # True = negation
                    else:
                        self.patterns.append((line, False))  # False = exclusion

        except (OSError, IOError):
            pass

        return self

    def should_exclude(self, text: str) -> bool:
        """
        Check if text should be excluded based on patterns.

        Patterns are evaluated in order. Later patterns override earlier ones.
        Negation patterns (starting with !) include the text even if excluded before.

        Args:
            text: Text to check

        Returns:
            True if text should be excluded, False otherwise
        """
        excluded = False

        for pattern, is_negation in self.patterns:
            if self._matches(text, pattern):
                excluded = not is_negation

        return excluded

    def _matches(self, text: str, pattern: str) -> bool:
        """
        Check if text matches pattern.

        Patterns can contain:
        - * (matches any sequence of characters)
        - Exact strings (case-sensitive)

        Args:
            text: Text to match
            pattern: Pattern (may contain *)

        Returns:
            True if text matches pattern
        """
        # Convert glob pattern to regex
        # Escape special regex characters except *
        regex_pattern = re.escape(pattern).replace(r"\*", ".*")
        # Anchor at start and end for exact matching
        regex_pattern = f"^{regex_pattern}$"

        return bool(re.match(regex_pattern, text))
