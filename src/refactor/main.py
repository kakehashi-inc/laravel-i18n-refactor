#!/usr/bin/env python3
"""
Laravel i18n Refactor Tool

A tool to help with Laravel internationalization by extracting hardcoded strings.
"""

import argparse
import sys
from pathlib import Path


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(prog="laravel-i18n-refactor", description="Laravel internationalization support tool")

    # Create subparsers for different actions
    subparsers = parser.add_subparsers(dest="action", help="Action to perform", required=True)

    # Extract action
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

    # Future actions can be added here
    # e.g., replace_parser = subparsers.add_parser('replace', ...)

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        if args.action == "extract":
            from refactor.actions.extract import extract_strings

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
        else:
            parser.error(f"Unknown action: {args.action}")
            return 1

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
