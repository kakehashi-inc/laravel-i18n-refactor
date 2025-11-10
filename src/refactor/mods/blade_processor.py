"""
Blade template processor for extracting hardcoded strings.
"""

import re
from typing import List, Tuple, Set
from pathlib import Path
from bs4 import BeautifulSoup, Comment, Tag
from bs4.element import NavigableString
from ..data_models.extracted_string import ExtractedString
from ..utils.php_analyzer import PHPAnalyzer
from ..utils.string_processor import StringProcessor


class BladeProcessor:
    """Processes Blade templates to extract hardcoded strings."""

    # Patterns for Blade constructs to exclude
    BLADE_TRANSLATION_PATTERNS = [
        r"\{\{\s*__\(",  # {{ __() }}
        r"\{\{\s*trans\(",  # {{ trans() }}
        r"\{!!\s*__\(",  # {!! __() !!}
        r"\{!!\s*trans\(",  # {!! trans() !!}
        r"@lang\(",  # @lang()
    ]

    BLADE_VARIABLE_PATTERNS = [
        r"\{\{\s*\$",  # {{ $variable }}
        r"\{!!\s*\$",  # {!! $variable !!}
    ]

    # Blade directives (with or without parentheses)
    BLADE_DIRECTIVE_PATTERN = r"@\w+"  # @if, @foreach, @endif, @endforeach, etc.

    # Blade directives with parentheses (generic pattern for all directives with arguments)
    # Matches @directiveName( where directiveName is one or more word characters
    # Examples: @include(, @class(, @push(, @component(, @slot(, etc.
    BLADE_DIRECTIVE_WITH_ARGS_PATTERN = r"@\w+\s*\("

    # Pattern to detect if string contains Blade syntax
    BLADE_SYNTAX_PATTERN = re.compile(
        r"@\w+|"  # Blade directives
        r"\{\{.*?\}\}|"  # {{ }}
        r"\{!!.*?!!\}|"  # {!! !!}
        r"<\?php|"  # PHP open tag
        r"\?\>"  # PHP close tag
    )

    def __init__(self, file_path: Path, min_bytes: int):
        """
        Initialize the processor.

        Args:
            file_path: Path to the Blade template file
            min_bytes: Minimum byte length for string extraction
        """
        self.file_path = file_path
        self.min_bytes = min_bytes
        self.content = ""
        self.excluded_ranges: Set[Tuple[int, int]] = set()
        self.php_ranges = []  # List of (start_pos, end_pos) tuples for PHP blocks
        self.php_analyzer = PHPAnalyzer(min_bytes)

    def process(self) -> List[ExtractedString]:
        """
        Process the Blade file and extract hardcoded strings.

        Processing flow:
        1. Read file content
        2. Extract PHP block ranges (<?php...?>, @php...@endphp) - calculated once, reused everywhere
        3. Extract Blade directive argument ranges (@include, @component, etc.)
        4. Remove comments for HTML parsing
        5. Identify excluded ranges for post-extraction filtering
        6. Extract strings from HTML content (NO MASKING - parse original content)
        7. Extract strings from PHP blocks and directive arguments (using PHPAnalyzer)
        8. Filter results based on excluded ranges and patterns
        9. Combine and return results

        Returns:
            List of ExtractedString objects
        """
        # Read file content
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.content = f.read()

        # Step 1: Extract PHP code ranges ONCE - will be reused by:
        # - _identify_excluded_ranges() to mark PHP blocks as excluded
        # - _extract_from_php_blocks() to extract strings from PHP code
        # - _extract_from_html() to avoid parsing PHP as HTML
        self.php_ranges = PHPAnalyzer.extract_php_ranges(self.content, detect_blade=True)

        # Step 2: Remove comments for cleaner HTML parsing
        cleaned_content = self._remove_comments(self.content)

        # Step 3: Identify excluded ranges (translation functions, variables, directives, etc.)
        self._identify_excluded_ranges(cleaned_content)

        # Step 4: Extract from HTML content (NO MASKING - parse original content)
        # The parser will see Blade directives, but we'll filter them out afterwards
        html_results = self._extract_from_html(cleaned_content)

        # Step 5: Extract from PHP blocks (already validated by PHPAnalyzer)
        php_results = self._extract_from_php_blocks()

        # Step 6: Filter HTML results based on excluded ranges and patterns
        filtered_html_results = []
        for text, line, column, _length in html_results:
            # Strip whitespace and adjust position
            stripped_text, adjusted_column, stripped_length = StringProcessor.adjust_text_position(text, column)

            # Skip if empty after stripping
            if not stripped_text:
                continue

            # Check if text should be excluded (Blade syntax, etc.)
            if self._should_exclude_text(stripped_text):
                continue

            # Check if position is in excluded range (translation functions, variables, PHP blocks)
            pos = StringProcessor.get_position_from_line_column(self.content, line, adjusted_column)
            if self._is_in_excluded_range(pos):
                continue

            filtered_html_results.append(ExtractedString(stripped_text, line, adjusted_column, stripped_length))

        # Step 7: Convert PHP results to ExtractedString and combine
        php_extracted = [ExtractedString(text, line, column, length) for text, line, column, length in php_results]

        return filtered_html_results + php_extracted

    def _extract_from_php_blocks(self) -> List[Tuple[str, int, int, int]]:
        """
        Extract strings from PHP code blocks in Blade templates.

        Returns:
            List of tuples: (text, line, column, length)
        """
        results = []

        # Process each PHP range
        for start_pos, end_pos in self.php_ranges:
            # Extract PHP block content
            php_content = self.content[start_pos:end_pos]

            # Use PHPAnalyzer to extract and validate strings
            validated_strings = self.php_analyzer.extract_and_validate_strings(php_content, StringProcessor.should_extract_string)

            # Convert relative positions to absolute positions in the original file
            for text, relative_line, relative_column, length in validated_strings:
                # Calculate absolute position
                relative_pos = StringProcessor.get_position_from_line_column(php_content, relative_line, relative_column)
                absolute_pos = start_pos + relative_pos
                absolute_line, absolute_column = StringProcessor.get_line_column(self.content, absolute_pos)

                results.append((text, absolute_line, absolute_column, length))

        return results

    def _should_exclude_text(self, text: str) -> bool:
        """
        Check if text should be excluded from extraction.

        This method checks for:
        - Blade syntax ({{, {!!, @directives)
        - Translation function calls (__(), trans(), etc.)
        - Variable expansions ($variable)
        - PHP code snippets

        Args:
            text: Text to check

        Returns:
            True if text should be excluded
        """
        # Exclude if contains Blade syntax
        if self.BLADE_SYNTAX_PATTERN.search(text):
            return True

        # Exclude translation function calls
        for pattern in self.BLADE_TRANSLATION_PATTERNS:
            if re.search(pattern, text):
                return True

        # Exclude variable expansions
        for pattern in self.BLADE_VARIABLE_PATTERNS:
            if re.search(pattern, text):
                return True

        # Use common validation logic (inverted - should_extract returns True if we want it)
        return not StringProcessor.should_extract_string(text, self.min_bytes)

    def _remove_comments(self, content: str) -> str:
        """
        Remove HTML and Blade comments.

        Args:
            content: Original content

        Returns:
            Content with comments removed
        """
        # Remove Blade comments {{-- ... --}}
        content = re.sub(r"\{\{--.*?--\}\}", "", content, flags=re.DOTALL)

        # Remove HTML comments <!-- ... -->
        content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)

        return content

    def _identify_excluded_ranges(self, content: str) -> None:
        """
        Identify position ranges that should be excluded from extraction.

        This method marks ranges in the original content that contain:
        - Translation functions ({{ __() }}, @lang(), etc.)
        - Variable expansions ({{ $var }})
        - Blade directives (@if, @endif, etc.)
        - Blade directives with array arguments (@include, @component, etc.)
        - PHP blocks (<?php...?>, @php...@endphp)
        - <style> tags (CSS code - never internationalized)

        NOTE: <script> tags are NOT excluded because they may contain
        internationalized strings passed from PHP side.

        These ranges are used in process() to filter out extracted strings
        that fall within excluded positions.

        Args:
            content: Cleaned content (comments removed, but Blade syntax intact)
        """
        self.excluded_ranges = set()

        # Find and exclude <style> tags (CSS code should never be extracted)
        # Match <style...>...</style> including multiline content
        for match in re.finditer(r"<style[^>]*>.*?</style>", content, re.DOTALL | re.IGNORECASE):
            self.excluded_ranges.add((match.start(), match.end()))

        # Find translation functions
        for pattern in self.BLADE_TRANSLATION_PATTERNS:
            for match in re.finditer(pattern, content):
                start = match.start()
                # Find the closing bracket/brace
                end = self._find_closing_bracket(content, start)
                if end > start:
                    self.excluded_ranges.add((start, end))

        # Find variable expansions
        for pattern in self.BLADE_VARIABLE_PATTERNS:
            for match in re.finditer(pattern, content):
                start = match.start()
                end = self._find_closing_bracket(content, start)
                if end > start:
                    self.excluded_ranges.add((start, end))

        # Find Blade directives with arguments (special handling)
        # These will be parsed as PHP code to exclude array keys
        for match in re.finditer(self.BLADE_DIRECTIVE_WITH_ARGS_PATTERN, content):
            start = match.start()
            # Find the closing parenthesis for the directive arguments
            end = self._find_closing_parenthesis(content, match.end() - 1)
            if end > start:
                self.excluded_ranges.add((start, end + 1))  # +1 to include closing )

        # Find other Blade directives (without arguments)
        for match in re.finditer(self.BLADE_DIRECTIVE_PATTERN, content):
            # Skip if already covered by directives with arrays
            already_excluded = False
            for start, end in self.excluded_ranges:
                if start <= match.start() < end:
                    already_excluded = True
                    break

            if not already_excluded:
                self.excluded_ranges.add((match.start(), match.end()))

        # Add PHP blocks from pre-calculated ranges
        for start, end in self.php_ranges:
            self.excluded_ranges.add((start, end))

    def _find_closing_bracket(self, content: str, start: int) -> int:
        """Find closing bracket/brace for a function call or variable expansion."""
        # Look for opening {{ or {!!
        i = start
        while i < len(content) and content[i] not in ("(", "{"):
            i += 1

        if i >= len(content):
            return start

        # If we found a parenthesis, match it first
        if content[i] == "(":
            depth = 1
            i += 1
            while i < len(content) and depth > 0:
                if content[i] == "(":
                    depth += 1
                elif content[i] == ")":
                    depth -= 1
                i += 1

        # Find closing }} or !!}
        while i < len(content):
            if content[i : i + 2] == "}}" or content[i : i + 3] == "!!}":
                return i + (2 if content[i : i + 2] == "}}" else 3)
            i += 1

        return i

    def _find_closing_parenthesis(self, content: str, start: int) -> int:
        """
        Find closing parenthesis for a function call or directive.

        Handles nested parentheses and string literals within the arguments.

        Args:
            content: Content to search in
            start: Starting position (should be at or just before opening '(')

        Returns:
            Position of closing ')', or -1 if not found
        """
        # Find opening parenthesis
        i = start
        while i < len(content) and content[i] != "(":
            i += 1

        if i >= len(content):
            return -1

        # Skip the opening parenthesis
        i += 1
        depth = 1

        while i < len(content) and depth > 0:
            char = content[i]

            # Handle string literals (skip their contents)
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

            # Track nesting depth
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1

            i += 1

        if depth == 0:
            return i - 1  # Return position of closing ')'
        else:
            return -1  # Unmatched parenthesis

    def _is_in_excluded_range(self, pos: int) -> bool:
        """Check if a position is within an excluded range."""
        for start, end in self.excluded_ranges:
            if start <= pos < end:
                return True
        return False

    def _extract_from_html(self, content: str) -> List[Tuple[str, int, int, int]]:
        """
        Extract strings from HTML content.

        NOTE: This method now parses the ORIGINAL content without masking Blade directives.
        Filtering of Blade syntax is done afterwards in process() using _should_exclude_text()
        and _is_in_excluded_range() checks.

        <style> tags are completely excluded from extraction as they contain CSS code
        which should never be internationalized.

        <script> tags are NOT excluded because they may contain internationalized strings
        passed from PHP side (e.g., JavaScript variables with translated text).

        Args:
            content: Cleaned HTML content (comments removed, but Blade syntax intact)

        Returns:
            List of tuples: (text, line, column, length)
        """
        results = []

        try:
            # Parse HTML content directly (no masking)
            # BeautifulSoup will treat Blade directives as text, which we'll filter later
            soup = BeautifulSoup(content, "lxml")

            # Extract text nodes
            results.extend(self._extract_text_nodes(soup))

            # Extract attribute values
            results.extend(self._extract_attributes(soup))

            # Extract JavaScript strings from <script> tags
            # These may contain internationalized strings from PHP
            results.extend(self._extract_script_strings(soup))

        except Exception:
            # If parsing fails, return empty results
            pass

        return results

    def _find_all_occurrences(self, text: str) -> List[Tuple[int, int, int]]:
        """
        Find all occurrences of text in original content.

        Args:
            text: Text to search for

        Returns:
            List of tuples: (line, column, length)
        """
        results = []
        search_pos = 0
        text_length = len(text)

        while True:
            pos = self.content.find(text, search_pos)
            if pos == -1:
                break

            line, column = StringProcessor.get_line_column(self.content, pos)
            results.append((line, column, text_length))
            search_pos = pos + text_length

        return results

    def _extract_text_nodes(self, soup: BeautifulSoup) -> List[Tuple[str, int, int, int]]:
        """Extract text nodes from HTML."""
        results = []

        for element in soup.descendants:
            if isinstance(element, NavigableString) and not isinstance(element, Comment):
                text = str(element)

                # Skip empty or whitespace-only strings
                if not text or text.isspace():
                    continue

                # Split text by newlines to handle multi-line text nodes
                # Each line will be processed separately
                for line_text in text.splitlines():
                    # Strip whitespace from the line
                    stripped_line = line_text.strip()

                    # Skip empty lines
                    if not stripped_line:
                        continue

                    # Find all occurrences of the stripped text in original content
                    for line, column, length in self._find_all_occurrences(stripped_line):
                        results.append((stripped_line, line, column, length))

        return results

    def _extract_attributes(self, soup: BeautifulSoup) -> List[Tuple[str, int, int, int]]:
        """Extract attribute values from HTML tags."""
        results = []

        # Attributes that typically contain user-visible text
        text_attributes = ["placeholder", "title", "alt", "value", "aria-label", "data-title"]

        for tag in soup.find_all(True):
            if not isinstance(tag, Tag):
                continue

            for attr_name in text_attributes:
                if attr_name in tag.attrs:
                    attr_value = tag.attrs[attr_name]

                    if isinstance(attr_value, str) and attr_value and not attr_value.isspace():
                        # Find pattern with attribute name and quotes
                        search_pattern = f'{attr_name}="{attr_value}"'
                        search_pos = 0

                        while True:
                            pos = self.content.find(search_pattern, search_pos)
                            if pos == -1:
                                break

                            # Position of value (after =" )
                            value_pos = pos + len(attr_name) + 2
                            line, column = StringProcessor.get_line_column(self.content, value_pos)
                            results.append((attr_value, line, column, len(attr_value)))

                            search_pos = pos + len(search_pattern)

        return results

    def _extract_script_strings(self, soup: BeautifulSoup) -> List[Tuple[str, int, int, int]]:
        """
        Extract string literals from <script> tags.

        Unlike <style> tags (which contain only CSS), <script> tags may contain
        internationalized strings passed from PHP side. Therefore, we extract
        string literals from JavaScript code.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of tuples: (text, line, column, length)
        """
        results = []

        for script in soup.find_all("script"):
            script_content = script.string
            if not script_content:
                continue

            # Find the position of this script tag in the ORIGINAL content
            # We need to find where this specific script tag's content appears
            script_tag_str = str(script)
            script_tag_pos = self.content.find(script_tag_str)
            if script_tag_pos == -1:
                continue

            # Find where the script content starts within the tag
            # Look for the > after <script...> and before </script>
            script_opening_end = self.content.find(">", script_tag_pos)
            if script_opening_end == -1:
                continue

            script_content_start = script_opening_end + 1

            # Find JavaScript string literals
            # Match both single and double quoted strings
            string_pattern = r'(["\'])(?:(?=(\\?))\2.)*?\1'

            for match in re.finditer(string_pattern, script_content):
                string_with_quotes = match.group(0)
                # Remove quotes
                string_value = string_with_quotes[1:-1]

                if string_value and not string_value.isspace():
                    # Check if this is a JavaScript function argument
                    # Look for patterns like: functionName('string') or object.method('string')
                    match_start = match.start()
                    before_string = script_content[:match_start].rstrip()

                    # Skip if it's a function call argument
                    # Patterns: func( 'string' or func('string' or object.method( 'string'
                    if re.search(r"[\w\.]\s*\($", before_string):
                        continue

                    # Find position in ORIGINAL content, starting from this script tag's content
                    # Search within a reasonable range from the script content start
                    search_start = script_content_start
                    search_end = script_content_start + len(script_content) + 1000  # Add buffer for safety
                    pos = self.content.find(string_with_quotes, search_start, search_end)

                    if pos != -1 and not self._is_in_excluded_range(pos):
                        # Position of string content (excluding quotes)
                        value_pos = pos + 1
                        line, column = StringProcessor.get_line_column(self.content, value_pos)
                        results.append((string_value, line, column, len(string_value)))

        return results
