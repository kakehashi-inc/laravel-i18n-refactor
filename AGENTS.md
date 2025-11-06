# Laravel i18n Refactor Tool - AI Agent Guide

## Quick Reference

**What:** CLI tool extracting hardcoded strings from Laravel projects for i18n
**Language:** Python 3.10+ | **Package:** PyPI via `uvx laravel-i18n-refactor`
**Entry:** `src/refactor/main.py` → `actions/extract.py` → Processors → JSON output

## Architecture at a Glance

```text
User Input (directory + pattern)
    ↓
main.py (argparse CLI)
    ↓
extract.py (orchestrator)
    ↓
file_finder.py (glob + Laravel auto-exclusions)
    ↓
├─ .blade.php → BladeProcessor (BeautifulSoup HTML parsing)
└─ .php       → PHPProcessor (manual string tokenization)
    ↓
string_collector.py (deduplication + consolidation)
    ↓
JSON output (text + occurrences with positions)
```

## Core Processing Logic

### File Routing

- **`.blade.php`** → `BladeProcessor`: HTML parsing via BeautifulSoup (lxml), extracts text nodes/attributes/`<script>` strings
- **`.php`** → `PHPProcessor`: Manual tokenization (no AST - Blade syntax incompatible), preserves line/column/length

**Why manual parsing?** Python AST cannot handle Blade syntax mixed in PHP files. Manual scanning maintains precise position data required for output format.

### Exclusion System (Critical)

**Blade excludes:**

- Translation: `{{ __() }}`, `@lang()`, `{!! trans() !!}`
- Variables: `{{ $var }}`, `{!! $var !!}`
- Directives: `@if()`, `@foreach()`, `@php...@endphp`
- Comments: `<!-- -->`, `{{-- --}}`

**PHP excludes:**

- Translation: `__()`, `trans()`, `Lang::get()`
- Logs: `Log::info()`, `logger()`, `error_log()`
- Console: `echo`, `print`, `var_dump()`, `dd()`, `dump()`
- Commands: `$this->info()`, `$this->error()`
- Array keys: `'key' =>` (values extracted)

**Context filtering:** PHPProcessor checks 200 chars before string literals using regex patterns (see `_should_include_string()`).

### Laravel Auto-Detection

- Searches for `composer.json` to identify Laravel project roots
- Auto-excludes: `vendor/`, `node_modules/`, `storage/`, `bootstrap/cache/`, `public/`
- See `LARAVEL_AUTO_EXCLUDE_DIRS` in `file_finder.py`

## Development Commands

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Local testing (no install)
python src/refactor/main.py extract <dir> -o output.json

# Code quality (line-length=160)
black src/
pylint src/

# Quick test with temp files
mkdir -p /tmp/test-laravel/resources/views
echo '<p>Test 日本語</p>' > /tmp/test-laravel/resources/views/test.blade.php
python src/refactor/main.py extract /tmp/test-laravel -o test-output.json
cat test-output.json | python -m json.tool
```

## PyPI Release Workflow

```bash
# 1. TestPyPI (always first)
rm -rf dist/ src/*.egg-info
uv run python -m build
twine upload --repository testpypi dist/*
uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ laravel_i18n_refactor --help

# 2. Production PyPI (after validation)
twine upload dist/*
```

See `Documents/pypiリリース方法.md` for detailed steps.

## Code Conventions

### Position Data Format

All processors return: `List[Tuple[str, int, int, int]]`

- `(text, line, column, length)`
- **Line:** 1-based (human-readable)
- **Column:** 0-based (programming standard)
- **Length:** character count (not bytes)

### Output Structure

```json
[
  {
    "text": "extracted string",
    "occurrences": [
      {
        "file": "/absolute/path/file.php",
        "positions": [{"line": 10, "column": 5, "length": 15}]
      }
    ]
  }
]
```

### Character Filtering

Both processors strip whitespace and skip:

- Empty/whitespace-only strings
- ASCII-only digits/symbols (e.g., "123", "===")
- **Exception:** Non-ASCII chars (Japanese, emoji) bypass symbol check

**Check:** `_contains_non_ascii()` → `ord(char) > 127`

## Debugging Checklist

### Missing Strings?

1. File auto-excluded? Check `LARAVEL_AUTO_EXCLUDE_DIRS` or `-e` flags
2. Processor routing: `.blade.php` exact match required (not just `.php`)
3. Add prints: `_should_exclude_text()` (Blade), `_should_include_string()` (PHP)
4. Test regex isolation: `re.search(pattern, context)`

### Blade Syntax Leaking?

- Check `_mask_blade_syntax()`: parenthesis depth counter for multi-line directives
- Verify PHP block removal: `<?php ?>`, `@php @endphp`

### Position Calculation Off?

```python
# Processors calculate from original content, adjust after strip
leading_whitespace = len(text) - len(text.lstrip())
adjusted_column = column + leading_whitespace
```

## File Organization

```text
src/refactor/
├── main.py              # CLI entry (argparse)
├── actions/
│   └── extract.py       # Orchestration logic
├── mods/
│   ├── blade_processor.py    # Blade template extraction
│   ├── php_processor.py      # PHP file extraction
│   └── string_collector.py   # Deduplication/consolidation
└── utils/
    ├── file_finder.py        # Glob + Laravel exclusions
    └── output_formatter.py   # JSON output
```

## Critical Constraints

**DO:**

- Preserve line/column indexing conventions (1-based/0-based)
- Use absolute paths in output (`file_path.resolve()`)
- Check `Documents/システム仕様書.md` before modifying exclusion patterns
- Handle individual file failures gracefully (warn, don't halt)

**DON'T:**

- Use Python AST for parsing (Blade incompatible)
- Add generic error handling without Laravel context awareness
- Change indexing conventions (breaks tooling compatibility)
- Modify exclusion patterns without consulting spec

## Project Specifics

- **No test suite:** Manual validation with real Laravel projects
- **Bilingual docs:** README.md (EN) + README-ja.md (JA) + Documents/システム仕様書.md (spec)
- **Build system:** Setuptools (`[build-system]` in pyproject.toml)
- **Entry point:** `[project.scripts]` → `laravel-i18n-refactor` command
- **Dependencies:** BeautifulSoup4 (lxml parser), no heavy frameworks

## Agent Workflow Optimization

When modifying this codebase:

1. **Context gathering:** Start with `Documents/システム仕様書.md` for exclusion logic
2. **File routing:** Check extension first (`.blade.php` vs `.php`)
3. **Position tracking:** Always use original content for calculations, adjust after processing
4. **Testing:** Create minimal test files in `/tmp`, validate JSON output
5. **Validation:** Test both processors independently before integration

For bugs/features:

- Blade issues → `blade_processor.py` + `_mask_blade_syntax()`
- PHP issues → `php_processor.py` + `_should_include_string()`
- Missing files → `file_finder.py` + `LARAVEL_AUTO_EXCLUDE_DIRS`
- Wrong positions → Position calculation logic in processors
- Output format → `string_collector.py` + `output_formatter.py`
