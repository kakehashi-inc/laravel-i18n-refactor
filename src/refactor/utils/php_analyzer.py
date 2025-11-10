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
    # Excluded functions and statements (translation + console output + logging)
    # Entries can be:
    # - Simple function names: "function_name" -> generates \bfunction_name\s*\(
    # - Static methods: "Class::method" -> generates Class::method\s*\(
    # - Blade directives: "@directive" -> generates @directive\s*\(
    # - Regex patterns (with regex: prefix): "regex:pattern" -> uses pattern as-is
    EXCLUDED_FUNCTIONS = [
        # Translation functions (Laravel i18n)
        "__",
        "trans",
        "@lang",
        "Lang::get",
        # Console output functions
        "var_dump",
        "dd",
        "dump",
        "print_r",
        # Console output statements (language constructs - use regex for space-based syntax)
        r"regex:\becho\s+",
        r"regex:\bprint\s+",
        # Logging functions
        "logger",
        "error_log",
        # Log facade static methods (Log::*)
        "Log::emergency",
        "Log::alert",
        "Log::critical",
        "Log::error",
        "Log::warning",
        "Log::notice",
        "Log::info",
        "Log::debug",
    ]

    # Class instance methods
    CLASS_INSTANCE_METHODS = [
        # Artisan command output methods
        "info",
        "error",
        "line",
        "comment",
        "warn",
        "warning",
        # Eloquent/Query Builder methods
        "select",
        "where",
        "whereIn",
        "whereNotIn",
        "whereBetween",
        "whereNull",
        "whereNotNull",
        "orderBy",
        "groupBy",
        "having",
        "join",
        "leftJoin",
        "rightJoin",
        "pluck",
        "value",
        "raw",
        "table",
        "format",
        # Validation methods
        "validate",
        "validateWithBag",
    ]

    # Function definitions to exclude entirely (including function body)
    # STRICT MODE: To prevent accidental exclusions, these patterns are highly specific.
    # Format: (access_level, function_name, return_type)
    # - access_level: Required access modifier (e.g., "protected")
    # - function_name: Exact function name
    # - return_type: Required return type hint (e.g., "array")
    # All three components must match for exclusion.
    EXCLUDED_FUNCTION_DEFINITIONS = [
        ("protected", "casts", "array"),
        ("public", "rules", "array"),
    ]

    # Regular expression functions
    REGEX_FUNCTIONS = [
        "preg_match",
        "preg_match_all",
        "preg_replace",
        "preg_replace_callback",
        "preg_replace_callback_array",
        "preg_filter",
        "preg_grep",
        "preg_split",
    ]

    # PHP builtin functions that take string arguments
    PHP_BUILTIN_FUNCTIONS = [
        # Class/Function/Constant existence checks
        "function_exists",
        "class_exists",
        "method_exists",
        "interface_exists",
        "trait_exists",
        "defined",
        "define",
        "extension_loaded",
        # Array functions
        "in_array",
        "array_key_exists",
        "array_search",
        "array_column",
        "array_filter",
        "array_map",
        # Variable handling
        "isset",
        "empty",
        "compact",
        "extract",
        # Type checking
        "gettype",
        "get_class",
        "get_called_class",
        "get_parent_class",
        "is_a",
        "is_subclass_of",
        # Property/Method access
        "property_exists",
        "constant",
        "call_user_func",
        "call_user_func_array",
        # HTTP/Session/Cookie
        "header",
        "setcookie",
        "setrawcookie",
        "session_name",
        "session_id",
        "session_save_path",
        # Configuration
        "ini_get",
        "ini_set",
        "ini_restore",
        "putenv",
        "getenv",
        # File/Stream functions
        "file_exists",
        "is_file",
        "is_dir",
        "is_readable",
        "is_writable",
        "filetype",
        "mime_content_type",
        "stream_context_create",
        "stream_wrapper_register",
        # Error handling
        "trigger_error",
        "user_error",
        "error_reporting",
        # Date/Time
        "date",
        "strtotime",
        "strftime",
        "timezone_name_from_abbr",
        # String functions (format specifiers)
        "sprintf",
        "vsprintf",
        "sscanf",
        # URL functions
        "parse_url",
        "http_build_query",
    ]

    # Laravel helper functions that take string arguments
    LARAVEL_HELPER_FUNCTIONS = [
        # Path helpers
        "app_path",
        "base_path",
        "config_path",
        "database_path",
        "public_path",
        "resource_path",
        "storage_path",
        # URL helpers
        "asset",
        "secure_asset",
        "route",
        "secure_url",
        "url",
        "action",
        # Configuration
        "config",
        "env",
        # Session
        "session",
        # Request
        "old",
        "request",
        # Views
        "view",
        # Responses
        "response",
        "redirect",
        "back",
        # Authentication
        "auth",
        "bcrypt",
        "hash",
        # Cache
        "cache",
        # Events
        "event",
        "broadcast",
        # Queue/Jobs
        "dispatch",
        "dispatch_sync",
        # Validation
        "validator",
        # String helpers
        "class_basename",
        "e",
        "preg_replace_array",
        "str",
        "trans",
        "trans_choice",
        "__",
        # Array helpers
        "data_get",
        "data_set",
        "data_fill",
        "head",
        "last",
        # Misc helpers
        "abort",
        "abort_if",
        "abort_unless",
        "app",
        "collect",
        "cookie",
        "decrypt",
        "encrypt",
        "info",
        "logger",
        "method_field",
        "now",
        "optional",
        "policy",
        "resolve",
        "retry",
        "tap",
        "throw_if",
        "throw_unless",
        "today",
        "trait_uses_recursive",
        "transform",
        "value",
        "with",
    ]

    def __init__(self, min_bytes: int = 2):
        """
        Initialize PHP analyzer.

        Args:
            min_bytes: Minimum byte length for string extraction (default: 2)
        """
        self.min_bytes = min_bytes
        self._compiled_patterns = None
        self._excluded_ranges = []  # List of (start_pos, end_pos) for excluded function calls

    def _get_exclusion_patterns(self) -> List[str]:
        """
        Build regex patterns from function/method name lists.

        All patterns are used to identify function/method calls whose entire
        argument list should be excluded from string extraction.

        Pattern format in EXCLUDED_FUNCTIONS:
        - Simple name: "func" -> r"\\bfunc\\s*\\("
        - Static method: "Class::method" -> r"Class::method\\s*\\("
        - Blade directive: "@directive" -> r"@directive\\s*\\("
        - Regex pattern: "regex:pattern" -> pattern (used as-is)

        Returns:
            List of regex patterns for exclusion checking
        """
        if self._compiled_patterns is not None:
            return self._compiled_patterns

        patterns = []

        # Excluded functions and statements
        for func in self.EXCLUDED_FUNCTIONS:
            if func.startswith("regex:"):
                # Custom regex pattern - use as-is
                patterns.append(func[6:])  # Remove "regex:" prefix
            elif "::" in func:
                # Static method calls: Class::method(
                patterns.append(rf"{re.escape(func)}\s*\(")
            elif func.startswith("@"):
                # Blade directives: @lang(
                patterns.append(rf"{re.escape(func)}\s*\(")
            else:
                # Regular function calls: function(
                patterns.append(rf"\b{re.escape(func)}\s*\(")

        # Class instance methods (command output + Eloquent)
        for method in self.CLASS_INSTANCE_METHODS:
            patterns.append(rf"\$this->{re.escape(method)}\s*\(")  # Command output: $this->info()
            patterns.append(rf"->{re.escape(method)}\s*\(")  # Eloquent instance: ->where()
            patterns.append(rf"::{re.escape(method)}\s*\(")  # Eloquent static: ::select()

        # Regex functions
        for func in self.REGEX_FUNCTIONS:
            patterns.append(rf"\b{re.escape(func)}\s*\(")

        # PHP builtin functions
        for func in self.PHP_BUILTIN_FUNCTIONS:
            patterns.append(rf"\b{re.escape(func)}\s*\(")

        # Laravel helper functions
        for func in self.LARAVEL_HELPER_FUNCTIONS:
            patterns.append(rf"\b{re.escape(func)}\s*\(")

        self._compiled_patterns = patterns
        return patterns

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

        # Step 1: Identify all excluded ranges
        self._identify_excluded_function_ranges(content)  # Excluded function calls
        self._identify_excluded_function_definitions(content)  # Excluded function definitions

        # Step 2: Extract all string literals
        string_literals = self.extract_string_literals(content)

        # Step 3: Validate and filter
        for text, line, column, _length in string_literals:
            stripped_text = text.strip()
            if not stripped_text:
                continue

            # Check if string position is within any excluded range
            position = StringProcessor.get_position_from_line_column(content, line, column)
            if self._is_in_excluded_function_range(position):
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

        # before_string should NOT include the opening quote
        # column points to the first character of string content (after opening quote)
        # So we need to go back 1 position to skip the opening quote
        if column > 0:
            before_string = current_line[: column - 1]
        else:
            before_string = ""

        # after_string starts from the position after string content
        # which is the closing quote position
        # We need to skip the closing quote to get the actual "after" context
        after_with_quote = current_line[column + len(text) :]

        # Skip the closing quote (either ' or ")
        if after_with_quote and after_with_quote[0] in ("'", '"'):
            after_string_raw = after_with_quote[1:]
        else:
            after_string_raw = after_with_quote

        after_string = after_string_raw.lstrip()

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
        patterns = self._get_exclusion_patterns()

        for pattern in patterns:
            if re.search(pattern, before_string):
                return True

        return False

    def _is_array_key(self, before_string: str, after_string: str, content: str, position: int, text_length: int) -> bool:
        """
        Check if the string is an array key (should be excluded).

        In PHP code, if a string literal (enclosed in quotes) is surrounded by [ and ],
        it is an array key and should be excluded.

        Examples:
        - $array['key'] - 'key' is an array key
        - $object->property['key'] - 'key' is an array key
        - $array['key1']['key2'] - both 'key1' and 'key2' are array keys
        - ['key' => 'value'] - 'key' is an array key (associative array)
        - $array['key'] = 'value' - first 'key' is array key, second 'value' is not

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

        # Primary check: String is surrounded by [ and ]
        # before_string should end with [ and after_string should start with ]
        if before_string_stripped.endswith("[") and after_string.startswith("]"):
            return True

        # Associative array key: 'key' => value (same line)
        if after_string.startswith("=>"):
            return True

        # Associative array key: 'key' => value (multi-line)
        string_end_pos = position + text_length
        remaining_content = content[string_end_pos : string_end_pos + 100]
        remaining_stripped = remaining_content.lstrip()

        # Skip closing quote if present
        if remaining_stripped.startswith("'") or remaining_stripped.startswith('"'):
            remaining_stripped = remaining_stripped[1:].lstrip()

        if remaining_stripped.startswith("=>"):
            return True

        return False

    def _identify_excluded_function_ranges(self, content: str) -> None:
        """
        Identify all ranges of excluded function calls (entire function call including arguments).

        This method finds all calls to excluded functions and marks the entire function call range
        (from function name to closing parenthesis). This applies uniformly to ALL exclusion categories:
        - Excluded functions (translation, console output, logging)
          Examples: __(), trans(), var_dump(), dd(), logger(), Log::error()
        - Laravel helpers (config(), route(), view(), etc.)
        - Class instance methods (->info(), ->where(), ::select(), etc.)
        - And all other excluded function categories

        Examples:
        - Log::error('Connection error: ' . $ex->getMessage() . ' [POST ' . $url . ']')
          → Entire range from 'Log::error(' to final ')' is excluded
        - config('app.name')
          → Entire range from 'config(' to ')' is excluded
        - __('auth.failed')
          → Entire range from '__(' to ')' is excluded
        - logger('Processing ' . $count . ' items')
          → Entire range from 'logger(' to ')' is excluded
        - $this->info('Processing...')
          → Entire range from '$this->info(' to ')' is excluded
        - User::where('name', 'John')
          → Entire range from '::where(' to ')' is excluded

        Args:
            content: PHP content to analyze
        """
        self._excluded_ranges = []
        patterns = self._get_exclusion_patterns()

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                # match.end() - 1 points to the opening '(' in most cases
                # Find the position of '(' after the function/method name
                paren_pos = match.end() - 1

                # Verify this is actually a '('
                if paren_pos >= len(content) or content[paren_pos] != "(":
                    continue

                # Find the matching closing parenthesis
                close_paren = self._find_matching_parenthesis(content, paren_pos)

                if close_paren > paren_pos:
                    # Exclude the entire function call (from start of match to closing paren)
                    self._excluded_ranges.append((match.start(), close_paren + 1))

    def _identify_excluded_function_definitions(self, content: str) -> None:
        """
        Identify all ranges of excluded function definitions (entire function including body).

        STRICT MODE: This method uses highly specific patterns to avoid accidental exclusions.
        Each pattern requires exact matches for:
        1. Access level (e.g., "protected")
        2. Function name (e.g., "casts")
        3. Return type hint (e.g., ": array")

        All three components must match for the function to be excluded.

        Examples (WILL be excluded):
        - protected function casts(): array { return ['key' => 'array']; }
          → Entire range from 'protected function casts' to final '}' is excluded

        Examples (will NOT be excluded - missing components):
        - public function casts(): array { ... }  // Wrong access level
        - protected function casts() { ... }  // Missing return type
        - protected function customCasts(): array { ... }  // Wrong function name
        - private function casts(): array { ... }  // Wrong access level

        Args:
            content: PHP content to analyze
        """
        for access_level, func_name, return_type in self.EXCLUDED_FUNCTION_DEFINITIONS:
            # Pattern: EXACT access level + function + EXACT function name + EXACT return type
            # Example: "protected function casts(): array"
            # \b ensures word boundary (no partial matches)
            # \s* allows for flexible whitespace
            pattern = rf"{re.escape(access_level)}\s+function\s+\b{re.escape(func_name)}\b\s*\(\s*\)\s*:\s*{re.escape(return_type)}"

            for match in re.finditer(pattern, content):
                # Find the opening brace after the return type
                # match.end() is right after the return type (e.g., "array")
                brace_search_start = match.end()
                brace_start = -1

                # Search for opening brace after return type
                # Allow for whitespace and possible comments
                for i in range(brace_search_start, min(brace_search_start + 100, len(content))):
                    if content[i] == "{":
                        brace_start = i
                        break
                    elif content[i] == ";":
                        # Abstract method or interface definition, no body
                        break

                if brace_start != -1:
                    brace_end = self._find_matching_brace(content, brace_start)
                    if brace_end > brace_start:
                        # Exclude the entire function definition (from start of match to closing brace)
                        self._excluded_ranges.append((match.start(), brace_end + 1))

    def _find_matching_parenthesis(self, content: str, open_paren_pos: int) -> int:
        """
        Find the matching closing parenthesis for an opening parenthesis.

        This correctly handles:
        - Nested parentheses
        - String literals containing parentheses
        - Comments containing parentheses

        Args:
            content: Content to search
            open_paren_pos: Position of the opening '('

        Returns:
            Position of matching ')', or -1 if not found
        """
        if open_paren_pos >= len(content) or content[open_paren_pos] != "(":
            return -1

        depth = 1
        i = open_paren_pos + 1

        while i < len(content) and depth > 0:
            char = content[i]

            # Skip multi-line comments /* ... */
            if i + 1 < len(content) and content[i : i + 2] == "/*":
                end = content.find("*/", i + 2)
                if end != -1:
                    i = end + 2
                    continue
                else:
                    return -1

            # Skip single-line comments //
            if i + 1 < len(content) and content[i : i + 2] == "//":
                end = content.find("\n", i + 2)
                if end != -1:
                    i = end + 1
                else:
                    return -1
                continue

            # Skip shell-style comments #
            if char == "#":
                end = content.find("\n", i + 1)
                if end != -1:
                    i = end + 1
                else:
                    return -1
                continue

            # Handle string literals
            if char in ('"', "'"):
                quote = char
                i += 1
                while i < len(content):
                    if content[i] == "\\" and i + 1 < len(content):
                        i += 2
                        continue
                    elif content[i] == quote:
                        i += 1
                        break
                    else:
                        i += 1
                continue

            # Count parentheses
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return i

            i += 1

        return -1

    def _find_matching_brace(self, content: str, open_brace_pos: int) -> int:
        """
        Find the matching closing brace for an opening brace.

        This correctly handles:
        - Nested braces
        - String literals containing braces
        - Comments containing braces

        Args:
            content: Content to search
            open_brace_pos: Position of the opening '{'

        Returns:
            Position of matching '}', or -1 if not found
        """
        if open_brace_pos >= len(content) or content[open_brace_pos] != "{":
            return -1

        depth = 1
        i = open_brace_pos + 1

        while i < len(content) and depth > 0:
            char = content[i]

            # Skip multi-line comments /* ... */
            if i + 1 < len(content) and content[i : i + 2] == "/*":
                end = content.find("*/", i + 2)
                if end != -1:
                    i = end + 2
                    continue
                else:
                    return -1

            # Skip single-line comments //
            if i + 1 < len(content) and content[i : i + 2] == "//":
                end = content.find("\n", i + 2)
                if end != -1:
                    i = end + 1
                else:
                    return -1
                continue

            # Skip shell-style comments #
            if char == "#":
                end = content.find("\n", i + 1)
                if end != -1:
                    i = end + 1
                else:
                    return -1
                continue

            # Handle string literals
            if char in ('"', "'"):
                quote = char
                i += 1
                while i < len(content):
                    if content[i] == "\\" and i + 1 < len(content):
                        i += 2
                        continue
                    elif content[i] == quote:
                        i += 1
                        break
                    else:
                        i += 1
                continue

            # Count braces
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return i

            i += 1

        return -1

    def _is_in_excluded_function_range(self, position: int) -> bool:
        """
        Check if a position is within any excluded function call range.

        Args:
            position: Character position in content

        Returns:
            True if position is within an excluded range
        """
        if position == -1:
            return False

        for start, end in self._excluded_ranges:
            if start <= position < end:
                return True

        return False
