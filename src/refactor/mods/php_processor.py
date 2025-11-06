"""
PHP file processor for extracting hardcoded strings.
"""

import re
from typing import List, Tuple
from pathlib import Path
from ..utils.string_validator import should_extract_string, get_line_column


class PHPProcessor:
    """Processes PHP files to extract hardcoded strings."""

    # Patterns for exclusion
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

    # PHP regex functions that take regex patterns as arguments
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

    def __init__(self, file_path: Path, min_bytes: int):
        """
        Initialize the processor.

        Args:
            file_path: Path to the PHP file
            min_bytes: Minimum byte length for string extraction
        """
        self.file_path = file_path
        self.min_bytes = min_bytes
        self.content = ""

    def process(self) -> List[Tuple[str, int, int, int]]:
        """
        Process the PHP file and extract hardcoded strings.

        Returns:
            List of tuples: (text, line, column, length)
        """
        # Read file content
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.content = f.read()

        # Extract all string literals with positions from ORIGINAL content
        string_literals = self._extract_string_literals(self.content)

        # Filter and clean based on context
        results = []
        for text, line, column, length in string_literals:
            # Strip leading/trailing whitespace
            stripped_text = text.strip()

            # Skip if empty after stripping
            if not stripped_text:
                continue

            if self._should_include_string(stripped_text, self.content, line, column):
                # Recalculate position and length for stripped text
                leading_whitespace = len(text) - len(text.lstrip())
                adjusted_column = column + leading_whitespace
                stripped_length = len(stripped_text)

                results.append((stripped_text, line, adjusted_column, stripped_length))

        return results

    def _extract_string_literals(self, content: str) -> List[Tuple[str, int, int, int]]:
        """
        Extract all string literals from PHP code.

        Args:
            content: PHP content (original, not cleaned)

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
                        string_chars.append(content[i])  # backslash
                        string_chars.append(content[i + 1])  # escaped character
                        i += 2
                        continue
                    elif content[i] == quote:
                        # End of string found
                        string_content = "".join(string_chars)

                        # Only add non-empty, non-whitespace strings
                        if string_content and not string_content.isspace():
                            line, column = get_line_column(content, start_pos + 1)
                            results.append((string_content, line, column, len(string_content)))

                        i += 1
                        break
                    else:
                        string_chars.append(content[i])
                        i += 1
            else:
                i += 1

        return results

    def _should_include_string(self, text: str, content: str, line: int, column: int) -> bool:
        """
        Determine if a string should be included based on context.

        Args:
            text: The string content
            content: Full file content
            line: Line number (1-based)
            column: Column number (0-based)

        Returns:
            True if the string should be included
        """
        # Use common validation logic
        if not should_extract_string(text, self.min_bytes):
            return False

        # Get the current line for context checking
        lines = content.split("\n")
        if line < 1 or line > len(lines):
            return False

        current_line = lines[line - 1]

        # Get context before the string on the same line
        before_string = current_line[:column]

        # Check for translation functions on the current line
        for pattern in self.TRANSLATION_FUNCTIONS:
            if re.search(pattern, before_string):
                return False

        # Check for log functions on the current line
        for pattern in self.LOG_FUNCTIONS:
            if re.search(pattern, before_string):
                return False

        # Check for console output on the current line
        for pattern in self.CONSOLE_OUTPUT:
            if re.search(pattern, before_string):
                return False

        # Check for command output on the current line
        for pattern in self.COMMAND_OUTPUT:
            if re.search(pattern, before_string):
                return False

        # Check for regex functions on the current line
        for pattern in self.REGEX_FUNCTIONS:
            if re.search(pattern, before_string):
                return False

        # Check if it's an array key
        before_string_stripped = before_string.rstrip()
        after_string = current_line[column + len(text) :].lstrip()

        # Check for array access patterns: ['key'] or ["key"]
        if before_string_stripped.endswith("[") and after_string.startswith("]"):
            return False

        # Check for patterns like $var['key'] or ->prop['key'] or )['key']
        if re.search(r"[\w\)\]]\s*\[$", before_string_stripped):
            if after_string.startswith("]"):
                return False

        return True

    def _get_position_from_line_column(self, content: str, line: int, column: int) -> int:
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

        # Calculate position
        pos = sum(len(lines[i]) + 1 for i in range(line - 1))  # +1 for newline
        pos += column

        if pos >= len(content):
            return -1

        return pos
