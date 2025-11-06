"""
PHP file processor for extracting hardcoded strings.
"""

from typing import List
from pathlib import Path
from ..data_models.extracted_string import ExtractedString
from ..utils.php_analyzer import PHPAnalyzer
from ..utils.string_processor import StringProcessor


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
        self.php_analyzer = PHPAnalyzer(min_bytes)

    def process(self) -> List[ExtractedString]:
        """
        Process the PHP file and extract hardcoded strings.

        For .php files, the entire file is treated as PHP code.
        All string literals are extracted and validated using PHPAnalyzer.

        Returns:
            List of ExtractedString objects
        """
        # Read file content
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.content = f.read()

        # Extract and validate strings in one step
        validated_strings = self.php_analyzer.extract_and_validate_strings(self.content, StringProcessor.should_extract_string)

        # Convert to ExtractedString objects
        return [ExtractedString(text, line, column, length) for text, line, column, length in validated_strings]
