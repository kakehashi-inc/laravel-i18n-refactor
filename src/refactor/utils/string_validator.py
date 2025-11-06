"""
String validation utilities for Laravel i18n refactoring.

Provides common validation logic shared between Blade and PHP processors.
"""


def _contains_non_ascii(text: str) -> bool:
    """
    Check if string contains non-ASCII characters (e.g., Japanese, Chinese, emoji).

    Args:
        text: String to check

    Returns:
        True if string contains any character with code > 127
    """
    return any(ord(char) > 127 for char in text)


def should_extract_string(text: str, min_bytes: int) -> bool:
    """
    Determine if a string should be extracted for translation.

    Creates a temporary copy of the string and removes:
    - Half-width digits (0-9)
    - Half-width symbols (ASCII non-alphanumeric characters)
    - Spaces, tabs, CR, LF

    Also excludes strings starting with symbols that cannot be at the beginning
    of sentences or words: # , / $ .

    For strings containing only ASCII characters, excludes strings with byte length
    less than min_bytes. However, strings containing non-ASCII characters (e.g.,
    Japanese, Chinese, emoji) are always extracted regardless of byte length.

    If nothing remains after removal, the string is excluded.
    If anything remains, the string should be extracted.

    Args:
        text: String to validate
        min_bytes: Minimum byte length (only applies to ASCII-only strings)

    Returns:
        True if string should be extracted, False otherwise
    """
    # Empty or whitespace-only strings are excluded
    if not text or not text.strip():
        return False

    # Create a temporary copy for checking
    check_text = text.strip()

    # Check if string contains non-ASCII characters
    has_non_ascii = _contains_non_ascii(check_text)

    # Check minimum byte length only for ASCII-only strings
    # Non-ASCII strings (e.g., Japanese, emoji) bypass this check
    if not has_non_ascii and len(check_text.encode("utf-8")) < min_bytes:
        return False

    # Exclude regex patterns (e.g., (?:, (?=, (?!, [0-9], \d, \w, etc.)
    regex_patterns = [
        "(?:",  # non-capturing group
        "(?=",  # positive lookahead
        "(?!",  # negative lookahead
        "(?<",  # lookbehind
        "\\d",
        "\\w",
        "\\s",
        "\\b",  # escape sequences
        "^[",
        "^\\",  # start anchors with character class or escape
    ]
    for pattern in regex_patterns:
        if check_text.startswith(pattern):
            return False

    # Exclude strings starting with symbols that cannot be at the beginning of sentences/words
    # These are: # , / $ . and various punctuation marks
    # This applies to all strings, regardless of whether they contain non-ASCII characters
    invalid_start_chars = {"#", ",", "/", "$", ".", "!", ":", ";", ")", "]", "}", "%", "&", "@", "?", "^", "~", "`"}
    if check_text and check_text[0] in invalid_start_chars:
        return False

    # Remove half-width digits, symbols, whitespace (space, tab, CR, LF)
    filtered_chars = []
    for char in check_text:
        char_code = ord(char)

        # Skip half-width digits (0-9: ASCII 48-57)
        if 48 <= char_code <= 57:
            continue

        # Skip whitespace (space, tab, CR, LF)
        if char in (" ", "\t", "\r", "\n"):
            continue

        # Skip half-width symbols (ASCII < 128 and not alphanumeric)
        if char_code < 128:
            # ASCII letters (a-z: 97-122, A-Z: 65-90) should be kept
            if not ((65 <= char_code <= 90) or (97 <= char_code <= 122)):
                continue

        # Keep this character (either non-ASCII or ASCII letter)
        filtered_chars.append(char)

    # If nothing remains after filtering, exclude the string
    if not filtered_chars:
        return False

    # If something remains, extract the string
    return True


def get_line_column(content: str, pos: int) -> tuple[int, int]:
    """
    Calculate line and column number for a position in content.

    Args:
        content: Full content
        pos: Position in content (0-based)

    Returns:
        Tuple of (line, column) where line is 1-based and column is 0-based
    """
    lines_before = content[:pos].split("\n")
    line = len(lines_before)
    column = len(lines_before[-1]) if lines_before else 0
    return line, column
