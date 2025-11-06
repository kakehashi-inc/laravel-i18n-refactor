"""
String processing utilities.

Consolidated module for all string-related processing:
- String validation
- Text adjustment (whitespace stripping with position correction)
- String collection and consolidation

This module combines functionality from:
- string_validator.py
- text_adjuster.py
- string_collector.py
"""

import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from ..data_models.string_occurrence import StringOccurrence


class StringProcessor:
    """
    Unified processor for string operations.

    Provides validation, adjustment, and collection capabilities.
    """

    @staticmethod
    def contains_non_ascii(text: str) -> bool:
        """
        Check if string contains non-ASCII characters (e.g., Japanese, Chinese, emoji).

        Args:
            text: String to check

        Returns:
            True if string contains any character with code > 127
        """
        return any(ord(char) > 127 for char in text)

    @staticmethod
    def should_extract_string(text: str, min_bytes: int) -> bool:
        """
        Determine if a string should be extracted for translation.

        Creates a temporary copy of the string and removes:
        - Half-width digits (0-9)
        - Half-width symbols (ASCII non-alphanumeric characters)
        - Spaces, tabs, CR, LF

        Also excludes strings starting with symbols that cannot be at the beginning
        of sentences or words: # , / $ .

        For strings containing only ASCII characters, excludes strings with byte length
        less than min_bytes. However, strings containing non-ASCII characters (e.g.,
        Japanese, Chinese, emoji) are always extracted regardless of byte length.

        If nothing remains after removal, the string is excluded.
        If anything remains, the string should be extracted.

        Args:
            text: String to validate
            min_bytes: Minimum byte length (only applies to ASCII-only strings)

        Returns:
            True if string should be extracted, False otherwise
        """
        # Empty or whitespace-only strings are excluded
        if not text or not text.strip():
            return False

        # Create a temporary copy for checking
        check_text = text.strip()

        # Exclude strings that are only escape sequences (e.g., \n, \t, \r, \r\n, etc.)
        # These are common in code configuration but not translatable text
        escape_only_pattern = r'^(\\[ntrfvabe\\"\'])+$'
        if re.match(escape_only_pattern, check_text):
            return False

        # Check if string contains non-ASCII characters
        has_non_ascii = StringProcessor.contains_non_ascii(check_text)

        # Check minimum byte length only for ASCII-only strings
        # Non-ASCII strings (e.g., Japanese, emoji) bypass this check
        if not has_non_ascii and len(check_text.encode("utf-8")) < min_bytes:
            return False

        # Exclude regex patterns (e.g., (?:, (?=, (?!, [0-9], \d, \w, etc.)
        regex_patterns = [
            "(?:",  # non-capturing group
            "(?=",  # positive lookahead
            "(?!",  # negative lookahead
            "(?<",  # lookbehind
            "\\d",
            "\\w",
            "\\s",
            "\\b",  # escape sequences
            "^[",
            "^\\",  # start anchors with character class or escape
        ]
        for pattern in regex_patterns:
            if check_text.startswith(pattern):
                return False

        # Exclude strings starting with symbols that cannot be at the beginning of sentences/words
        # These are: # , / $ . and various punctuation marks
        # This applies to all strings, regardless of whether they contain non-ASCII characters
        invalid_start_chars = {"#", ",", "/", "$", ".", "!", ":", ";", ")", "]", "}", "%", "&", "@", "?", "^", "~", "`"}
        if check_text and check_text[0] in invalid_start_chars:
            return False

        # Remove half-width digits, symbols, whitespace (space, tab, CR, LF)
        filtered_chars = []
        for char in check_text:
            char_code = ord(char)

            # Skip half-width digits (0-9: ASCII 48-57)
            if 48 <= char_code <= 57:
                continue

            # Skip whitespace (space, tab, CR, LF)
            if char in (" ", "\t", "\r", "\n"):
                continue

            # Skip half-width symbols (ASCII < 128 and not alphanumeric)
            if char_code < 128:
                # ASCII letters (a-z: 97-122, A-Z: 65-90) should be kept
                if not ((65 <= char_code <= 90) or (97 <= char_code <= 122)):
                    continue

            # Keep this character (either non-ASCII or ASCII letter)
            filtered_chars.append(char)

        # If nothing remains after filtering, exclude the string
        if not filtered_chars:
            return False

        # If something remains, extract the string
        return True

    @staticmethod
    def get_line_column(content: str, pos: int) -> Tuple[int, int]:
        """
        Calculate line and column number for a position in content.

        Args:
            content: Full content
            pos: Position in content (0-based)

        Returns:
            Tuple of (line, column) where line is 1-based and column is 0-based
        """
        lines_before = content[:pos].split("\n")
        line = len(lines_before)
        column = len(lines_before[-1]) if lines_before else 0
        return line, column

    @staticmethod
    def get_position_from_line_column(content: str, line: int, column: int) -> int:
        """
        Get position in content from line and column.

        Args:
            content: Full content
            line: Line number (1-based)
            column: Column number (0-based)

        Returns:
            Position in content, or -1 if invalid
        """
        lines = content.split("\n")
        if line < 1 or line > len(lines):
            return -1

        pos = sum(len(lines[i]) + 1 for i in range(line - 1))
        pos += column

        if pos >= len(content):
            return -1

        return pos

    @staticmethod
    def adjust_text_position(text: str, column: int) -> Tuple[str, int, int]:
        """
        Strip whitespace from text and adjust column position accordingly.

        Args:
            text: Original text with potential leading/trailing whitespace
            column: Original column position (0-based)

        Returns:
            Tuple of (stripped_text, adjusted_column, stripped_length)
        """
        stripped_text = text.strip()

        # Calculate leading whitespace offset
        leading_whitespace = len(text) - len(text.lstrip())
        adjusted_column = column + leading_whitespace
        stripped_length = len(stripped_text)

        return stripped_text, adjusted_column, stripped_length


class StringCollector:
    """
    Collects and consolidates extracted strings from multiple files.

    Merges identical strings and tracks all their occurrences.
    """

    def __init__(self):
        """Initialize the collector."""
        # Dictionary mapping text to list of (file_path, occurrences)
        self.strings: Dict[str, List[Tuple[str, List[StringOccurrence]]]] = {}

    def add_string(self, text: str, file_path: Path, line: int, column: int, length: int, context: Optional[List[str]] = None) -> None:
        """
        Add a string occurrence.

        Args:
            text: The extracted string content
            file_path: Path to the source file
            line: Line number (1-based)
            column: Column number (0-based)
            length: String length in characters
            context: Optional list of context lines (including the target line)
        """
        # Use absolute path
        absolute_path = str(file_path.resolve())

        # Create occurrence
        occurrence = StringOccurrence(line, column, length, context)

        # Add to collection
        if text not in self.strings:
            self.strings[text] = []

        # Find existing file entry
        for file_entry in self.strings[text]:
            if file_entry[0] == absolute_path:
                # Add to existing file's occurrences
                file_entry[1].append(occurrence)
                return

        # Create new file entry
        self.strings[text].append((absolute_path, [occurrence]))

    def get_results(self) -> List[Dict]:
        """
        Get consolidated results in the output format.

        Returns:
            List of dictionaries with structure:
            [
                {
                    "text": "string content",
                    "occurrences": [
                        {
                            "file": "relative/path/to/file.php",
                            "positions": [
                                {"line": 10, "column": 5, "length": 15}
                            ]
                        }
                    ]
                }
            ]
        """
        results = []

        for text, file_occurrences in self.strings.items():
            occurrences = []

            for file_path, positions in file_occurrences:
                occurrences.append({"file": file_path, "positions": [pos.to_dict() for pos in positions]})

            results.append({"text": text, "occurrences": occurrences})

        return results

    def get_string_count(self) -> int:
        """Get the number of unique strings collected."""
        return len(self.strings)

    def get_total_occurrences(self) -> int:
        """Get the total number of string occurrences."""
        total = 0
        for file_occurrences in self.strings.values():
            for _, positions in file_occurrences:
                total += len(positions)
        return total
