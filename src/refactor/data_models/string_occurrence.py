"""
String occurrence data class.
"""

from typing import Dict


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
