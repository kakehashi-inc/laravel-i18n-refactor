"""
String occurrence data class.
"""

from typing import Any, Dict, List, Optional


class StringOccurrence:
    """Represents a single occurrence of a string."""

    def __init__(self, line: int, column: int, length: int, context: Optional[List[str]] = None):
        """
        Initialize a string occurrence.

        Args:
            line: Line number (1-based)
            column: Column number (0-based)
            length: Length of the string in characters
            context: Optional list of context lines (including the target line)
        """
        self.line = line
        self.column = column
        self.length = length
        self.context = context

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result: Dict[str, Any] = {"line": self.line, "column": self.column, "length": self.length}
        if self.context is not None:
            result["context"] = self.context
        return result
