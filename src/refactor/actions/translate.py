"""
Translation action for translating extracted strings using AI providers.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple


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
    openai_parser.add_argument("--batch-size", type=int, help="Batch size (or OPENAI_BATCH_SIZE env var, default: 10)")
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


def parse_language_spec(lang_spec: str) -> Tuple[str, str]:
    """
    Parse language specification string.

    Args:
        lang_spec: Language spec in format "code:description" or just "code"

    Returns:
        Tuple of (code, description)
    """
    if ":" in lang_spec:
        parts = lang_spec.split(":", 1)
        return (parts[0].strip(), parts[1].strip())

    # Default descriptions for common language codes
    default_descriptions = {
        "ja": "Japanese",
        "en": "American English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "zh": "Chinese",
        "ko": "Korean",
        "pt": "Portuguese",
        "ru": "Russian",
        "it": "Italian",
        "nl": "Dutch",
        "pl": "Polish",
        "tr": "Turkish",
        "vi": "Vietnamese",
        "th": "Thai",
        "ar": "Arabic",
        "hi": "Hindi",
    }
    return (lang_spec, default_descriptions.get(lang_spec, lang_spec.upper()))


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


def merge_translations(original: List[Dict], translated: List[Dict]) -> List[Dict]:
    """
    Merge translated content back into original data.

    Args:
        original: Original extraction data
        translated: Translated items from AI

    Returns:
        Merged data with translations
    """
    # Create map of translations by text
    translation_map = {item["text"]: item.get("translations", False) for item in translated}

    # Merge into original data
    for item in original:
        if item["text"] in translation_map:
            new_translations = translation_map[item["text"]]

            # Handle different cases
            if new_translations is False:
                # Mark as non-translatable
                item["translations"] = False
            elif isinstance(new_translations, dict):
                # Merge translations
                if "translations" not in item or not isinstance(item["translations"], dict):
                    item["translations"] = {}
                item["translations"].update(new_translations)

    return original


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

            print(f"Translating {len(items_to_translate)} items in {input_path}...")

            if args.dry_run:
                print(f"[DRY RUN] Would translate {len(items_to_translate)} items")
                for item in items_to_translate[:5]:
                    print(f"  - {item['text'][:50]}...")
                if len(items_to_translate) > 5:
                    print(f"  ... and {len(items_to_translate) - 5} more")
                continue

            # Translate in batches
            translated_items = []
            batch_size = getattr(args, "batch_size", 10)

            for i in range(0, len(items_to_translate), batch_size):
                batch = items_to_translate[i : i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(items_to_translate) + batch_size - 1) // batch_size

                print(f"  Processing batch {batch_num}/{total_batches}...", file=sys.stderr)

                try:
                    result = provider.translate_batch(batch, languages)
                    translated_items.extend(result)
                except Exception as e:
                    print(f"  Warning: Batch translation failed: {e}", file=sys.stderr)
                    # Continue processing other batches

            # Merge translations
            merged_data = merge_translations(data, translated_items)

            # Generate output filename
            output_path = input_path.parent / f"{input_path.stem}-translated{input_path.suffix}"

            # Save result
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=2)

            print(f"Saved translations to {output_path}")
            total_translated += len(translated_items)

        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {input_path}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Error processing {input_path}: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            continue

    if not args.dry_run and total_translated > 0:
        print(f"\nTotal items translated: {total_translated}", file=sys.stderr)

    return 0
