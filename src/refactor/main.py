#!/usr/bin/env python3
"""
Laravel i18n Refactor Tool

A tool to help with Laravel internationalization by extracting hardcoded strings.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        prog='laravel-i18n-refactor',
        description='Laravel internationalization support tool'
    )

    # Create subparsers for different actions
    subparsers = parser.add_subparsers(
        dest='action',
        help='Action to perform',
        required=True
    )

    # Extract action
    extract_parser = subparsers.add_parser(
        'extract',
        help='Extract hardcoded strings from Laravel project files'
    )
    extract_parser.add_argument(
        'directory',
        type=Path,
        help='Target directory to search for files'
    )
    extract_parser.add_argument(
        '-n', '--name',
        default='**/*.php',
        help='File name pattern (e.g., "**/*.blade.php", "*.php")'
    )
    extract_parser.add_argument(
        '-o', '--output',
        type=Path,
        default=None,
        help='Output JSON file path (default: stdout)'
    )

    # Future actions can be added here
    # e.g., replace_parser = subparsers.add_parser('replace', ...)

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        if args.action == 'extract':
            from refactor.actions.extract import extract_strings
            return extract_strings(
                directory=args.directory,
                pattern=args.name,
                output_path=args.output
            )
        else:
            parser.error(f'Unknown action: {args.action}')
            return 1

    except KeyboardInterrupt:
        print('\nOperation cancelled by user', file=sys.stderr)
        return 130
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
