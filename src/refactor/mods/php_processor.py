"""
PHP file processor for extracting hardcoded strings.
"""

import re
from typing import List, Tuple
from pathlib import Path
from ..data_models.extracted_string import ExtractedString
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

    # PHP built-in functions that don't need translation
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

    # Eloquent/Database query builder methods
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
        self.php_ranges = []  # List of (start_pos, end_pos) tuples for PHP blocks

    def _extract_php_ranges(self, content: str) -> List[Tuple[int, int]]:
        """
        Extract all PHP code ranges from content.

        PHP ranges include:
        - <?php ... ?> (or to end of file if no closing tag)
        - @php ... @endphp (for Blade files)

        Args:
            content: File content

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

            # Find closing tag or use end of file
            php_end = content.find("?>", php_start)
            if php_end == -1:
                # No closing tag, PHP goes to end of file
                ranges.append((php_start, len(content)))
                break
            else:
                ranges.append((php_start, php_end + 2))  # +2 to include ?>
                pos = php_end + 2

        # Find @php ... @endphp blocks (for Blade files)
        pos = 0
        while True:
            blade_php_start = content.find("@php", pos)
            if blade_php_start == -1:
                break

            # Check if this is actually @php directive (not part of another word)
            if blade_php_start > 0 and content[blade_php_start - 1].isalnum():
                pos = blade_php_start + 4
                continue

            blade_php_end = content.find("@endphp", blade_php_start)
            if blade_php_end == -1:
                # No @endphp, assume it goes to end of file
                ranges.append((blade_php_start, len(content)))
                break
            else:
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

    def _is_in_php_block(self, position: int) -> bool:
        """
        Check if a position is within a PHP code block.

        Args:
            position: Character position in content

        Returns:
            True if position is within a PHP block
        """
        for start, end in self.php_ranges:
            if start <= position < end:
                return True
        return False

    def process(self) -> List[ExtractedString]:
        """
        Process the PHP file and extract hardcoded strings.

        Returns:
            List of ExtractedString objects
        """
        # Read file content
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.content = f.read()

        # Extract PHP code ranges
        self.php_ranges = self._extract_php_ranges(self.content)

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

                results.append(ExtractedString(stripped_text, line, adjusted_column, stripped_length))

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

        # Calculate position in content
        position = self._get_position_from_line_column(content, line, column)
        if position == -1:
            return True  # Can't determine position, include by default

        # Only apply PHP-specific exclusions if the string is within a PHP block
        if not self._is_in_php_block(position):
            return True  # Outside PHP blocks, include the string

        # String is in PHP block, apply PHP-specific exclusions
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

        # Check for PHP built-in functions on the current line
        for pattern in self.PHP_BUILTIN_FUNCTIONS:
            if re.search(pattern, before_string):
                return False

        # Check for Eloquent/Database query methods on the current line
        for pattern in self.ELOQUENT_METHODS:
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
