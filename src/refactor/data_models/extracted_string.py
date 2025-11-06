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

    def to_tuple(self) -> tuple:
        """
        Convert to tuple format for backward compatibility.

        Returns:
            Tuple of (text, line, column, length)
        """
        return (self.text, self.line, self.column, self.length)

    @classmethod
    def from_tuple(cls, data: tuple) -> "ExtractedString":
        """
        Create from tuple format.

        Args:
            data: Tuple of (text, line, column, length)

        Returns:
            ExtractedString instance
        """
        return cls(data[0], data[1], data[2], data[3])

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ExtractedString(text={self.text!r}, line={self.line}, column={self.column}, length={self.length})"
