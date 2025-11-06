"""
PHP code analysis utilities.

Consolidated module for all PHP-related analysis:
- PHP block detection (<?php...?>, @php...@endphp)
- PHP string literal extraction
- Context-based validation for PHP strings

This module combines functionality from:
- php_block_detector.py
- php_string_extractor.py
"""

import re
from typing import List, Tuple

from refactor.utils.string_processor import StringProcessor


class PHPAnalyzer:
    """
    Unified analyzer for PHP code.

    Provides all PHP analysis capabilities including block detection,
    string extraction, and context-based validation.
    """

    # Exclusion patterns for PHP string validation
    TRANSLATION_FUNCTIONS = [
        r"__\s*\(",
        r"trans\s*\(",
        r"@lang\s*\(",
        r"Lang::get\s*\(",
    ]

    LOG_FUNCTIONS = [
        r"Log::\w+\s*\(",
        r"logger\s*\(",
        r"error_log\s*\(",
    ]

    CONSOLE_OUTPUT = [
        r"\becho\s+",
        r"\bprint\s+",
        r"\bvar_dump\s*\(",
        r"\bdd\s*\(",
        r"\bdump\s*\(",
        r"\bprint_r\s*\(",
    ]

    COMMAND_OUTPUT = [
        r"\$this->info\s*\(",
        r"\$this->error\s*\(",
        r"\$this->line\s*\(",
        r"\$this->comment\s*\(",
        r"\$this->warn\s*\(",
        r"\$this->warning\s*\(",
    ]

    REGEX_FUNCTIONS = [
        r"\bpreg_match\s*\(",
        r"\bpreg_match_all\s*\(",
        r"\bpreg_replace\s*\(",
        r"\bpreg_replace_callback\s*\(",
        r"\bpreg_replace_callback_array\s*\(",
        r"\bpreg_filter\s*\(",
        r"\bpreg_grep\s*\(",
        r"\bpreg_split\s*\(",
    ]

    PHP_BUILTIN_FUNCTIONS = [
        r"\bfunction_exists\s*\(",
        r"\bclass_exists\s*\(",
        r"\bmethod_exists\s*\(",
        r"\binterface_exists\s*\(",
        r"\btrait_exists\s*\(",
        r"\bdefined\s*\(",
        r"\bdefine\s*\(",
        r"\bin_array\s*\(",
        r"\barray_key_exists\s*\(",
        r"\bisset\s*\(",
        r"\bempty\s*\(",
        r"\bheader\s*\(",
        r"\bsetcookie\s*\(",
        r"\bsession_name\s*\(",
        r"\bini_get\s*\(",
        r"\bini_set\s*\(",
        r"\bextension_loaded\s*\(",
        r"\bget_class\s*\(",
        r"\bget_called_class\s*\(",
        r"\bis_a\s*\(",
        r"\bis_subclass_of\s*\(",
    ]

    ELOQUENT_METHODS = [
        r"::select\s*\(",
        r"::where\s*\(",
        r"::whereIn\s*\(",
        r"::whereNotIn\s*\(",
        r"::whereBetween\s*\(",
        r"::whereNull\s*\(",
        r"::whereNotNull\s*\(",
        r"::orderBy\s*\(",
        r"::groupBy\s*\(",
        r"::having\s*\(",
        r"::join\s*\(",
        r"::leftJoin\s*\(",
        r"::rightJoin\s*\(",
        r"::table\s*\(",
        r"->select\s*\(",
        r"->where\s*\(",
        r"->whereIn\s*\(",
        r"->whereNotIn\s*\(",
        r"->whereBetween\s*\(",
        r"->whereNull\s*\(",
        r"->whereNotNull\s*\(",
        r"->orderBy\s*\(",
        r"->groupBy\s*\(",
        r"->having\s*\(",
        r"->join\s*\(",
        r"->leftJoin\s*\(",
        r"->rightJoin\s*\(",
        r"->pluck\s*\(",
        r"->value\s*\(",
        r"->raw\s*\(",
        r"->table\s*\(",
        r"->format\s*\(",
    ]

    def __init__(self, min_bytes: int = 2):
        """
        Initialize PHP analyzer.

        Args:
            min_bytes: Minimum byte length for string extraction (default: 2)
        """
        self.min_bytes = min_bytes

    def extract_and_validate_strings(self, content: str, validator_func) -> List[Tuple[str, int, int, int]]:
        """
        Extract and validate string literals from PHP content in one step.

        This is a convenience method that combines extraction and validation,
        returning only strings that pass validation checks.

        Args:
            content: PHP content to process
            validator_func: Function for basic string validation (should_extract_string)

        Returns:
            List of tuples: (stripped_text, line, column, length) - only validated strings
        """
        results = []

        # Extract all string literals
        string_literals = self.extract_string_literals(content)

        # Validate and filter
        for text, line, column, _length in string_literals:
            stripped_text = text.strip()
            if not stripped_text:
                continue

            # Use validation with context
            if self.should_include_string(stripped_text, content, line, column, validator_func):
                # Calculate position for stripped text
                leading_whitespace = len(text) - len(text.lstrip())
                adjusted_column = column + leading_whitespace
                stripped_length = len(stripped_text)
                results.append((stripped_text, line, adjusted_column, stripped_length))

        return results

    # ========== PHP Block Detection ==========

    @staticmethod
    def find_block_end(content: str, start_pos: int, end_marker: str, end_marker_length: int) -> int:
        """
        Find the end marker that is not inside a string literal or comment.

        This function correctly handles:
        - String literals (both single and double quoted)
        - Escaped characters in strings
        - Multi-line comments /* ... */
        - Single-line comments //
        - Shell-style comments #

        Args:
            content: Full content to search
            start_pos: Position to start searching from
            end_marker: End marker to find (e.g., "?>", "@endphp")
            end_marker_length: Length of end marker

        Returns:
            Position of end marker, or -1 if not found
        """
        i = start_pos

        while i < len(content) - (end_marker_length - 1):
            char = content[i]

            # Skip multi-line comments /* ... */
            if i + 1 < len(content) and content[i : i + 2] == "/*":
                end = content.find("*/", i + 2)
                if end != -1:
                    i = end + 2
                    continue
                else:
                    return -1  # Unclosed comment

            # Skip single-line comments //
            if i + 1 < len(content) and content[i : i + 2] == "//":
                end = content.find("\n", i + 2)
                if end != -1:
                    i = end + 1
                else:
                    return -1  # Comment to end of file
                continue

            # Skip shell-style comments #
            if char == "#":
                end = content.find("\n", i + 1)
                if end != -1:
                    i = end + 1
                else:
                    return -1  # Comment to end of file
                continue

            # Check for string literals
            if char in ('"', "'"):
                quote = char
                i += 1
                # Skip through string, handling escapes
                while i < len(content):
                    if content[i] == "\\" and i + 1 < len(content):
                        i += 2  # Skip escaped character
                        continue
                    elif content[i] == quote:
                        i += 1
                        break
                    else:
                        i += 1
                continue

            # Check for end marker
            if content[i : i + end_marker_length] == end_marker:
                return i

            i += 1

        return -1

    @staticmethod
    def extract_php_ranges(content: str, detect_blade: bool = False) -> List[Tuple[int, int]]:
        """
        Extract all PHP code ranges from content.

        PHP ranges include:
        - <?php ... ?> (or to end of file if no closing tag)
        - @php ... @endphp (only if detect_blade=True)

        This function properly handles:
        - String literals containing ?> or @endphp
        - Comments containing ?> or @endphp
        - Escaped characters in strings

        Args:
            content: File content
            detect_blade: Whether to detect @php...@endphp blocks (for Blade files)

        Returns:
            List of (start_pos, end_pos) tuples representing PHP code ranges
        """
        ranges = []

        # Find <?php ... ?> blocks
        pos = 0
        while True:
            # Find opening tag
            php_start = content.find("<?php", pos)
            if php_start == -1:
                break

            # Find closing tag, skipping those in strings and comments
            php_end = PHPAnalyzer.find_block_end(content, php_start + 5, "?>", 2)
            if php_end == -1:
                # No closing tag, PHP goes to end of file
                ranges.append((php_start, len(content)))
                break
            else:
                ranges.append((php_start, php_end + 2))  # +2 to include ?>
                pos = php_end + 2

        # Find @php ... @endphp blocks (only for Blade files)
        if detect_blade:
            pos = 0
            while True:
                blade_php_start = content.find("@php", pos)
                if blade_php_start == -1:
                    break

                # Check if this is actually @php directive (not part of another word)
                if blade_php_start > 0 and content[blade_php_start - 1].isalnum():
                    pos = blade_php_start + 4
                    continue

                # Find @endphp, skipping those in strings and comments
                blade_php_end = PHPAnalyzer.find_block_end(content, blade_php_start + 4, "@endphp", 7)
                if blade_php_end == -1:
                    # No @endphp, assume it goes to end of file
                    ranges.append((blade_php_start, len(content)))
                    break
                else:
                    # Check if @endphp is not part of another word
                    if blade_php_end + 7 < len(content) and content[blade_php_end + 7].isalnum():
                        pos = blade_php_end + 1
                        continue

                    ranges.append((blade_php_start, blade_php_end + 7))  # +7 to include @endphp
                    pos = blade_php_end + 7

        # Sort and merge overlapping ranges
        if ranges:
            ranges.sort()
            merged = [ranges[0]]
            for start, end in ranges[1:]:
                if start <= merged[-1][1]:
                    # Overlapping or adjacent, merge
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                else:
                    merged.append((start, end))
            return merged

        return ranges

    # ========== PHP String Extraction ==========

    def extract_string_literals(self, content: str) -> List[Tuple[str, int, int, int]]:
        """
        Extract all string literals from PHP code.

        Args:
            content: PHP content

        Returns:
            List of tuples: (text, line, column, length)
        """
        results = []
        i = 0

        while i < len(content):
            char = content[i]

            # Skip multi-line comments /* ... */
            if i + 1 < len(content) and content[i : i + 2] == "/*":
                end = content.find("*/", i + 2)
                if end != -1:
                    i = end + 2
                    continue
                else:
                    break

            # Skip single-line comments //
            if i + 1 < len(content) and content[i : i + 2] == "//":
                end = content.find("\n", i + 2)
                if end != -1:
                    i = end + 1
                else:
                    break
                continue

            # Skip shell-style comments #
            if char == "#":
                end = content.find("\n", i + 1)
                if end != -1:
                    i = end + 1
                else:
                    break
                continue

            # Check for string start
            if char in ('"', "'"):
                quote = char
                start_pos = i
                i += 1
                string_chars = []

                # Extract string content
                while i < len(content):
                    if content[i] == "\\" and i + 1 < len(content):
                        # Escaped character - add both backslash and next char to string
                        string_chars.append(content[i])
                        string_chars.append(content[i + 1])
                        i += 2
                        continue
                    elif content[i] == quote:
                        # End of string found
                        string_content = "".join(string_chars)

                        # Only add non-empty, non-whitespace strings
                        if string_content and not string_content.isspace():
                            line, column = StringProcessor.get_line_column(content, start_pos + 1)
                            results.append((string_content, line, column, len(string_content)))

                        i += 1
                        break
                    else:
                        string_chars.append(content[i])
                        i += 1
            else:
                i += 1

        return results

    # ========== PHP String Validation ==========

    def should_include_string(self, text: str, content: str, line: int, column: int, validator_func) -> bool:
        """
        Determine if a string should be included based on context.

        Args:
            text: The string content
            content: Full file content
            line: Line number (1-based)
            column: Column number (0-based)
            validator_func: Function for basic string validation (should_extract_string)

        Returns:
            True if the string should be included
        """
        # Use common validation logic
        if not validator_func(text, self.min_bytes):
            return False

        # Get context information
        lines = content.split("\n")
        if line < 1 or line > len(lines):
            return False

        current_line = lines[line - 1]
        before_string = current_line[:column]
        after_string = current_line[column + len(text) :].lstrip()

        # Check for exclusion patterns
        if self._is_excluded_by_function_pattern(before_string):
            return False

        # Calculate position for array key check
        # Get position for context check
        position = StringProcessor.get_position_from_line_column(content, line, column)
        if position == -1:
            return True

        if self._is_array_key(before_string, after_string, content, position, len(text)):
            return False

        return True

    def _is_excluded_by_function_pattern(self, before_string: str) -> bool:
        """
        Check if the string is excluded by any function pattern.

        Args:
            before_string: Context before the string on the same line

        Returns:
            True if the string should be excluded
        """
        all_patterns = (
            self.TRANSLATION_FUNCTIONS
            + self.LOG_FUNCTIONS
            + self.CONSOLE_OUTPUT
            + self.COMMAND_OUTPUT
            + self.REGEX_FUNCTIONS
            + self.PHP_BUILTIN_FUNCTIONS
            + self.ELOQUENT_METHODS
        )

        for pattern in all_patterns:
            if re.search(pattern, before_string):
                return True

        return False

    def _is_array_key(self, before_string: str, after_string: str, content: str, position: int, text_length: int) -> bool:
        """
        Check if the string is an array key (should be excluded).

        Args:
            before_string: Context before the string on the same line
            after_string: Context after the string on the same line (already lstrip)
            content: Full file content
            position: Character position in content
            text_length: Length of the text

        Returns:
            True if the string is an array key
        """
        before_string_stripped = before_string.rstrip()

        # Pattern 1: Array access - ['key'] or ["key"]
        if before_string_stripped.endswith("[") and after_string.startswith("]"):
            return True

        # Pattern 2: Array access with variable/property
        if re.search(r"[\w\)\]]\s*\[$", before_string_stripped) and after_string.startswith("]"):
            return True

        # Pattern 3: Associative array key - same line
        if after_string.startswith("=>"):
            return True

        # Pattern 4: Associative array key - multi-line
        string_end_pos = position + text_length
        remaining_content = content[string_end_pos : string_end_pos + 100]
        remaining_stripped = remaining_content.lstrip()

        if remaining_stripped.startswith("'") or remaining_stripped.startswith('"'):
            remaining_stripped = remaining_stripped[1:].lstrip()

        if remaining_stripped.startswith("=>"):
            return True

        # Pattern 5: Array assignment
        if after_string.startswith("]"):
            after_bracket = after_string[1:].lstrip()
            if after_bracket.startswith("=") and not after_bracket.startswith("=="):
                return True

        return False
