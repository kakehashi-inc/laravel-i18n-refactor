"""
Extract action for extracting hardcoded strings from Laravel files.
"""

import sys
import os
from pathlib import Path
from typing import Optional, List

from refactor.utils.file_finder import find_files_iter
from refactor.utils.output_formatter import format_output
from refactor.mods.string_collector import StringCollector
from refactor.mods.blade_processor import BladeProcessor
from refactor.mods.php_processor import PHPProcessor


def truncate_path(path_str: str, max_width: int) -> str:
    """
    Truncate a file path to fit within max_width by removing the middle part.

    Args:
        path_str: The file path string
        max_width: Maximum width in characters

    Returns:
        Truncated path string
    """
    if len(path_str) <= max_width:
        return path_str

    if max_width < 10:
        # Too narrow, just truncate
        return path_str[:max_width]

    # Calculate how much to keep on each side
    # Reserve 3 chars for "..."
    available = max_width - 3
    left_side = available // 2
    right_side = available - left_side

    return f"{path_str[:left_side]}...{path_str[-right_side:]}"


def extract_strings(
    directory: Path,
    pattern: str,
    output_path: Optional[Path],
    exclude_dirs: Optional[List[str]],
    split_threshold: int,
    min_bytes: int,
) -> int:
    """
    Extract hardcoded strings from Laravel project files.

    Args:
        directory: Target directory to search for files
        pattern: File name pattern (e.g., "**/*.php", "**/*.blade.php")
        output_path: Output JSON file path, or None for stdout
        exclude_dirs: List of directory names to exclude
        split_threshold: Threshold for splitting output into multiple files
        min_bytes: Minimum byte length for string extraction

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Validate directory
        if not directory.exists():
            print(f"Error: Directory does not exist: {directory}", file=sys.stderr)
            return 1

        if not directory.is_dir():
            print(f"Error: Path is not a directory: {directory}", file=sys.stderr)
            return 1

        # Use provided exclusions or empty list
        if exclude_dirs is None:
            exclude_dirs = []

        # Initialize collector
        collector = StringCollector(directory)

        # Find files
        print("Searching for files...", file=sys.stderr)
        try:
            files = list(find_files_iter(directory, pattern, exclude_dirs))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        if not files:
            print(f"Warning: No files found matching pattern '{pattern}' in {directory}", file=sys.stderr)
            # Still output empty results
            format_output([], output_path, split_threshold)
            return 0

        print(f"Found {len(files)} files to process", file=sys.stderr)

        # Process each file
        print("Processing files...", file=sys.stderr)
        processed_count = 0
        error_count = 0
        total_files = len(files)

        # Get terminal width (default to 80 if not available)
        try:
            terminal_width = os.get_terminal_size().columns
        except (AttributeError, OSError):
            terminal_width = 80

        for index, file_path in enumerate(files, 1):
            try:
                # Show progress: display current file being processed
                # Use relative path from directory for cleaner display
                try:
                    relative_path = file_path.relative_to(directory)
                except ValueError:
                    relative_path = file_path

                # Format progress: [count/total] filepath
                counter = f"[{index}/{total_files}]"
                path_str = str(relative_path)

                # Calculate available width for the path
                # Reserve space for counter + 1 space, and leave 2 chars margin
                available_width = terminal_width - len(counter) - 1 - 2

                if available_width > 0:
                    truncated_path = truncate_path(path_str, available_width)
                    progress_msg = f"{counter} {truncated_path}"
                else:
                    # Terminal too narrow, just show counter
                    progress_msg = counter

                # Display progress with carriage return to overwrite the same line
                # \033[K clears from cursor to end of line
                print(f"\r\033[K{progress_msg}", end="", flush=True, file=sys.stderr)

                # Determine file type and process accordingly
                if file_path.suffix == ".php" and ".blade.php" in file_path.name:
                    # Blade template
                    results = process_blade_file(file_path, collector, min_bytes)
                elif file_path.suffix == ".php":
                    # Regular PHP file
                    results = process_php_file(file_path, collector, min_bytes)
                else:
                    # Skip non-PHP files
                    continue

                processed_count += 1

            except Exception as e:
                error_count += 1
                # Clear the progress line before printing error
                print("\r\033[K", end="", file=sys.stderr)
                print(f"Warning: Failed to process {file_path}: {e}", file=sys.stderr)
                continue

        # Clear the progress line after processing all files
        print("\r\033[K", end="", file=sys.stderr)

        # Get consolidated results
        print("Consolidating results...", file=sys.stderr)
        results = collector.get_results()

        # Output results
        print("Writing output...", file=sys.stderr)
        format_output(results, output_path, split_threshold)

        # Print summary to stderr
        print(f"\nProcessed {processed_count} files", file=sys.stderr)
        print(f"Found {collector.get_string_count()} unique strings", file=sys.stderr)
        print(f"Total occurrences: {collector.get_total_occurrences()}", file=sys.stderr)

        if error_count > 0:
            print(f"Errors: {error_count} files failed to process", file=sys.stderr)

        return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def process_blade_file(file_path: Path, collector: StringCollector, min_bytes: int) -> int:
    """
    Process a Blade template file.

    Args:
        file_path: Path to the Blade file
        collector: StringCollector instance
        min_bytes: Minimum byte length for string extraction

    Returns:
        Number of strings extracted
    """
    processor = BladeProcessor(file_path, min_bytes)
    results = processor.process()

    for text, line, column, length in results:
        collector.add_string(text, file_path, line, column, length)

    return len(results)


def process_php_file(file_path: Path, collector: StringCollector, min_bytes: int) -> int:
    """
    Process a PHP file.

    Args:
        file_path: Path to the PHP file
        collector: StringCollector instance
        min_bytes: Minimum byte length for string extraction

    Returns:
        Number of strings extracted
    """
    processor = PHPProcessor(file_path, min_bytes)
    results = processor.process()

    for text, line, column, length in results:
        collector.add_string(text, file_path, line, column, length)

    return len(results)
