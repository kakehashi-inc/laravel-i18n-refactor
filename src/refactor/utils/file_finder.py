"""
File finder utility for discovering files with glob patterns.
"""

from pathlib import Path
from typing import List, Iterator, Set, Optional


# Laravel project directories to auto-exclude when composer.json is found
LARAVEL_AUTO_EXCLUDE_DIRS = [
    "bootstrap/cache",  # Bootstrap cache
    "config",  # Configuration files
    "database",  # Database files (migrations, seeds, factories)
    "lang",  # Language files
    "node_modules",  # NPM dependencies
    "public",  # Public assets (compiled/generated)
    "resources/lang",  # Language files
    "storage",  # Storage directory (logs, cache, sessions)
    "test",  # Test files
    "tests",  # Test files
    "vendor",  # Composer dependencies
    "routes",  # Route definitions
]


def get_laravel_exclude_directories(base_directory: Path) -> Set[Path]:
    """
    Find Laravel project roots and identify directories to auto-exclude.
    Looks for composer.json files to identify Laravel projects, then marks
    specific directories for exclusion.

    Args:
        base_directory: Base directory to search from

    Returns:
        Set of directory paths to auto-exclude
    """
    exclude_dirs = set()

    # Find all composer.json files (Laravel project indicators)
    for composer_file in base_directory.rglob("composer.json"):
        project_root = composer_file.parent

        # Add Laravel-specific directories relative to project root
        for dir_name in LARAVEL_AUTO_EXCLUDE_DIRS:
            exclude_path = project_root / dir_name
            if exclude_path.exists() and exclude_path.is_dir():
                exclude_dirs.add(exclude_path.resolve())

    return exclude_dirs


def should_exclude_path(path: Path, exclude_dirs: List[str], auto_exclude_dirs: Set[Path], include_hidden: bool) -> bool:
    """
    Check if a path should be excluded.

    Args:
        path: Path to check
        exclude_dirs: List of directory names to exclude (user-specified)
        auto_exclude_dirs: Set of directory paths to auto-exclude (Laravel-specific)
        include_hidden: Include hidden directories (starting with .) in search

    Returns:
        True if the path should be excluded
    """
    resolved_path = path.resolve()

    # Exclude hidden directories if include_hidden is False
    if not include_hidden:
        for parent in resolved_path.parents:
            if parent.name.startswith("."):
                return True
        if resolved_path.is_dir() and resolved_path.name.startswith("."):
            return True

    # Check if path is inside an auto-excluded directory
    for auto_exclude_dir in auto_exclude_dirs:
        try:
            resolved_path.relative_to(auto_exclude_dir)
            return True
        except ValueError:
            continue

    # Check if any parent directory matches user-specified exclude list
    for parent in resolved_path.parents:
        if parent.name in exclude_dirs:
            return True

    # Check if the path itself is a user-specified excluded directory
    if resolved_path.name in exclude_dirs:
        return True

    return False


def find_files(directory: Path, pattern: str, exclude_dirs: Optional[List[str]] = None, include_hidden: bool = False) -> List[Path]:
    """
    Find files matching a glob pattern in the specified directory.

    Args:
        directory: Base directory to search in
        pattern: Glob pattern (e.g., "**/*.php", "*.blade.php")
        exclude_dirs: List of directory names to exclude
        include_hidden: Include hidden directories (starting with .) in search

    Returns:
        List of Path objects for matching files

    Raises:
        ValueError: If directory doesn't exist or is not a directory
    """
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    # Use provided exclusions or empty list
    if exclude_dirs is None:
        exclude_dirs = []

    # Find Laravel project directories to auto-exclude
    auto_exclude_dirs = get_laravel_exclude_directories(directory)

    # Use glob to find matching files
    files = []
    for file_path in directory.glob(pattern):
        if file_path.is_file() and not should_exclude_path(file_path, exclude_dirs, auto_exclude_dirs, include_hidden):
            files.append(file_path)

    # Sort for consistent ordering
    files.sort()

    return files


def find_files_iter(directory: Path, pattern: str, exclude_dirs: Optional[List[str]] = None, include_hidden: bool = False) -> Iterator[Path]:
    """
    Find files matching a glob pattern (iterator version).

    Args:
        directory: Base directory to search in
        pattern: Glob pattern (e.g., "**/*.php", "*.blade.php")
        exclude_dirs: List of directory names to exclude
        include_hidden: Include hidden directories (starting with .) in search

    Yields:
        Path objects for matching files

    Raises:
        ValueError: If directory doesn't exist or is not a directory
    """
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    # Use provided exclusions or empty list
    if exclude_dirs is None:
        exclude_dirs = []

    # Find Laravel project directories to auto-exclude
    auto_exclude_dirs = get_laravel_exclude_directories(directory)

    # Use glob to find matching files
    all_files = sorted(directory.glob(pattern))
    for file_path in all_files:
        if file_path.is_file() and not should_exclude_path(file_path, exclude_dirs, auto_exclude_dirs, include_hidden):
            yield file_path
