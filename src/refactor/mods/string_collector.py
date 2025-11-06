"""
String collector for consolidating extracted strings.
"""

from typing import Dict, List, Tuple
from pathlib import Path


class StringOccurrence:
    """Represents a single occurrence of a string."""

    def __init__(self, line: int, column: int, length: int):
        """
        Initialize a string occurrence.

        Args:
            line: Line number (1-based)
            column: Column number (0-based)
            length: Length of the string in characters
        """
        self.line = line
        self.column = column
        self.length = length

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary format."""
        return {"line": self.line, "column": self.column, "length": self.length}


class StringCollector:
    """
    Collects and consolidates extracted strings from multiple files.

    Merges identical strings and tracks all their occurrences.
    """

    def __init__(self, base_dir: Path):
        """
        Initialize the collector.

        Args:
            base_dir: Base directory for calculating relative paths
        """
        self.base_dir = base_dir
        # Dictionary mapping text to list of (file_path, occurrences)
        self.strings: Dict[str, List[Tuple[str, List[StringOccurrence]]]] = {}

    def add_string(self, text: str, file_path: Path, line: int, column: int, length: int) -> None:
        """
        Add a string occurrence.

        Args:
            text: The extracted string content
            file_path: Path to the source file
            line: Line number (1-based)
            column: Column number (0-based)
            length: String length in characters
        """
        # Calculate relative path
        try:
            relative_path = str(file_path.relative_to(self.base_dir))
        except ValueError:
            # If file is not relative to base_dir, use absolute path
            relative_path = str(file_path)

        # Create occurrence
        occurrence = StringOccurrence(line, column, length)

        # Add to collection
        if text not in self.strings:
            self.strings[text] = []

        # Find existing file entry
        for file_entry in self.strings[text]:
            if file_entry[0] == relative_path:
                # Add to existing file's occurrences
                file_entry[1].append(occurrence)
                return

        # Create new file entry
        self.strings[text].append((relative_path, [occurrence]))

    def get_results(self) -> List[Dict]:
        """
        Get consolidated results in the output format.

        Returns:
            List of dictionaries with structure:
            [
                {
                    "text": "string content",
                    "occurrences": [
                        {
                            "file": "relative/path/to/file.php",
                            "positions": [
                                {"line": 10, "column": 5, "length": 15}
                            ]
                        }
                    ]
                }
            ]
        """
        results = []

        for text, file_occurrences in self.strings.items():
            occurrences = []

            for file_path, positions in file_occurrences:
                occurrences.append({"file": file_path, "positions": [pos.to_dict() for pos in positions]})

            results.append({"text": text, "occurrences": occurrences})

        return results

    def get_string_count(self) -> int:
        """Get the number of unique strings collected."""
        return len(self.strings)

    def get_total_occurrences(self) -> int:
        """Get the total number of string occurrences."""
        total = 0
        for file_occurrences in self.strings.values():
            for _, positions in file_occurrences:
                total += len(positions)
        return total
