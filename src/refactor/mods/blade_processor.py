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
        3. Remove comments
        4. Mask Blade directives and PHP blocks (using pre-calculated ranges)
        5. Identify excluded ranges for HTML parsing
        6. Extract strings from HTML content
        7. Extract strings from PHP blocks (using PHPStringExtractor)
        8. Combine and filter results

        Returns:
            List of ExtractedString objects
        """
        # Read file content
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.content = f.read()

        # Step 1: Extract PHP code ranges ONCE - will be reused by:
        # - _mask_blade_syntax() to remove PHP blocks from HTML parsing
        # - _identify_excluded_ranges() to mark PHP blocks as excluded
        # - _extract_from_php_blocks() to extract strings from PHP code
        self.php_ranges = PHPAnalyzer.extract_php_ranges(self.content, detect_blade=True)

        # Step 2: Remove comments
        cleaned_content = self._remove_comments(self.content)

        # Step 3: Mask Blade syntax (uses self.php_ranges)
        masked_content = self._mask_blade_syntax(cleaned_content)

        # Step 4: Identify excluded ranges (uses self.php_ranges)
        self._identify_excluded_ranges(masked_content)

        # Step 5: Extract from HTML content
        html_results = self._extract_from_html(masked_content)

        # Step 6: Extract from PHP blocks (already validated by PHPAnalyzer)
        php_results = self._extract_from_php_blocks()

        # Step 7: Filter HTML results (PHP results are already validated)
        filtered_html_results = []
        for text, line, column, _length in html_results:
            # Strip whitespace and adjust position
            stripped_text, adjusted_column, stripped_length = StringProcessor.adjust_text_position(text, column)

            # Skip if empty after stripping or contains Blade syntax
            if not stripped_text or self._should_exclude_text(stripped_text):
                continue

            filtered_html_results.append(ExtractedString(stripped_text, line, adjusted_column, stripped_length))

        # Step 8: Convert PHP results to ExtractedString and combine
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

    def _mask_blade_syntax(self, content: str) -> str:
        """
        Mask Blade directives and PHP blocks to prevent them from being extracted.

        Args:
            content: Content with comments already removed

        Returns:
            Content with Blade syntax masked
        """
        # Step 1: Mask PHP blocks using pre-calculated ranges
        # Build masked content by copying non-PHP parts
        if self.php_ranges:
            parts = []
            last_end = 0
            for start, end in self.php_ranges:
                parts.append(content[last_end:start])
                last_end = end
            parts.append(content[last_end:])
            content = "".join(parts)

        # Step 2: Mask Blade directives with parentheses (@if(...), @foreach(...), etc.)
        # Handle multi-line arguments with proper parenthesis matching
        result = []
        i = 0
        while i < len(content):
            # Check for @ directive
            if content[i] == "@" and i + 1 < len(content) and content[i + 1].isalpha():
                # Found a directive, extract the name
                j = i + 1
                while j < len(content) and (content[j].isalnum() or content[j] == "_"):
                    j += 1

                # Check if followed by opening parenthesis (skip whitespace)
                k = j
                while k < len(content) and content[k] in " \t\n\r":
                    k += 1

                if k < len(content) and content[k] == "(":
                    # Find matching closing parenthesis
                    depth = 1
                    k += 1
                    while k < len(content) and depth > 0:
                        if content[k] == "(":
                            depth += 1
                        elif content[k] == ")":
                            depth -= 1
                        k += 1
                    # Skip the entire directive with arguments
                    i = k
                else:
                    # Directive without parentheses, skip just the directive
                    i = j
            else:
                result.append(content[i])
                i += 1

        return "".join(result)

    def _should_exclude_text(self, text: str) -> bool:
        """
        Check if text should be excluded from extraction.

        Args:
            text: Text to check

        Returns:
            True if text should be excluded
        """
        # Exclude if contains Blade syntax (safety check)
        if self.BLADE_SYNTAX_PATTERN.search(text):
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

        Args:
            content: Cleaned content
        """
        self.excluded_ranges = set()

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

        # Find Blade directives
        for match in re.finditer(self.BLADE_DIRECTIVE_PATTERN, content):
            self.excluded_ranges.add((match.start(), match.end()))

        # Add PHP blocks from pre-calculated ranges
        # Note: These ranges are from the original content, not the masked content
        # This is intentional as we want to exclude these positions in original content
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

    def _is_in_excluded_range(self, pos: int) -> bool:
        """Check if a position is within an excluded range."""
        for start, end in self.excluded_ranges:
            if start <= pos < end:
                return True
        return False

    def _extract_from_html(self, content: str) -> List[Tuple[str, int, int, int]]:
        """
        Extract strings from HTML content.

        Args:
            content: Cleaned HTML content

        Returns:
            List of tuples: (text, line, column, length)
        """
        results = []

        try:
            soup = BeautifulSoup(content, "lxml")

            # Extract text nodes
            results.extend(self._extract_text_nodes(soup))

            # Extract attribute values
            results.extend(self._extract_attributes(soup))

            # Extract JavaScript strings
            results.extend(self._extract_script_strings(soup, content))

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

                # Find all occurrences in original content
                for line, column, length in self._find_all_occurrences(text):
                    results.append((text, line, column, length))

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

    def _extract_script_strings(self, soup: BeautifulSoup, content: str) -> List[Tuple[str, int, int, int]]:
        """Extract string literals from <script> tags."""
        results = []

        for script in soup.find_all("script"):
            script_content = script.string
            if not script_content:
                continue

            # Find JavaScript string literals
            # Match both single and double quoted strings
            string_pattern = r'(["\'])(?:(?=(\\?))\2.)*?\1'

            for match in re.finditer(string_pattern, script_content):
                string_with_quotes = match.group(0)
                # Remove quotes
                string_value = string_with_quotes[1:-1]

                if string_value and not string_value.isspace():
                    # Find position in original content
                    pos = content.find(string_with_quotes)
                    if pos != -1 and not self._is_in_excluded_range(pos):
                        # Position of string content (excluding quotes)
                        value_pos = pos + 1
                        line, column = StringProcessor.get_line_column(content, value_pos)
                        results.append((string_value, line, column, len(string_value)))

        return results
