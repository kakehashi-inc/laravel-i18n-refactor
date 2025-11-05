"""
PHP file processor for extracting hardcoded strings.
"""

import re
from typing import List, Tuple, Set
from pathlib import Path


class PHPProcessor:
    """Processes PHP files to extract hardcoded strings."""

    # Patterns for exclusion
    TRANSLATION_FUNCTIONS = [
        r'__\s*\(',
        r'trans\s*\(',
        r'@lang\s*\(',
        r'Lang::get\s*\(',
    ]

    LOG_FUNCTIONS = [
        r'Log::\w+\s*\(',
        r'logger\s*\(',
        r'error_log\s*\(',
    ]

    CONSOLE_OUTPUT = [
        r'\becho\s+',
        r'\bprint\s+',
        r'\bvar_dump\s*\(',
        r'\bdd\s*\(',
        r'\bdump\s*\(',
        r'\bprint_r\s*\(',
    ]

    COMMAND_OUTPUT = [
        r'\$this->info\s*\(',
        r'\$this->error\s*\(',
        r'\$this->line\s*\(',
        r'\$this->comment\s*\(',
        r'\$this->warn\s*\(',
        r'\$this->warning\s*\(',
    ]

    def __init__(self, file_path: Path):
        """
        Initialize the processor.

        Args:
            file_path: Path to the PHP file
        """
        self.file_path = file_path
        self.content = ""

    def process(self) -> List[Tuple[str, int, int, int]]:
        """
        Process the PHP file and extract hardcoded strings.

        Returns:
            List of tuples: (text, line, column, length)
        """
        # Read file content
        with open(self.file_path, 'r', encoding='utf-8') as f:
            self.content = f.read()

        # Remove all comments
        cleaned_content = self._remove_comments(self.content)

        # Extract all string literals with positions
        string_literals = self._extract_string_literals(cleaned_content)

        # Filter based on context
        results = []
        for text, line, column, length in string_literals:
            if self._should_include_string(text, cleaned_content, line, column):
                results.append((text, line, column, length))

        return results

    def _remove_comments(self, content: str) -> str:
        """
        Remove all PHP comments.

        Args:
            content: Original content

        Returns:
            Content with comments removed
        """
        # Remove multi-line comments /* ... */ and /** ... */
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # Remove single-line comments // ...
        content = re.sub(r'//[^\n]*', '', content)

        # Remove shell-style comments # ...
        content = re.sub(r'#[^\n]*', '', content)

        return content

    def _extract_string_literals(self, content: str) -> List[Tuple[str, int, int, int]]:
        """
        Extract all string literals from PHP code.

        Args:
            content: PHP content with comments removed

        Returns:
            List of tuples: (text, line, column, length)
        """
        results = []

        # Pattern for single-quoted strings
        single_quote_pattern = r"'([^'\\]*(\\.[^'\\]*)*)'"

        # Pattern for double-quoted strings
        double_quote_pattern = r'"([^"\\]*(\\.[^"\\]*)*)"'

        # Extract single-quoted strings
        for match in re.finditer(single_quote_pattern, content):
            string_content = match.group(1)
            if string_content and not string_content.isspace():
                pos = match.start() + 1  # Position after opening quote
                line, column = self._get_line_column(content, pos)
                results.append((string_content, line, column, len(string_content)))

        # Extract double-quoted strings
        for match in re.finditer(double_quote_pattern, content):
            string_content = match.group(1)
            if string_content and not string_content.isspace():
                pos = match.start() + 1  # Position after opening quote
                line, column = self._get_line_column(content, pos)
                results.append((string_content, line, column, len(string_content)))

        return results

    def _should_include_string(
        self,
        text: str,
        content: str,
        line: int,
        column: int
    ) -> bool:
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
        # Skip empty or whitespace-only strings
        if not text or text.isspace():
            return False

        # Get the context around this string
        pos = self._get_position_from_line_column(content, line, column)
        if pos == -1:
            return False

        # Get some context before the string (up to 200 characters)
        context_start = max(0, pos - 200)
        context = content[context_start:pos]

        # Check for translation functions
        for pattern in self.TRANSLATION_FUNCTIONS:
            if re.search(pattern, context):
                return False

        # Check for log functions
        for pattern in self.LOG_FUNCTIONS:
            if re.search(pattern, context):
                return False

        # Check for console output
        for pattern in self.CONSOLE_OUTPUT:
            if re.search(pattern, context):
                return False

        # Check for command output
        for pattern in self.COMMAND_OUTPUT:
            if re.search(pattern, context):
                return False

        # Check if it's an array key
        # Pattern: 'key' => or "key" =>
        if re.search(r'[\'"]' + re.escape(text) + r'[\'"]\s*=>', content[pos-50:pos+len(text)+10]):
            return False

        # Check for namespace, use, class name, const, function definitions
        # These typically appear at the beginning of lines or after specific keywords
        if re.search(r'\b(namespace|use|class|interface|trait|const|function)\s+[\'"]?' + re.escape(text), context):
            return False

        return True

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
        lines = content.split('\n')
        if line < 1 or line > len(lines):
            return -1

        # Calculate position
        pos = sum(len(lines[i]) + 1 for i in range(line - 1))  # +1 for newline
        pos += column

        if pos >= len(content):
            return -1

        return pos
