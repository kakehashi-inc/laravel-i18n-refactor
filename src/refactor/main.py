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
        default=200,
        dest="split_threshold",
        help="Threshold for splitting output into multiple files (default: 200, only applies when output file is specified)",
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
