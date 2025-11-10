"""
Translation action for translating extracted strings using AI providers.
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def get_terminal_width() -> int:
    """
    Get terminal width.

    Returns:
        Terminal width (default: 80 if cannot determine)
    """
    try:
        return os.get_terminal_size().columns
    except (AttributeError, OSError):
        return 80


def truncate_text(text: str, max_width: int) -> str:
    """
    Truncate text to fit within max_width, showing beginning and end with '...' in middle.

    Args:
        text: Text to truncate
        max_width: Maximum width

    Returns:
        Truncated text
    """
    if len(text) <= max_width:
        return text

    if max_width < 10:
        return text[:max_width]

    # Show beginning and end with '...' in middle
    ellipsis = "..."
    side_length = (max_width - len(ellipsis)) // 2
    return text[:side_length] + ellipsis + text[-side_length:]


def print_progress(current: int, total: int, text: str, overwrite: bool = True) -> None:
    """
    Print translation progress with text truncation.

    Args:
        current: Current item number (1-based)
        total: Total number of items
        text: Text being translated
        overwrite: If True, overwrite previous line
    """
    terminal_width = get_terminal_width()
    max_text_width = terminal_width - 2  # Leave 2 chars margin

    # Build progress message
    progress_prefix = f"[{current}/{total}] Translating: "
    available_width = max_text_width - len(progress_prefix)

    if available_width > 0:
        truncated_text = truncate_text(text, available_width)
        message = progress_prefix + truncated_text
    else:
        message = f"[{current}/{total}]"

    # Print with or without overwrite
    if overwrite:
        # Clear line and print
        print(f"\r{message:<{max_text_width}}", end="", flush=True, file=sys.stderr)
    else:
        print(message, file=sys.stderr)


def setup_translate_parser(subparsers) -> None:
    """
    Set up the translate command parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    translate_parser = subparsers.add_parser(
        "translate", help="Translate extracted strings using AI providers", description="Translate extracted strings using AI providers"
    )

    # Create parent parser for common translate options
    translate_common = argparse.ArgumentParser(add_help=False)
    translate_common.add_argument("-i", "--input", action="append", metavar="FILE", help="Input JSON file(s) to translate (can be specified multiple times)")
    translate_common.add_argument(
        "--lang", action="append", metavar="CODE:DESCRIPTION", help='Target language in format "code:description" (e.g., "ja:Japanese", "en:American English")'
    )
    translate_common.add_argument("--batch-size", type=int, default=5, help="Number of items to translate in one API call (default: 5)")
    translate_common.add_argument("--list-models", action="store_true", help="List available models for this provider and exit")
    translate_common.add_argument("--dry-run", action="store_true", help="Show what would be translated without making API calls")

    # Provider-specific subparsers
    provider_subparsers = translate_parser.add_subparsers(
        dest="provider", title="providers", description="Available AI providers", help="AI provider to use", required=True
    )

    # OpenAI provider
    openai_parser = provider_subparsers.add_parser("openai", parents=[translate_common], help="Use OpenAI GPT models")
    openai_parser.add_argument("--model", required=True, help="Model name (required)")
    openai_parser.add_argument("--api-key", help="API key (or OPENAI_API_KEY env var)")
    openai_parser.add_argument("--organization", help="Organization ID (or OPENAI_ORGANIZATION env var)")
    openai_parser.add_argument("--temperature", type=float, help="Sampling temperature (or OPENAI_TEMPERATURE env var)")
    openai_parser.add_argument("--max-tokens", type=int, help="Maximum tokens (or OPENAI_MAX_TOKENS env var)")
    openai_parser.set_defaults(func=translate_files)

    # Claude provider
    claude_parser = provider_subparsers.add_parser("claude", parents=[translate_common], help="Use Anthropic Claude")
    claude_parser.add_argument("--model", required=True, help="Model name (required)")
    claude_parser.add_argument("--api-key", help="API key (or ANTHROPIC_API_KEY env var)")
    claude_parser.add_argument("--temperature", type=float, help="Sampling temperature (or ANTHROPIC_TEMPERATURE env var)")
    claude_parser.add_argument("--max-tokens", type=int, help="Maximum tokens (or ANTHROPIC_MAX_TOKENS env var, default: 4096)")
    claude_parser.set_defaults(func=translate_files)

    # Gemini provider
    gemini_parser = provider_subparsers.add_parser("gemini", parents=[translate_common], help="Use Google Gemini")
    gemini_parser.add_argument("--model", required=True, help="Model name (required)")
    gemini_parser.add_argument("--api-key", help="API key (or GEMINI_API_KEY/GOOGLE_API_KEY env var)")
    gemini_parser.add_argument("--temperature", type=float, help="Sampling temperature (or GEMINI_TEMPERATURE env var)")
    gemini_parser.add_argument("--max-tokens", type=int, help="Maximum output tokens (or GEMINI_MAX_TOKENS env var)")
    gemini_parser.add_argument("--top-p", type=float, help="Nucleus sampling (or GEMINI_TOP_P env var)")
    gemini_parser.add_argument("--top-k", type=int, help="Top-k sampling (or GEMINI_TOP_K env var)")
    gemini_parser.set_defaults(func=translate_files)

    # OpenAI-compatible provider
    openai_compat_parser = provider_subparsers.add_parser("openai-compat", parents=[translate_common], help="Use OpenAI-compatible endpoints")
    openai_compat_parser.add_argument("--model", required=True, help="Model name (required)")
    openai_compat_parser.add_argument("--api-base", required=True, help="API base URL (required, or OPENAI_COMPAT_API_BASE env var)")
    openai_compat_parser.add_argument("--api-key", help="API key (or OPENAI_COMPAT_API_KEY env var)")
    openai_compat_parser.add_argument("--temperature", type=float, help="Sampling temperature (or OPENAI_COMPAT_TEMPERATURE env var)")
    openai_compat_parser.add_argument("--max-tokens", type=int, help="Maximum tokens (or OPENAI_COMPAT_MAX_TOKENS env var)")
    openai_compat_parser.set_defaults(func=translate_files)

    # Ollama provider
    ollama_parser = provider_subparsers.add_parser("ollama", parents=[translate_common], help="Use Ollama for local models")
    ollama_parser.add_argument("--model", required=True, help="Model name (required)")
    ollama_parser.add_argument("--api-base", help="Ollama server URL (or OLLAMA_HOST env var, default: http://localhost:11434)")
    ollama_parser.add_argument("--temperature", type=float, help="Sampling temperature (or OLLAMA_TEMPERATURE env var)")
    ollama_parser.add_argument("--max-tokens", type=int, help="Maximum tokens (or OLLAMA_MAX_TOKENS env var)")
    ollama_parser.add_argument("--num-ctx", type=int, help="Context window size (or OLLAMA_NUM_CTX env var)")
    ollama_parser.add_argument("--top-p", type=float, help="Nucleus sampling (or OLLAMA_TOP_P env var)")
    ollama_parser.add_argument("--top-k", type=int, help="Top-k sampling (or OLLAMA_TOP_K env var)")
    ollama_parser.add_argument("--repeat-penalty", type=float, help="Repetition penalty (or OLLAMA_REPEAT_PENALTY env var)")
    ollama_parser.set_defaults(func=translate_files)

    # Anthropic-compatible provider
    anthropic_compat_parser = provider_subparsers.add_parser("anthropic-compat", parents=[translate_common], help="Use Anthropic-compatible endpoints")
    anthropic_compat_parser.add_argument("--model", required=True, help="Model name (required)")
    anthropic_compat_parser.add_argument("--api-base", required=True, help="API base URL (required, or ANTHROPIC_COMPAT_API_BASE env var)")
    anthropic_compat_parser.add_argument("--api-key", help="API key (or ANTHROPIC_COMPAT_API_KEY env var)")
    anthropic_compat_parser.add_argument("--temperature", type=float, help="Sampling temperature (or ANTHROPIC_COMPAT_TEMPERATURE env var)")
    anthropic_compat_parser.add_argument("--max-tokens", type=int, help="Maximum tokens (or ANTHROPIC_COMPAT_MAX_TOKENS env var, default: 4096)")
    anthropic_compat_parser.set_defaults(func=translate_files)


def parse_language_spec(lang_spec: str) -> Tuple[str, str]:
    """
    Parse language specification string.

    Args:
        lang_spec: Language spec in format "code:description"

    Returns:
        Tuple of (code, description)

    Raises:
        ValueError: If lang_spec is not in "code:description" format
    """
    if ":" not in lang_spec:
        raise ValueError(f'Language specification must be in format "code:description" (e.g., "ja:Japanese"), got: {lang_spec}')

    parts = lang_spec.split(":", 1)
    code = parts[0].strip()
    description = parts[1].strip()

    if not code or not description:
        raise ValueError(f"Both code and description must be non-empty in language specification: {lang_spec}")

    return (code, description)


def validate_extraction_format(data: List[Dict]) -> Tuple[bool, Optional[str]]:
    """
    Validate if JSON is in expected extraction format.

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(data, list):
        return False, "JSON must be a list"

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            return False, f"Item {idx} is not a dictionary"
        if "text" not in item:
            return False, f"Item {idx} is missing 'text' field"
        if "occurrences" not in item:
            return False, f"Item {idx} is missing 'occurrences' field"

    return True, None


def identify_untranslated(data: List[Dict], languages: List[str]) -> List[Dict]:
    """
    Find items that need translation for specified languages.

    Args:
        data: List of extraction items
        languages: List of language codes to check

    Returns:
        List of items that need translation
    """
    items_to_translate = []

    for item in data:
        # translations フィールドがない場合
        if "translations" not in item:
            items_to_translate.append(item)
            continue

        # translations が false の場合はスキップ
        if item["translations"] is False:
            continue

        # 必要な言語が不足している場合
        if isinstance(item["translations"], dict):
            missing_langs = [lang for lang in languages if lang not in item["translations"]]
            if missing_langs:
                items_to_translate.append(item)

    return items_to_translate


def translate_files(args) -> int:
    """
    Main translation function.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code
    """
    from refactor.providers import get_provider

    # Handle --list-models mode
    if args.list_models:
        try:
            provider = get_provider(args.provider, api_key=getattr(args, "api_key", None), api_base=getattr(args, "api_base", None), list_models=True)
            models = provider.list_models()
            print(f"Available models for {args.provider}:")
            for model in models:
                print(f"  {model}")
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    # Validate input files
    if not args.input:
        print("Error: --input files required (unless using --list-models)", file=sys.stderr)
        return 1

    # Parse language specifications
    if args.lang:
        languages = [parse_language_spec(lang) for lang in args.lang]
    else:
        # Default languages
        languages = [("ja", "Japanese"), ("en", "American English")]

    # Initialize provider
    try:
        # Collect provider-specific kwargs
        provider_kwargs = {
            "model": args.model,
        }

        # Add optional parameters if present
        optional_params = ["api_key", "api_base", "organization", "temperature", "max_tokens", "batch_size", "top_p", "top_k", "num_ctx", "repeat_penalty"]

        for param in optional_params:
            if hasattr(args, param):
                value = getattr(args, param)
                if value is not None:
                    provider_kwargs[param] = value

        provider = get_provider(args.provider, **provider_kwargs)

    except Exception as e:
        print(f"Error initializing provider: {e}", file=sys.stderr)
        return 1

    # Process each input file
    total_translated = 0
    total_non_translatable = 0
    total_failed = 0

    for input_path_str in args.input:
        input_path = Path(input_path_str)

        if not input_path.exists():
            print(f"Error: File not found: {input_path}", file=sys.stderr)
            continue

        try:
            # Load JSON
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate format
            is_valid, error = validate_extraction_format(data)
            if not is_valid:
                print(f"Error in {input_path}: {error}", file=sys.stderr)
                continue

            # Identify items needing translation
            items_to_translate = identify_untranslated(data, [lang[0] for lang in languages])

            if not items_to_translate:
                print(f"No items need translation in {input_path}")
                continue

            print(f"Translating {len(items_to_translate)} items in {input_path}...", file=sys.stderr)

            if args.dry_run:
                print(f"[DRY RUN] Would translate {len(items_to_translate)} items in batches of {args.batch_size}")
                for item in items_to_translate[:5]:
                    print(f"  - {item['text'][:50]}...")
                if len(items_to_translate) > 5:
                    print(f"  ... and {len(items_to_translate) - 5} more")
                continue

            # Process items in batches
            file_translated = 0
            file_non_translatable = 0
            file_failed = 0
            batch_size = args.batch_size

            for batch_start in range(0, len(items_to_translate), batch_size):
                batch_end = min(batch_start + batch_size, len(items_to_translate))
                batch = items_to_translate[batch_start:batch_end]
                batch_num = (batch_start // batch_size) + 1
                total_batches = (len(items_to_translate) + batch_size - 1) // batch_size

                # Display progress for first item in batch
                first_item_text = batch[0]["text"]
                print_progress(batch_end, len(items_to_translate), first_item_text)

                try:
                    # Translate batch
                    results = provider.translate_batch(batch, languages)

                    # Update items in data directly
                    for result in results:
                        result_text = result.get("text")
                        if not result_text:
                            continue

                        # Find the item in original data by text
                        for original_item in data:
                            if original_item.get("text") == result_text:
                                translations = result.get("translations")
                                if translations is False:
                                    original_item["translations"] = False
                                    file_non_translatable += 1
                                elif isinstance(translations, dict):
                                    # Merge translations
                                    if "translations" not in original_item or not isinstance(original_item["translations"], dict):
                                        original_item["translations"] = {}
                                    original_item["translations"].update(translations)
                                    file_translated += 1
                                break

                except Exception as e:
                    print(f"\n  Warning: Batch {batch_num}/{total_batches} translation failed: {e}", file=sys.stderr)
                    file_failed += len(batch)
                    continue

            # Clear progress line
            print("\r" + " " * (get_terminal_width() - 2) + "\r", end="", file=sys.stderr)

            # Generate output filename
            output_path = input_path.parent / f"{input_path.stem}-translated{input_path.suffix}"

            # Save result
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"  Saved translations to {output_path}", file=sys.stderr)
            print(f"  Results: {file_translated} translated, {file_non_translatable} non-translatable, {file_failed} failed", file=sys.stderr)

            total_translated += file_translated
            total_non_translatable += file_non_translatable
            total_failed += file_failed

        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {input_path}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Error processing {input_path}: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            continue

    if not args.dry_run and (total_translated > 0 or total_non_translatable > 0 or total_failed > 0):
        print("\n=== Translation Summary ===", file=sys.stderr)
        print(f"Translated: {total_translated}", file=sys.stderr)
        print(f"Non-translatable: {total_non_translatable}", file=sys.stderr)
        print(f"Failed: {total_failed}", file=sys.stderr)
        print(f"Total processed: {total_translated + total_non_translatable + total_failed}", file=sys.stderr)

    return 0
