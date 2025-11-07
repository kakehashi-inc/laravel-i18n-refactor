# Laravel i18n Refactor Tool - AI Agent Guide

## Quick Reference

**What:** CLI tool extracting hardcoded strings from Laravel projects for i18n
**Language:** Python 3.10+ | **Package:** PyPI via `uvx laravel-i18n-refactor`
**Entry:** `src/refactor/main.py` → `actions/extract.py` → Processors → JSON output

## ⚠️ Critical Development Rules

### Python Environment Management

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

**CRITICAL:** The embedded exclusion dictionary (`dict/embed-exclude-dict.txt`) must NOT be modified:

- ❌ **DO NOT** add, remove, or modify entries in `dict/embed-exclude-dict.txt`
- ✅ **ONLY** suggest changes to the developer for review

### 📝 Exclusion Dictionary Syntax

Glob patterns and regular expressions supported:

```text
# Exact match
word

# Wildcards
data-*
*-suffix

# Character classes
[0-9]*
[a-z]*

# Regular expressions (with regex: prefix)
regex:^\d+x\d+$        # Dimension patterns (600x600, 1920x1080)
regex:^\d{3,4}$        # 3-4 digit numbers
regex:^#[0-9a-fA-F]+$  # Hex color codes

# Negation
pattern*
!pattern-keep
```

**Implementation:** `ExclusionMatcher.append_from_file(path)` appends patterns (method chaining)

- Glob patterns: `*` for wildcard, `[0-9]` for character classes
- Regular expressions: `regex:PATTERN` for Python regex patterns
- Patterns evaluated in order; later patterns override earlier ones

## Architecture Overview

### Processing Flow
```
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
output_formatter.py (JSON output + auto-splitting)
```

### Two-Track Processing Model

Files are routed by extension:
- **`.blade.php`** → `BladeProcessor`: Parses HTML with BeautifulSoup (lxml), extracts text nodes/attributes/`<script>` strings
- **`.php`** → `PHPProcessor`: Manual tokenization (Python AST incompatible with Blade syntax), context-aware filtering

**Why manual parsing in PHPProcessor?** Standard Python AST doesn't handle Blade syntax in PHP files. Manual scanning preserves position data (line/column/length) needed for output.

**Current approach (NO MASKING):**
- Parse original content directly with BeautifulSoup
- Filter excluded patterns afterwards using `_should_exclude_text()` and `_is_in_excluded_range()`
- Position accuracy: 97% (3% are file boundary cases with fewer context lines)

## Command Line Options

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

## Output Format

**⚠️ IMPORTANT: Automatic File Splitting**

Output files are **automatically split** when extracting many strings:
- **Default threshold**: 100 items per file
- **File naming**: `output.json` → `output-01.json`, `output-02.json`, `output-03.json`, ...
- **Control**: `--split-threshold NUM` to customize (0 = disable splitting)
- **Implementation**: `src/refactor/utils/output_formatter.py` (`_write_to_files()`)

**When validating or testing output:**
- Always check for numbered files (e.g., `output-1.json`, `output-2.json`)
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
            "line": 10,        // 1-based
            "column": 5,       // 0-based
            "length": 15,      // character count
            "context": [       // 5 lines (2 before + target + 2 after)
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

## Smart Exclusion System

### Blade Excludes

**Translation functions:**
- `{{ __() }}`, `{{ trans() }}`, `@lang()`
- `{!! __() !!}`, `{!! trans() !!}`

**Variables:**
- `{{ $variable }}`, `{!! $variable !!}`

**Directives:**
- `@if()`, `@foreach()`, `@endif`, `@endforeach`
- `@php...@endphp`

**Comments:**
- `<!-- HTML comments -->`
- `{{-- Blade comments --}}`

### PHP Excludes

**Translation functions:**
- `__()`, `trans()`, `Lang::get()`

**Logs:**
- `Log::info()`, `logger()`, `error_log()`

**Console output:**
- `echo`, `print`, `var_dump()`, `dd()`, `dump()`

**Command output:**
- `$this->info()`, `$this->error()`, `$this->warn()`

**Array keys:**
- `'key' => 'value'` (values are extracted, keys are excluded)

**Context filtering:** PHPProcessor checks 200 chars before string literals using regex patterns (see `_should_include_string()`).

### Laravel Auto-Detection

- Searches for `composer.json` to identify Laravel project roots
- Auto-excludes: `vendor/`, `node_modules/`, `storage/`, `bootstrap/cache/`, `public/`
- See `LARAVEL_AUTO_EXCLUDE_DIRS` in `file_finder.py`
- User-specified `-e` exclusions layer on top

## Development Commands

```bash
# Run locally using project venv
venv/bin/python src/refactor/main.py extract <dir> -o output.json

# Code quality (line-length=160, see pyproject.toml)
venv/bin/black src/
venv/bin/pylint src/

# Quick test with temp files
mkdir -p /tmp/test-laravel/resources/views
echo '<p>Test 日本語</p>' > /tmp/test-laravel/resources/views/test.blade.php
venv/bin/python src/refactor/main.py extract /tmp/test-laravel -o test-output.json

# Validate output (check for numbered files!)
ls -la output/
venv/bin/python scripts/validate_output.py output/output-N.json
```

## Key Implementation Details

### Position Data Format

All processors return: `List[Tuple[str, int, int, int]]`

- `(text, line, column, length)`
- **Line:** 1-based (human-readable)
- **Column:** 0-based (programming standard)
- **Length:** character count (not bytes)

### Character Filtering

Both processors strip whitespace and skip:
- Empty/whitespace-only strings
- ASCII-only digits/symbols (e.g., "123", "===")
- **Exception:** Non-ASCII chars (Japanese, emoji) bypass symbol check

**Implementation:** `_contains_non_ascii()` → `ord(char) > 127`

### File Organization

```
src/refactor/
├── main.py                    # CLI entry (argparse)
├── actions/
│   └── extract.py             # Orchestration logic
├── mods/
│   ├── blade_processor.py     # Blade template extraction
│   └── php_processor.py       # PHP file extraction
└── utils/
    ├── file_finder.py         # Glob + Laravel exclusions
    ├── output_formatter.py    # JSON output + auto-splitting
    ├── string_processor.py    # Position calculation utilities
    └── php_analyzer.py        # PHP code analysis
```

### String Position Calculation

Both processors calculate positions from original file content, then adjust after stripping:

```python
# Extract with position from original content
text, line, column, length = processor.extract()

# Adjust after stripping whitespace
stripped_text, adjusted_column, stripped_length = StringProcessor.adjust_text_position(text, column)
```

**Current accuracy:** 97% (3% are file boundary cases with fewer context lines)

## Debugging Checklist

### Missing Strings?

1. **File auto-excluded?** Check `LARAVEL_AUTO_EXCLUDE_DIRS` or `-e` flags
2. **Processor routing:** `.blade.php` exact match required (not just `.php`)
3. **Add debug prints:** `_should_exclude_text()` (Blade), `_should_include_string()` (PHP)
4. **Test regex isolation:** `re.search(pattern, context)`

### Wrong Positions?

- Processors calculate from **original content** (not masked)
- Use `_find_all_occurrences()` on `self.content`
- Check `StringProcessor.get_line_column()` for position calculation
- Verify `adjust_text_position()` for column adjustment after stripping

### Blade Syntax Leaking?

- Check `_should_exclude_text()` with `BLADE_SYNTAX_PATTERN`
- Verify exclusion ranges in `_identify_excluded_ranges()`
- Ensure `_is_in_excluded_range()` is called in `process()` method

### Position Calculation Issues?

```python
# Text nodes from BeautifulSoup may include newlines
# Solution: Split by newlines and process each line separately
for line_text in text.splitlines():
    stripped_line = line_text.strip()
    if stripped_line:
        for line, column, length in self._find_all_occurrences(stripped_line):
            results.append((stripped_line, line, column, length))
```

## Critical Constraints

### DO:

- **Preserve line/column conventions:** Line is 1-based, column is 0-based
- **Use absolute paths:** `file_path.resolve()` in output
- **Consult spec before changes:** Check `Documents/システム仕様書.md` before modifying exclusion patterns
- **Handle failures gracefully:** Individual file failures print warnings but don't halt processing
- **Default values in main.py only:** All command-line parameter defaults must be in `main.py` argparse configuration

### DON'T:

- **Use Python AST for parsing:** Incompatible with Blade syntax
- **Modify exclusion patterns without spec review:** Changes must align with `システム仕様書.md`
- **Change indexing conventions:** Breaks tooling compatibility (line: 1-based, column: 0-based)
- **Run build/upload commands as agent:** PyPI operations are developer-only
- **Define defaults outside main.py:** Prevents inconsistency across codebase

## Project Specifics

- **No test suite:** Manual validation with real Laravel projects
- **Bilingual docs:** `README.md` (EN) + `README-ja.md` (JA) + `Documents/システム仕様書.md` (spec)
- **Build system:** Setuptools (`[build-system]` in pyproject.toml)
- **Entry point:** `[project.scripts]` → `laravel-i18n-refactor` command
- **Dependencies:** BeautifulSoup4 (lxml parser), no heavy frameworks
