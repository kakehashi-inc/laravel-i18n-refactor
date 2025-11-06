# Laravel i18n Refactor Tool - AI Agent Instructions

## Project Overview

A CLI tool that extracts hardcoded strings from Laravel projects (Blade templates and PHP files) for internationalization. Written in Python 3.10+, published to PyPI, and used via `uvx laravel-i18n-refactor extract <directory>`.

**Key Architecture:**
- Entry: `src/refactor/main.py` (CLI parser + action dispatcher)
- Core Logic: `src/refactor/actions/extract.py` (orchestrates file discovery and processing)
- Processors: `blade_processor.py` (HTML/BeautifulSoup), `php_processor.py` (manual string parsing)
- Utilities: `string_collector.py` (consolidates duplicates), `file_finder.py` (glob + Laravel-aware exclusions)

## Critical Domain Knowledge

### Two-Track Processing Model

Files are routed by extension:
- `.blade.php` → `BladeProcessor` (parses HTML with BeautifulSoup, extracts text nodes/attributes/scripts)
- `.php` → `PHPProcessor` (tokenizes strings manually, context-aware filtering)

**Why manual parsing in PHPProcessor?** Standard Python AST doesn't handle Blade syntax in PHP files. Manual scanning preserves position data (line/column/length) needed for output.

### Smart Exclusion System (See `Documents/システム仕様書.md`)

**Blade:** Excludes `{{ __() }}`, `@lang()`, PHP variables (`{{ $var }}`), Blade directives, comments
**PHP:** Excludes translation functions, logs (`Log::info()`), console output (`echo`, `dd()`), array keys, command output (`$this->info()`)

**Context-Based Filtering:** PHPProcessor checks 200-char context before string literals using regex patterns to detect exclusion functions.

### Laravel Project Auto-Detection

`file_finder.py` searches for `composer.json` to identify Laravel roots, then auto-excludes `vendor/`, `node_modules/`, `storage/`, `bootstrap/cache/`, `public/` (see `LARAVEL_AUTO_EXCLUDE_DIRS`). User-specified `-e` exclusions layer on top.

## Development Workflows

### Local Development & Testing

```bash
# Install with dev dependencies (uv recommended)
uv pip install -e ".[dev]"

# Run locally (without install)
python src/refactor/main.py extract <directory> -o output.json

# Code quality
black src/  # line-length=160 (see pyproject.toml)
pylint src/
```

### Testing New String Extraction Logic

Create test files in a temp directory:
```bash
mkdir -p /tmp/test-laravel/resources/views
echo '<p>Test 日本語</p>' > /tmp/test-laravel/resources/views/test.blade.php
python src/refactor/main.py extract /tmp/test-laravel -o test-output.json
```

### PyPI Release Process (See `Documents/pypiリリース方法.md`)

1. **TestPyPI first:**
   ```bash
   rm -rf dist/ src/*.egg-info
   uv run python -m build
   twine upload --repository testpypi dist/*
   uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ laravel_i18n_refactor --help
   ```

2. **Production PyPI after validation:**
   ```bash
   twine upload dist/*
   ```

## Code Conventions

### File Organization
- Actions in `src/refactor/actions/` (orchestration logic)
- Processors in `src/refactor/mods/` (file-type-specific extraction)
- Utilities in `src/refactor/utils/` (reusable helpers)

### String Position Data
All processors return: `List[Tuple[str, int, int, int]]` = `(text, line, column, length)`
- Line: 1-based (human-readable)
- Column: 0-based (programming convention)
- Length: character count (not bytes)

### Output Format (Consolidated JSON)
```json
[
  {
    "text": "extracted string",
    "occurrences": [
      {"file": "/absolute/path/file.php", "positions": [{"line": 10, "column": 5, "length": 15}]}
    ]
  }
]
```

### Character Filtering Rules
Both processors strip whitespace from extracted strings and skip:
- Empty/whitespace-only strings
- ASCII-only strings containing only digits/symbols (e.g., "123", "===")
- Exception: Non-ASCII chars (Japanese, emoji) bypass symbol check

**Implementation:** `_contains_non_ascii()` checks `ord(char) > 127`

## Debugging Tips

### When Strings Are Missing
1. Check if file is auto-excluded (Laravel directories or `-e` flag)
2. Verify processor routing: `.blade.php` suffix exact match required
3. Add debug prints in `_should_exclude_text()` / `_should_include_string()`
4. Test regex patterns in isolation: `re.search(pattern, context)`

### When Blade Syntax Leaks Through
`blade_processor.py` masks directives in `_mask_blade_syntax()` before HTML parsing. Check:
- Parenthesis matching for multi-line directives (depth counter)
- PHP block removal (`<?php ?>`, `@php @endphp`)

### Position Calculation Issues
Both processors calculate positions from original file content, then adjust after stripping:
```python
leading_whitespace = len(text) - len(text.lstrip())
adjusted_column = column + leading_whitespace
```

## Integration Points

- **BeautifulSoup:** Blade parsing (`lxml` parser for speed)
- **Setuptools:** Build system (see `[build-system]` in `pyproject.toml`)
- **Entry Point:** `[project.scripts]` defines `laravel-i18n-refactor` command

## Project-Specific Patterns

- **No test suite:** Manual validation using real Laravel projects
- **Bilingual docs:** `README.md` (English) + `README-ja.md` (Japanese) + `Documents/システム仕様書.md` (detailed Japanese spec)
- **Absolute paths in output:** `string_collector.py` uses `file_path.resolve()` for unambiguous file references
- **Graceful error handling:** Individual file failures print warnings but don't halt processing

## Do Not

- Add generic error handling without specific Laravel context awareness
- Use Python AST for parsing (incompatible with Blade syntax)
- Modify exclusion patterns without consulting `Documents/システム仕様書.md` (authoritative spec)
- Change line/column indexing conventions (breaks tooling compatibility)
- **Define default values outside of `main.py`:** Default values for command-line parameters must ONLY be defined in `main.py` argparse configuration. All other functions must accept these parameters as required arguments (not Optional with defaults). This prevents inconsistency and maintenance issues from scattered default values across the codebase.
