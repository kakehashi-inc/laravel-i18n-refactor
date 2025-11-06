"""
Blade template processor for extracting hardcoded strings.
"""

import re
from typing import List, Tuple, Set
from pathlib import Path
from bs4 import BeautifulSoup, Comment, Tag
from bs4.element import NavigableString


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

    def __init__(self, file_path: Path):
        """
        Initialize the processor.

        Args:
            file_path: Path to the Blade template file
        """
        self.file_path = file_path
        self.content = ""
        self.excluded_ranges: Set[Tuple[int, int]] = set()

    def process(self) -> List[Tuple[str, int, int, int]]:
        """
        Process the Blade file and extract hardcoded strings.

        Returns:
            List of tuples: (text, line, column, length)
        """
        # Read file content
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.content = f.read()

        # Remove comments first
        cleaned_content = self._remove_comments(self.content)

        # Remove/mask Blade syntax before HTML parsing
        masked_content = self._mask_blade_syntax(cleaned_content)

        # Identify excluded ranges (Blade constructs) - still needed for {{ }} patterns
        self._identify_excluded_ranges(masked_content)

        # Parse HTML and extract strings
        results = self._extract_from_html(masked_content)

        # Filter and clean extracted strings
        filtered_results = []
        for text, line, column, length in results:
            # Strip leading/trailing whitespace for validation
            stripped_text = text.strip()

            # Skip if empty after stripping or contains Blade syntax
            if not stripped_text or self._should_exclude_text(stripped_text):
                continue

            # Use the stripped text for output
            # Recalculate position and length based on stripped text
            stripped_length = len(stripped_text)

            # Find the position of the first non-whitespace character
            leading_whitespace = len(text) - len(text.lstrip())
            adjusted_column = column + leading_whitespace

            filtered_results.append((stripped_text, line, adjusted_column, stripped_length))

        return filtered_results

    def _mask_blade_syntax(self, content: str) -> str:
        """
        Mask Blade directives and PHP blocks to prevent them from being extracted.

        Args:
            content: Content with comments already removed

        Returns:
            Content with Blade syntax masked
        """
        # Mask Blade directives with parentheses (@if(...), @foreach(...), etc.)
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

        content = "".join(result)

        # Mask PHP blocks
        content = re.sub(r"<\?php.*?\?>", "", content, flags=re.DOTALL)
        content = re.sub(r"@php.*?@endphp", "", content, flags=re.DOTALL)

        return content

    def _should_exclude_text(self, text: str) -> bool:
        """
        Check if text should be excluded from extraction.

        Args:
            text: Text to check

        Returns:
            True if text should be excluded
        """
        # Exclude empty or whitespace-only strings
        if not text or not text.strip():
            return True

        # Exclude if contains Blade syntax (safety check)
        if self.BLADE_SYNTAX_PATTERN.search(text):
            return True

        # Exclude very short strings that are likely not translatable text
        stripped = text.strip()
        if len(stripped) <= 3:
            # Allow only if it contains Japanese or other non-ASCII characters
            if not self._contains_non_ascii(stripped):
                # Skip if it's only numbers, operators, or single characters
                if stripped.isdigit() or stripped in [
                    "!=",
                    "==",
                    "<=",
                    ">=",
                    "<",
                    ">",
                    "=",
                    "+",
                    "-",
                    "*",
                    "/",
                    "%",
                    "&",
                    "|",
                    "^",
                    "~",
                    "!",
                    "?",
                    "@",
                    "#",
                    "$",
                    "(",
                    ")",
                    "[",
                    "]",
                    "{",
                    "}",
                    ":",
                    ";",
                    ",",
                    ".",
                    "->",
                    "=>",
                    "::",
                    "..",
                    "...",
                ]:
                    return True

        # Exclude strings that look like technical identifiers (snake_case, camelCase, etc.)
        # But allow sentences with spaces
        if "_" in stripped and " " not in stripped and not self._contains_non_ascii(stripped):
            # Looks like a config key or column name: email_from_address, created_at, etc.
            if stripped.islower() or stripped.isupper():
                return True

        # Exclude strings that are all uppercase without spaces (likely constants)
        if stripped.isupper() and " " not in stripped and not self._contains_non_ascii(stripped):
            return True

        return False

    def _contains_non_ascii(self, text: str) -> bool:
        """
        Check if the text contains non-ASCII characters (e.g., Japanese).

        Args:
            text: Text to check

        Returns:
            True if text contains non-ASCII characters
        """
        return any(ord(char) > 127 for char in text)

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
                end = self._find_closing_brace(content, start)
                if end > start:
                    self.excluded_ranges.add((start, end))

        # Find Blade directives
        for match in re.finditer(self.BLADE_DIRECTIVE_PATTERN, content):
            self.excluded_ranges.add((match.start(), match.end()))

        # Find PHP blocks
        for match in re.finditer(r"<\?php.*?\?>", content, flags=re.DOTALL):
            self.excluded_ranges.add((match.start(), match.end()))

        for match in re.finditer(r"@php.*?@endphp", content, flags=re.DOTALL):
            self.excluded_ranges.add((match.start(), match.end()))

    def _find_closing_bracket(self, content: str, start: int) -> int:
        """Find closing bracket/brace for a function call."""
        # Look for {{ or {!!
        i = start
        while i < len(content) and content[i] != "(":
            i += 1

        if i >= len(content):
            return start

        # Find matching closing parenthesis
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

    def _find_closing_brace(self, content: str, start: int) -> int:
        """Find closing brace for Blade echo."""
        i = start + 2  # Skip {{ or {!!

        # Find closing }} or !!}
        while i < len(content):
            if content[i : i + 2] == "}}":
                return i + 2
            elif content[i : i + 3] == "!!}":
                return i + 3
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
            results.extend(self._extract_text_nodes(soup, content))

            # Extract attribute values
            results.extend(self._extract_attributes(soup, content))

            # Extract JavaScript strings
            results.extend(self._extract_script_strings(soup, content))

        except Exception:
            # If parsing fails, return empty results
            pass

        return results

    def _extract_text_nodes(self, soup: BeautifulSoup, content: str) -> List[Tuple[str, int, int, int]]:
        """Extract text nodes from HTML."""
        results = []

        for element in soup.descendants:
            if isinstance(element, NavigableString) and not isinstance(element, Comment):
                text = str(element)

                # Skip empty or whitespace-only strings
                if not text or text.isspace():
                    continue

                # Find position in original content
                pos = content.find(text)
                if pos == -1 or self._is_in_excluded_range(pos):
                    continue

                # Calculate line and column
                line, column = self._get_line_column(content, pos)

                results.append((text, line, column, len(text)))

        return results

    def _extract_attributes(self, soup: BeautifulSoup, content: str) -> List[Tuple[str, int, int, int]]:
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
                        # Find position in original content
                        search_pattern = f'{attr_name}="{attr_value}"'
                        pos = content.find(search_pattern)

                        if pos != -1:
                            value_pos = pos + len(attr_name) + 2  # +2 for ="

                            if not self._is_in_excluded_range(value_pos):
                                line, column = self._get_line_column(content, value_pos)
                                results.append((attr_value, line, column, len(attr_value)))

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
                        line, column = self._get_line_column(content, value_pos)
                        results.append((string_value, line, column, len(string_value)))

        return results

    def _get_line_column(self, content: str, pos: int) -> Tuple[int, int]:
        """
        Calculate line and column number for a position.

        Args:
            content: Full content
            pos: Position in content

        Returns:
            Tuple of (line, column) where line is 1-based and column is 0-based
        """
        lines_before = content[:pos].split("\n")
        line = len(lines_before)
        column = len(lines_before[-1]) if lines_before else 0
        return line, column
