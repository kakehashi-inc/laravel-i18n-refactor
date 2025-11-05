"""
Blade template processor for extracting hardcoded strings.
"""

import re
from typing import List, Tuple, Set
from pathlib import Path
from bs4 import BeautifulSoup, Comment, NavigableString, Tag


class BladeProcessor:
    """Processes Blade templates to extract hardcoded strings."""

    # Patterns for Blade constructs to exclude
    BLADE_TRANSLATION_PATTERNS = [
        r'\{\{\s*__\(',          # {{ __() }}
        r'\{\{\s*trans\(',       # {{ trans() }}
        r'\{!!\s*__\(',          # {!! __() !!}
        r'\{!!\s*trans\(',       # {!! trans() !!}
        r'@lang\(',              # @lang()
    ]

    BLADE_VARIABLE_PATTERNS = [
        r'\{\{\s*\$',            # {{ $variable }}
        r'\{!!\s*\$',            # {!! $variable !!}
    ]

    BLADE_DIRECTIVE_PATTERN = r'@\w+\s*\([^)]*\)'  # @if(), @foreach(), etc.

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
        with open(self.file_path, 'r', encoding='utf-8') as f:
            self.content = f.read()

        # Remove comments first
        cleaned_content = self._remove_comments(self.content)

        # Identify excluded ranges (Blade constructs)
        self._identify_excluded_ranges(cleaned_content)

        # Parse HTML and extract strings
        results = self._extract_from_html(cleaned_content)

        return results

    def _remove_comments(self, content: str) -> str:
        """
        Remove HTML and Blade comments.

        Args:
            content: Original content

        Returns:
            Content with comments removed
        """
        # Remove Blade comments {{-- ... --}}
        content = re.sub(r'\{\{--.*?--\}\}', '', content, flags=re.DOTALL)

        # Remove HTML comments <!-- ... -->
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

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
        for match in re.finditer(r'<\?php.*?\?>', content, flags=re.DOTALL):
            self.excluded_ranges.add((match.start(), match.end()))

        for match in re.finditer(r'@php.*?@endphp', content, flags=re.DOTALL):
            self.excluded_ranges.add((match.start(), match.end()))

    def _find_closing_bracket(self, content: str, start: int) -> int:
        """Find closing bracket/brace for a function call."""
        # Look for {{ or {!!
        i = start
        while i < len(content) and content[i] != '(':
            i += 1

        if i >= len(content):
            return start

        # Find matching closing parenthesis
        depth = 1
        i += 1
        while i < len(content) and depth > 0:
            if content[i] == '(':
                depth += 1
            elif content[i] == ')':
                depth -= 1
            i += 1

        # Find closing }} or !!}
        while i < len(content):
            if content[i:i+2] == '}}' or content[i:i+3] == '!!}':
                return i + (2 if content[i:i+2] == '}}' else 3)
            i += 1

        return i

    def _find_closing_brace(self, content: str, start: int) -> int:
        """Find closing brace for Blade echo."""
        i = start + 2  # Skip {{ or {!!

        # Find closing }} or !!}
        while i < len(content):
            if content[i:i+2] == '}}':
                return i + 2
            elif content[i:i+3] == '!!}':
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
            soup = BeautifulSoup(content, 'lxml')

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
        text_attributes = ['placeholder', 'title', 'alt', 'value', 'aria-label', 'data-title']

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

        for script in soup.find_all('script'):
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
        lines_before = content[:pos].split('\n')
        line = len(lines_before)
        column = len(lines_before[-1]) if lines_before else 0
        return line, column
