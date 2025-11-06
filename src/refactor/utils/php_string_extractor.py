"""
PHP string extraction utilities.
Shared logic for extracting strings from PHP code blocks.
"""

import re
from typing import List, Tuple
from ..utils.string_validator import should_extract_string, get_line_column


class PHPStringExtractor:
    """Extract and validate strings from PHP code."""

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

    def __init__(self, min_bytes: int):
        """
        Initialize the extractor.

        Args:
            min_bytes: Minimum byte length for string extraction
        """
        self.min_bytes = min_bytes

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

    def should_include_string(self, text: str, content: str, line: int, column: int) -> bool:
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
        position = self.get_position_from_line_column(content, line, column)
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

    def get_position_from_line_column(self, content: str, line: int, column: int) -> int:
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
