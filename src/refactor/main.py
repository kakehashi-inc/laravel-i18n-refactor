#!/usr/bin/env python3
"""
Laravel i18n Refactor Tool

A tool to help with Laravel internationalization by extracting hardcoded strings.
"""

import argparse
import sys

from refactor.actions.extract import setup_extract_parser
from refactor.actions.translate import setup_translate_parser


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(prog="laravel-i18n-refactor", description="Laravel internationalization support tool")

    # Create subparsers for different actions
    subparsers = parser.add_subparsers(dest="action", help="Action to perform", required=True)

    setup_extract_parser(subparsers)
    setup_translate_parser(subparsers)

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Each action has its own func set by set_defaults()
        if hasattr(args, "func"):
            return args.func(args)
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
