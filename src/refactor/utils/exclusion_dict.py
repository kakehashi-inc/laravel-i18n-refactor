"""
Exclusion dictionary management utilities.

Handles loading of exclusion dictionaries from files with .gitignore-like syntax.
"""

import re
from pathlib import Path
from typing import List, Tuple


class ExclusionMatcher:
    """
    Matcher for exclusion patterns with .gitignore-like syntax and regex extension.

    Supports:
    - Exact matches: "word"
    - Wildcards: "word*", "*word", "*word*"
    - Character classes: "[0-9]", "[a-z]"
    - Regular expressions: "regex:^\\d+x\\d+$"
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
        - Lines starting with "regex:" are treated as regular expressions
        - * is a wildcard matching any characters (glob pattern)
        - [0-9], [a-z] are character classes (glob pattern)
        - All other lines are treated as patterns

        Examples:
            word              # Exact match
            data-*            # Wildcard pattern
            [0-9]*x[0-9]*     # Character class pattern
            regex:^\\d+x\\d+$  # Regular expression pattern
            !important        # Negation (include despite exclusion)

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

        Patterns can be:
        - Regular expressions (starting with "regex:")
        - Glob patterns with * (matches any sequence of characters)
        - Glob patterns with character classes ([0-9], [a-z])
        - Exact strings (case-sensitive)

        Args:
            text: Text to match
            pattern: Pattern (may contain * or regex:prefix)

        Returns:
            True if text matches pattern
        """
        # Check if pattern is a regular expression
        if pattern.startswith("regex:"):
            regex = pattern[6:]  # Remove "regex:" prefix
            try:
                return bool(re.match(regex, text))
            except re.error:
                # Invalid regex, treat as no match
                return False

        # Convert glob pattern to regex
        # Escape special regex characters except * and []
        regex_pattern = ""
        i = 0
        while i < len(pattern):
            char = pattern[i]
            if char == "*":
                regex_pattern += ".*"
            elif char == "[":
                # Find closing bracket
                j = i + 1
                while j < len(pattern) and pattern[j] != "]":
                    j += 1
                if j < len(pattern):
                    # Valid character class
                    regex_pattern += pattern[i : j + 1]
                    i = j
                else:
                    # No closing bracket, treat as literal
                    regex_pattern += re.escape(char)
            else:
                regex_pattern += re.escape(char)
            i += 1

        # Anchor at start and end for exact matching
        regex_pattern = f"^{regex_pattern}$"

        return bool(re.match(regex_pattern, text))
