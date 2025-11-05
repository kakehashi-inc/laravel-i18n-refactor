"""
File finder utility for discovering files with glob patterns.
"""

from pathlib import Path
from typing import List, Iterator


def find_files(directory: Path, pattern: str) -> List[Path]:
    """
    Find files matching a glob pattern in the specified directory.

    Args:
        directory: Base directory to search in
        pattern: Glob pattern (e.g., "**/*.php", "*.blade.php")

    Returns:
        List of Path objects for matching files

    Raises:
        ValueError: If directory doesn't exist or is not a directory
    """
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    # Use glob to find matching files
    files = list(directory.glob(pattern))

    # Filter to only include files (not directories)
    files = [f for f in files if f.is_file()]

    # Sort for consistent ordering
    files.sort()

    return files


def find_files_iter(directory: Path, pattern: str) -> Iterator[Path]:
    """
    Find files matching a glob pattern (iterator version).

    Args:
        directory: Base directory to search in
        pattern: Glob pattern (e.g., "**/*.php", "*.blade.php")

    Yields:
        Path objects for matching files

    Raises:
        ValueError: If directory doesn't exist or is not a directory
    """
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    # Use glob to find matching files
    for file_path in sorted(directory.glob(pattern)):
        if file_path.is_file():
            yield file_path
