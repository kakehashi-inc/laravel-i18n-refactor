"""
Extract action for extracting hardcoded strings from Laravel files.
"""

import sys
import os
import re
from pathlib import Path
from typing import Optional, List

from refactor.utils.file_finder import find_files_iter
from refactor.utils.output_formatter import format_output
from refactor.utils.string_processor import StringCollector
from refactor.utils.exclusion_dict import ExclusionMatcher
from refactor.mods.blade_processor import BladeProcessor
from refactor.mods.php_processor import PHPProcessor


def setup_extract_parser(subparsers) -> None:
    """
    Set up the extract command parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    extract_parser = subparsers.add_parser("extract", help="Extract hardcoded strings from Laravel project files")
    extract_parser.add_argument("directory", type=Path, help="Target directory to search for files")
    extract_parser.add_argument("-n", "--name", default="**/*.php", help='File name pattern (e.g., "**/*.blade.php", "*.php")')
    extract_parser.add_argument("-o", "--output", type=Path, default=None, help="Output JSON file path (default: stdout)")
    extract_parser.add_argument(
        "-e", "--exclude", action="append", dest="exclude", help="Directory names to exclude (can be specified multiple times, default: node_modules)"
    )
    extract_parser.add_argument(
        "--split-threshold",
        type=int,
        default=100,
        dest="split_threshold",
        help="Threshold for splitting output into multiple files (default: 100, only applies when output file is specified)",
    )
    extract_parser.add_argument(
        "--min-bytes",
        type=int,
        default=2,
        dest="min_bytes",
        help="Minimum byte length for extracted strings (default: 2, strings with less than 2 bytes will be excluded)",
    )
    extract_parser.add_argument(
        "--include-hidden",
        action="store_true",
        dest="include_hidden",
        help="Include hidden directories (directories starting with .) in search (default: False)",
    )
    extract_parser.add_argument(
        "--context-lines",
        type=int,
        default=5,
        dest="context_lines",
        help="Number of context lines to include in output (default: 5, means 2 before + target line + 2 after, 0 to disable)",
    )
    extract_parser.add_argument(
        "--enable-blade",
        action="store_true",
        default=True,
        dest="enable_blade",
        help="Enable processing of .blade.php files (default: True)",
    )
    extract_parser.add_argument(
        "--disable-blade",
        action="store_false",
        dest="enable_blade",
        help="Disable processing of .blade.php files",
    )
    extract_parser.add_argument(
        "--enable-php",
        action="store_true",
        default=False,
        dest="enable_php",
        help="Enable processing of regular .php files (default: False)",
    )
    extract_parser.add_argument(
        "--disable-php",
        action="store_false",
        dest="enable_php",
        help="Disable processing of regular .php files (this is the default)",
    )
    extract_parser.add_argument(
        "--exclude-dict",
        type=Path,
        default=None,
        dest="exclude_dict",
        help="Path to a text file containing strings to exclude (one per line)",
    )
    extract_parser.set_defaults(func=run_extract)


def run_extract(args) -> int:
    """
    Run the extract action.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code
    """
    # Set default exclude if not specified
    exclude_dirs = args.exclude if args.exclude else ["node_modules"]

    return extract_strings(
        directory=args.directory,
        pattern=args.name,
        output_path=args.output,
        exclude_dirs=exclude_dirs,
        split_threshold=args.split_threshold,
        min_bytes=args.min_bytes,
        include_hidden=args.include_hidden,
        context_lines=args.context_lines,
        enable_blade=args.enable_blade,
        enable_php=args.enable_php,
        exclude_dict_path=args.exclude_dict,
    )


def check_output_directory(output_path: Path) -> bool:
    """
    Check if the output directory exists and prompt user to create if not.

    Args:
        output_path: Output file path

    Returns:
        True if directory exists or user chose to create it, False otherwise
    """
    output_dir = output_path.parent

    # If directory exists, no prompt needed
    if output_dir.exists():
        return True

    # Directory doesn't exist, prompt user
    print(f"\nOutput directory does not exist: {output_dir}", file=sys.stderr)
    print("Create directory recursively? (Y/n): ", end="", flush=True, file=sys.stderr)

    try:
        response = input().strip()
    except EOFError:
        # Handle case where input is not available (e.g., piped input)
        print("\nNo input available. Cannot create directory.", file=sys.stderr)
        return False

    if response.upper() == "Y":
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {output_dir}", file=sys.stderr)
            return True
        except Exception as e:
            print(f"Error: Failed to create directory: {e}", file=sys.stderr)
            return False
    else:
        print("Operation cancelled. Directory was not created.", file=sys.stderr)
        return False


def check_and_remove_existing_files(output_path: Path) -> None:
    """
    Check if output files already exist and prompt user to delete them.
    This is an optional step - processing continues regardless of user response.

    Args:
        output_path: Output file path
    """
    output_dir = output_path.parent
    stem = output_path.stem
    suffix = output_path.suffix

    # Pattern matches both single file and split files
    # e.g., "output.json" or "output-01.json", "output-02.json", etc.
    pattern = re.compile(rf"^{re.escape(stem)}(-\d+)?{re.escape(suffix)}$")

    # Find matching files in the output directory
    existing_files = []
    if output_dir.exists():
        for file_path in output_dir.iterdir():
            if file_path.is_file() and pattern.match(file_path.name):
                existing_files.append(file_path)

    # If no existing files, no action needed
    if not existing_files:
        return

    # Display existing files and prompt for deletion
    print("\nThe following output file(s) already exist:", file=sys.stderr)
    for file_path in sorted(existing_files):
        print(f"  {file_path}", file=sys.stderr)
    print("Delete these file(s) before processing? (Y/n): ", end="", flush=True, file=sys.stderr)

    try:
        response = input().strip()
    except EOFError:
        # Handle case where input is not available (e.g., piped input)
        print("\nNo input available. Skipping file deletion.", file=sys.stderr)
        return

    if response.upper() == "Y":
        # Delete all existing files, continue even if some fail
        for file_path in existing_files:
            try:
                file_path.unlink()
            except Exception as e:
                print(f"Warning: Failed to delete {file_path}: {e}", file=sys.stderr)
                # Continue deleting other files
    else:
        print("Skipped deletion. Existing files will be overwritten.", file=sys.stderr)


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
    include_hidden: bool,
    context_lines: int,
    enable_blade: bool,
    enable_php: bool,
    exclude_dict_path: Optional[Path],
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
        include_hidden: Include hidden directories (starting with .) in search
        context_lines: Number of context lines to include (0 to disable)
        enable_blade: Enable processing of .blade.php files
        enable_php: Enable processing of regular .php files
        exclude_dict_path: Path to exclusion dictionary file

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

        # Load exclusion dictionaries
        # From src/refactor/actions/ we go up three levels to project root, then into dict/
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent
        embedded_dict_file = project_root / "dict" / "embed-exclude-dict.txt"

        # Initialize ExclusionMatcher and append embedded dictionary first
        exclude_matcher = ExclusionMatcher()
        exclude_matcher.append_from_file(embedded_dict_file)

        # Append user dictionary if provided (patterns append after embedded ones)
        if exclude_dict_path and exclude_dict_path.exists():
            exclude_matcher.append_from_file(exclude_dict_path)

        # Check output directory before processing (only if output_path is specified)
        if output_path:
            if not check_output_directory(output_path):
                print("Error: Output directory creation cancelled", file=sys.stderr)
                return 0

            # Check for existing output files and prompt for deletion (optional)
            check_and_remove_existing_files(output_path)

        # Initialize collector with prepared exclude matcher
        collector = StringCollector(exclude_matcher)

        # Find files
        print("Searching for files...", file=sys.stderr)
        try:
            files = list(find_files_iter(directory, pattern, exclude_dirs, include_hidden=include_hidden))
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
                is_blade = file_path.suffix == ".php" and ".blade.php" in file_path.name
                is_php = file_path.suffix == ".php" and ".blade.php" not in file_path.name

                if is_blade and enable_blade:
                    # Blade template
                    results = process_blade_file(file_path, collector, min_bytes, context_lines)
                    processed_count += 1
                elif is_php and enable_php:
                    # Regular PHP file
                    results = process_php_file(file_path, collector, min_bytes, context_lines)
                    processed_count += 1
                else:
                    # Skip if file type is disabled
                    continue

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
        output_files = format_output(results, output_path, split_threshold)

        # Print summary to stderr
        print(f"\nProcessed {processed_count} files", file=sys.stderr)
        print(f"Found {collector.get_string_count()} unique strings", file=sys.stderr)
        print(f"Total occurrences: {collector.get_total_occurrences()}", file=sys.stderr)

        if error_count > 0:
            print(f"Errors: {error_count} files failed to process", file=sys.stderr)

        # Display output files and AI translation prompt if output_path is specified
        if output_files:
            print("\n" + "=" * 80, file=sys.stderr)
            print("OUTPUT FILES:", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            for file_path in output_files:
                print(f"  {file_path}", file=sys.stderr)

            print("\n" + "=" * 80, file=sys.stderr)
            print("IMPORTANT NOTE:", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            print('The prompt sample below uses "en" and "ja" as language keys.', file=sys.stderr)
            print("Adjust these keys to match your Laravel project's lang/ directory structure", file=sys.stderr)
            print("before using the prompt with AI.", file=sys.stderr)
            print("Examples:", file=sys.stderr)
            print('  lang/en/, lang/ja/ -> use "en", "ja"', file=sys.stderr)
            print('  lang/en_US/, lang/ja_JP/ -> use "en_US", "ja_JP"', file=sys.stderr)

            print("\n" + "=" * 80, file=sys.stderr)
            print("AI TRANSLATION PROMPT SAMPLE:", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            print(
                """
Please add translation information to the JSON file(s) above. For each entry:

1. Add a "translations" field at the same level as "text"
2. Inside "translations", provide translations with these language keys:
   - "en": English translation
   - "ja": Japanese translation
3. Examine the "text" value and its surrounding code context in "occurrences" → "positions" → "context"
4. If the text is clearly NOT meant for user-facing i18n (such as technical identifiers,
   dimension patterns like "600x600", CSS class names, or code literals), set "translations": false

Output format:

For translatable text:
{
  "text": "Please log in",
  "translations": {
    "en": "Please log in",
    "ja": "ログインしてください"
  },
  "occurrences": [...]
}

For non-translatable text:
{
  "text": "600x600",
  "translations": false,
  "occurrences": [...]
}

Process all entries in the file(s) and return the complete modified JSON.
""",
                file=sys.stderr,
            )
            print("=" * 80, file=sys.stderr)

        return 0

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def process_blade_file(file_path: Path, collector: StringCollector, min_bytes: int, context_lines: int) -> int:
    """
    Process a Blade template file.

    Args:
        file_path: Path to the Blade file
        collector: StringCollector instance
        min_bytes: Minimum byte length for string extraction
        context_lines: Number of context lines to include (0 to disable)

    Returns:
        Number of strings extracted
    """
    processor = BladeProcessor(file_path, min_bytes)
    results = processor.process()

    # Read file content for context extraction if needed
    file_lines = None
    if context_lines > 0:
        with open(file_path, "r", encoding="utf-8") as f:
            file_lines = f.readlines()

    for extracted in results:
        context = None
        if context_lines > 0 and file_lines is not None:
            context = extract_context_lines(file_lines, extracted.line, context_lines)
        collector.add_string(extracted.text, file_path, extracted.line, extracted.column, extracted.length, context)

    return len(results)


def process_php_file(file_path: Path, collector: StringCollector, min_bytes: int, context_lines: int) -> int:
    """
    Process a PHP file.

    Args:
        file_path: Path to the PHP file
        collector: StringCollector instance
        min_bytes: Minimum byte length for string extraction
        context_lines: Number of context lines to include (0 to disable)

    Returns:
        Number of strings extracted
    """
    processor = PHPProcessor(file_path, min_bytes)
    results = processor.process()

    # Read file content for context extraction if needed
    file_lines = None
    if context_lines > 0:
        with open(file_path, "r", encoding="utf-8") as f:
            file_lines = f.readlines()

    for extracted in results:
        context = None
        if context_lines > 0 and file_lines is not None:
            context = extract_context_lines(file_lines, extracted.line, context_lines)
        collector.add_string(extracted.text, file_path, extracted.line, extracted.column, extracted.length, context)

    return len(results)


def extract_context_lines(file_lines: List[str], target_line: int, context_lines: int) -> List[str]:
    """
    Extract context lines around a target line.

    Args:
        file_lines: List of all lines in the file
        target_line: Target line number (1-based)
        context_lines: Total number of lines to extract (e.g., 5 means 2 before + target + 2 after)

    Returns:
        List of context lines (without trailing newlines)
    """
    # Calculate before and after counts
    # For context_lines=5: 2 before, 1 target, 2 after
    # For context_lines=3: 1 before, 1 target, 1 after
    # For odd numbers: equal before and after
    # For even numbers: one more after
    before_count = (context_lines - 1) // 2
    after_count = context_lines - 1 - before_count

    # Calculate actual line indices (0-based)
    target_idx = target_line - 1  # Convert to 0-based
    start_idx = max(0, target_idx - before_count)
    end_idx = min(len(file_lines), target_idx + after_count + 1)

    # Extract lines and remove trailing newlines
    context = [line.rstrip("\n\r") for line in file_lines[start_idx:end_idx]]

    return context
