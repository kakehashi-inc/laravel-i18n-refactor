"""
PHP file processor for extracting hardcoded strings.
"""

from typing import List, Tuple
from pathlib import Path
from ..data_models.extracted_string import ExtractedString
from ..utils.php_string_extractor import PHPStringExtractor


class PHPProcessor:
    """Processes PHP files to extract hardcoded strings."""

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
        self.php_extractor = PHPStringExtractor(min_bytes)  # Shared PHP string extractor
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
        string_literals = self.php_extractor.extract_string_literals(self.content)

        # Filter and clean based on context
        results = []
        for text, line, column, _length in string_literals:
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

    def _should_include_string(self, text: str, content: str, line: int, column: int) -> bool:
        """
        Determine if a string should be included based on context.

        This method adds PHP block awareness on top of the common PHP string extractor logic.

        Args:
            text: The string content
            content: Full file content
            line: Line number (1-based)
            column: Column number (0-based)

        Returns:
            True if the string should be included
        """
        # Calculate position in content
        position = self.php_extractor.get_position_from_line_column(content, line, column)
        if position == -1:
            return True  # Can't determine position, include by default

        # Only apply PHP-specific exclusions if the string is within a PHP block
        if not self._is_in_php_block(position):
            return True  # Outside PHP blocks, include the string

        # Delegate to common PHP string extractor for validation
        return self.php_extractor.should_include_string(text, content, line, column)
