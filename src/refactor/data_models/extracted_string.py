"""
Extracted string data class.
"""


class ExtractedString:
    """Represents an extracted string with its position information."""

    def __init__(self, text: str, line: int, column: int, length: int):
        """
        Initialize an extracted string.

        Args:
            text: The extracted string content
            line: Line number (1-based)
            column: Column number (0-based)
            length: Length of the string in characters
        """
        self.text = text
        self.line = line
        self.column = column
        self.length = length

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ExtractedString(text={self.text!r}, line={self.line}, column={self.column}, length={self.length})"
