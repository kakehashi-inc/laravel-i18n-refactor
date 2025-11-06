"""
Extract action for extracting hardcoded strings from Laravel files.
"""

import sys
from pathlib import Path
from typing import Optional, List

from refactor.utils.file_finder import find_files_iter
from refactor.utils.output_formatter import format_output
from refactor.mods.string_collector import StringCollector
from refactor.mods.blade_processor import BladeProcessor
from refactor.mods.php_processor import PHPProcessor


def extract_strings(directory: Path, pattern: str, output_path: Optional[Path], exclude_dirs: Optional[List[str]] = None) -> int:
    """
    Extract hardcoded strings from Laravel project files.

    Args:
        directory: Target directory to search for files
        pattern: File name pattern (e.g., "**/*.php", "**/*.blade.php")
        output_path: Output JSON file path, or None for stdout
        exclude_dirs: List of directory names to exclude

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
        try:
            files = list(find_files_iter(directory, pattern, exclude_dirs))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        if not files:
            print(f"Warning: No files found matching pattern '{pattern}' in {directory}", file=sys.stderr)
            # Still output empty results
            format_output([], output_path)
            return 0

        # Process each file
        processed_count = 0
        error_count = 0

        for file_path in files:
            try:
                # Determine file type and process accordingly
                if file_path.suffix == ".php" and ".blade.php" in file_path.name:
                    # Blade template
                    results = process_blade_file(file_path, collector)
                elif file_path.suffix == ".php":
                    # Regular PHP file
                    results = process_php_file(file_path, collector)
                else:
                    # Skip non-PHP files
                    continue

                processed_count += 1

            except Exception as e:
                error_count += 1
                print(f"Warning: Failed to process {file_path}: {e}", file=sys.stderr)
                continue

        # Get consolidated results
        results = collector.get_results()

        # Output results
        format_output(results, output_path)

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


def process_blade_file(file_path: Path, collector: StringCollector) -> int:
    """
    Process a Blade template file.

    Args:
        file_path: Path to the Blade file
        collector: StringCollector instance

    Returns:
        Number of strings extracted
    """
    processor = BladeProcessor(file_path)
    results = processor.process()

    for text, line, column, length in results:
        collector.add_string(text, file_path, line, column, length)

    return len(results)


def process_php_file(file_path: Path, collector: StringCollector) -> int:
    """
    Process a PHP file.

    Args:
        file_path: Path to the PHP file
        collector: StringCollector instance

    Returns:
        Number of strings extracted
    """
    processor = PHPProcessor(file_path)
    results = processor.process()

    for text, line, column, length in results:
        collector.add_string(text, file_path, line, column, length)

    return len(results)
