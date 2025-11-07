# Laravel i18n Refactor Tool - AI Agent Instructions

## Project Overview

CLI tool extracting hardcoded strings from Laravel projects (Blade templates and PHP files) for internationalization. Written in Python 3.10+, published to PyPI, and used via `uvx laravel-i18n-refactor extract <directory>`.

**Key Architecture:**
- Entry: `src/refactor/main.py` (CLI parser + action dispatcher)
- Core Logic: `src/refactor/actions/extract.py` (orchestrates file discovery and processing)
- Processors: `blade_processor.py` (HTML/BeautifulSoup), `php_processor.py` (manual string parsing)
- Utilities: `output_formatter.py` (JSON output + auto-splitting), `file_finder.py` (glob + Laravel-aware exclusions)

## Critical Development Rules

### ⚠️ Python Environment Management

**IMPORTANT:** This project uses a pre-configured virtual environment in the project root:

- ✅ **ALWAYS** use `venv/bin/python` from the project root
- ✅ Use `venv/bin/black` and `venv/bin/pylint` for code quality checks
- ❌ **DO NOT** create temporary virtual environments
- ❌ **DO NOT** install packages automatically as an agent
- ❌ **DO NOT** use `uv run`, `uv pip`, or any `uv` commands for development
- ❌ **DO NOT** run build commands (`python -m build`)
- ❌ **DO NOT** run PyPI upload commands (`twine upload`)
- ❌ **DO NOT** perform any external operations that affect repositories or services

**Reason:** Developer manages environment; building and publishing to PyPI are critical operations that MUST be performed by the developer; `uv` is only for end-users installing from PyPI (`uvx laravel-i18n-refactor`); development must use the pre-configured environment for consistency.

### 🚫 Embedded Exclusion Dictionary Protection

**CRITICAL:** The embedded exclusion dictionary (`dict/embed-exclude-dict.txt`) contains curated language codes and must NOT be modified without explicit developer approval:

- ❌ **DO NOT** add entries to `dict/embed-exclude-dict.txt`
- ❌ **DO NOT** remove entries from `dict/embed-exclude-dict.txt`
- ❌ **DO NOT** modify entries in `dict/embed-exclude-dict.txt`
- ✅ **ONLY** suggest changes to the developer for review

**Reason:** The embedded dictionary is shared across all users and must remain stable. Incorrect modifications can affect all projects using this tool.

### 📝 Exclusion Dictionary Syntax

The tool supports glob patterns and regular expressions:

```text
# Comments (lines starting with #)
# Exact match (case-sensitive)
word

# Wildcards
data-*        # Matches data-id, data-name, etc.
*-icon        # Matches search-icon, menu-icon, etc.
prefix*       # Matches prefixAny

# Character classes
[0-9]*        # Matches strings starting with digits
[a-z]*        # Matches strings starting with lowercase letters

# Regular expressions (with regex: prefix)
regex:^\d+x\d+$        # Dimension patterns (600x600, 1920x1080)
regex:^\d{3,4}$        # 3-4 digit numbers
regex:^#[0-9a-fA-F]+$  # Hex color codes

# Negation (re-include despite previous exclusion)
data-*         # Exclude all data-* patterns
!data-label    # But include data-label
```

**Implementation:** `ExclusionMatcher` class in `src/refactor/utils/exclusion_dict.py`

- `append_from_file(path)`: Append patterns from file (method chaining)
- `should_exclude(text)`: Check if text matches any exclusion pattern
- Patterns evaluated in order; later patterns override earlier ones
- Glob patterns: `*` for wildcard, `[0-9]` for character classes
- Regular expressions: `regex:PATTERN` for Python regex patterns

## Critical Domain Knowledge

### Two-Track Processing Model

Files are routed by extension:
- `.blade.php` → `BladeProcessor` (parses HTML with BeautifulSoup, extracts text nodes/attributes/scripts)
- `.php` → `PHPProcessor` (tokenizes strings manually, context-aware filtering)

**Why manual parsing in PHPProcessor?** Standard Python AST doesn't handle Blade syntax in PHP files. Manual scanning preserves position data (line/column/length) needed for output.

### Smart Exclusion System

### Smart Exclusion System

**Blade Excludes:**
- Translation: `{{ __() }}`, `{{ trans() }}`, `@lang()`, `{!! __() !!}`, `{!! trans() !!}`
- Variables: `{{ $variable }}`, `{!! $variable !!}`
- Directives: `@if()`, `@foreach()`, `@endif`, `@endforeach`, `@php...@endphp`
- Comments: `<!-- HTML comments -->`, `{{-- Blade comments --}}`

**PHP Excludes:**
- Translation: `__()`, `trans()`, `Lang::get()`
- Logs: `Log::info()`, `logger()`, `error_log()`
- Console: `echo`, `print`, `var_dump()`, `dd()`, `dump()`
- Commands: `$this->info()`, `$this->error()`, `$this->warn()`
- Array keys: `'key' => 'value'` (values are extracted, keys are excluded)

**Context-Based Filtering:** PHPProcessor checks 200-char context before string literals using regex patterns (see `_should_include_string()`)

### Laravel Project Auto-Detection

`file_finder.py` searches for `composer.json` to identify Laravel roots, then auto-excludes `vendor/`, `node_modules/`, `storage/`, `bootstrap/cache/`, `public/` (see `LARAVEL_AUTO_EXCLUDE_DIRS`). User-specified `-e` exclusions layer on top.

## Development Workflows

### Local Development & Testing

```bash
# Run locally using project venv
venv/bin/python src/refactor/main.py extract <directory> -o output.json

# Code quality
venv/bin/black src/  # line-length=160 (see pyproject.toml)
venv/bin/pylint src/

# Quick test
mkdir -p /tmp/test-laravel/resources/views
echo '<p>Test 日本語</p>' > /tmp/test-laravel/resources/views/test.blade.php
venv/bin/python src/refactor/main.py extract /tmp/test-laravel -o test-output.json
```

**Note:** All dependencies are already installed in `venv/`. DO NOT run `pip install` as an agent.

## Command Line Options Reference

```bash
# Required
<directory>              # Target directory

# File Selection
-n, --name PATTERN       # File pattern (default: "**/*.php")
-e, --exclude DIR        # Exclude directories (multiple, default: node_modules)
--include-hidden         # Include hidden directories (default: False)

# Output Control
-o, --output FILE        # Output path (default: stdout)
--split-threshold NUM    # Split every N items (default: 100, 0=disable)
--context-lines NUM      # Context lines (default: 5, 0=disable)

# Processing Control
--enable-blade           # Process .blade.php (default: True)
--disable-blade          # Skip .blade.php
--enable-php             # Process .php (default: False)
--disable-php            # Skip .php

# Filtering
--min-bytes NUM          # Minimum byte length (default: 2)
```

### Output Format (Consolidated JSON)

**⚠️ CRITICAL: Automatic File Splitting**

Output files are **automatically split** when extracting many strings:
- **Default**: 100 items per file
- **Naming**: `output.json` → `output-01.json`, `output-02.json`, `output-03.json`, ...
- **Control**: `--split-threshold NUM` option (0 = disable splitting)
- **Implementation**: `src/refactor/utils/output_formatter.py` (`_write_to_files()`)

**When testing/validating:**
- Always check for numbered files (`output-1.json`, `output-2.json`, etc.)
- List directory contents to find the latest file
- Use the highest-numbered file for validation

```json
[
  {
    "text": "extracted string",
    "occurrences": [
      {
        "file": "/absolute/path/file.php",
        "positions": [
          {
            "line": 10,
            "column": 5,
            "length": 15,
            "context": [
              "    previous line",
              "    target line with extracted string",
              "    next line"
            ]
          }
        ]
      }
    ]
  }
]
```

**Fields:**
- `line`: 1-based line number
- `column`: 0-based column position
- `length`: character count (not bytes)
- `context`: Target line + 2 lines before/after (5 total, less at boundaries)

### Character Filtering Rules

Both processors strip whitespace from extracted strings and skip:
- Empty/whitespace-only strings
- ASCII-only strings containing only digits/symbols (e.g., "123", "===")
- Exception: Non-ASCII chars (Japanese, emoji) bypass symbol check

**Implementation:** `_contains_non_ascii()` checks `ord(char) > 127`

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

## Debugging Tips

### When Strings Are Missing

1. Check if file is auto-excluded (Laravel directories or `-e` flag)
2. Verify processor routing: `.blade.php` suffix exact match required
3. Add debug prints in `_should_exclude_text()` / `_should_include_string()`
4. Test regex patterns in isolation: `re.search(pattern, context)`

### When Position Calculation Issues

Both processors calculate positions from original file content, then adjust after stripping:
```python
leading_whitespace = len(text) - len(text.lstrip())
adjusted_column = column + leading_whitespace
```

**Current accuracy:** 97% (3% are file boundary cases with fewer context lines)

## Project-Specific Patterns

- **No test suite:** Manual validation using real Laravel projects
- **Bilingual docs:** `README.md` (English) + `README-ja.md` (Japanese) + `Documents/システム仕様書.md` (detailed Japanese spec)
- **Absolute paths in output:** `string_collector.py` uses `file_path.resolve()` for unambiguous file references
- **Graceful error handling:** Individual file failures print warnings but don't halt processing
- **Default values:** Default values for command-line parameters must ONLY be defined in `main.py` argparse configuration. All other functions must accept these parameters as required arguments (not Optional with defaults). This prevents inconsistency and maintenance issues from scattered default values across the codebase.

## Do Not

- Add generic error handling without specific Laravel context awareness
- Use Python AST for parsing (incompatible with Blade syntax)
- Modify exclusion patterns without consulting `Documents/システム仕様書.md` (authoritative spec)
- Change line/column indexing conventions (breaks tooling compatibility)
- Define default values outside of `main.py`: Default values for command-line parameters must ONLY be defined in `main.py` argparse configuration
