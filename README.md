# Laravel i18n Refactor Tool

A CLI tool to help with Laravel internationalization by extracting hardcoded strings from Blade templates and PHP files.

## Features

- 🔍 Automatically detects hardcoded strings in Laravel projects
- 📝 Supports both Blade templates and PHP files
- 🎯 Smart filtering to exclude already translated strings
- 📊 Consolidates duplicate strings across multiple files
- 📁 Outputs structured JSON for easy integration

## Installation

```bash
# Using uvx (recommended - no installation required)
uvx laravel-i18n-refactor extract .

# Or install with uv
uv pip install laravel-i18n-refactor

# Or install with pip
pip install laravel-i18n-refactor
```

## Usage

### Extract hardcoded strings

```bash
# Using uvx (no installation required)
uvx laravel-i18n-refactor extract .

# Extract from Blade templates only
uvx laravel-i18n-refactor extract resources/views -n "**/*.blade.php" -o strings.json

# Extract from specific directory
uvx laravel-i18n-refactor extract app/Http/Controllers -n "*.php" -o output.json

# If installed, you can use the command directly
laravel-i18n-refactor extract .
```

### Command Line Options

```text
laravel-i18n-refactor extract <directory> [OPTIONS]

Arguments:
  directory                 Target directory to search for files

Options:
  -n, --name PATTERN        File name pattern (default: "**/*.php")
                            Examples: "**/*.blade.php", "*.php", "**/*_controller.php"

  -o, --output FILE         Output JSON file path (default: stdout)
                            If not specified, output is written to stdout

  -e, --exclude DIR         Directory names to exclude (can be specified multiple times, default: node_modules)
                            Example: -e vendor -e storage -e tests

  --split-threshold NUM     Threshold for splitting output into multiple files (default: 100)
                            When extracted strings exceed this number, automatically split into multiple files
                            Use 0 to disable splitting

  --min-bytes NUM           Minimum byte length for extracted strings (default: 2)
                            Strings with fewer bytes than this value will be excluded

  --include-hidden          Include hidden directories (directories starting with .) in search
                            Default: False (hidden directories are skipped)

  --context-lines NUM       Number of context lines to include in output (default: 5)
                            5 means: 2 lines before + target line + 2 lines after
                            Use 0 to disable context output

  --enable-blade            Enable processing of .blade.php files (default: True)

  --disable-blade           Disable processing of .blade.php files

  --enable-php              Enable processing of regular .php files (default: False)

  --disable-php             Disable processing of regular .php files (this is the default)

  -h, --help                Show this help message

Examples:
  # Basic usage (Blade files only, default settings)
  uvx laravel-i18n-refactor extract .

  # Exclude multiple directories
  uvx laravel-i18n-refactor extract . -e node_modules -e storage -e bootstrap/cache

  # Extract only from specific pattern with exclusions
  uvx laravel-i18n-refactor extract . -n "**/*.blade.php" -e tests -e vendor

  # Process both Blade and PHP files
  uvx laravel-i18n-refactor extract . --enable-php -o output.json

  # Change split threshold (split every 200 items)
  uvx laravel-i18n-refactor extract . -o output.json --split-threshold 200

  # Disable splitting (output everything in a single file)
  uvx laravel-i18n-refactor extract . -o output.json --split-threshold 0

  # Change context lines (7 lines: 3 before + target + 3 after)
  uvx laravel-i18n-refactor extract . -o output.json --context-lines 7

  # Disable context output
  uvx laravel-i18n-refactor extract . -o output.json --context-lines 0

  # Change minimum byte length (exclude strings with less than 3 bytes)
  uvx laravel-i18n-refactor extract . -o output.json --min-bytes 3

  # Include hidden directories in search
  uvx laravel-i18n-refactor extract . --include-hidden
```

### Automatic Exclusions

The tool automatically detects Laravel projects (by finding `composer.json`) and excludes:

**User-specified exclusions:**
- Directories specified with `-e`/`--exclude` (default: `node_modules`)

**Laravel project auto-exclusions:**
- `vendor` - Composer dependencies
- `node_modules` - NPM dependencies
- `public` - Public assets (compiled/generated files)
- `storage` - Storage directory (logs, cache, sessions)
- `bootstrap/cache` - Bootstrap cache files

These auto-exclusions ensure that dependencies and generated files are not processed, keeping the focus on your source code.

## Output Format

The tool generates a JSON file with the following structure:

```json
[
  {
    "text": "Extracted string content",
    "occurrences": [
      {
        "file": "resources/views/example.blade.php",
        "positions": [
          {
            "line": 10,
            "column": 5,
            "length": 25,
            "context": [
              "    <div>",
              "        <h1>Extracted string content</h1>",
              "    </div>"
            ]
          }
        ]
      }
    ]
  }
]
```

### Automatic File Splitting

When extracting a large number of strings, the output is automatically split into multiple files:

- **Default**: Split every 100 items
- **Split Example**: `output.json` → `output-01.json`, `output-02.json`, `output-03.json`, ...
- **Customization**: Use `--split-threshold` option to change the threshold
- **Disable Splitting**: Use `--split-threshold 0` to output everything in a single file

```bash
# Default (split every 100 items)
uvx laravel-i18n-refactor extract . -o output.json

# Custom threshold (split every 200 items)
uvx laravel-i18n-refactor extract . -o output.json --split-threshold 200

# Disable splitting (single file)
uvx laravel-i18n-refactor extract . -o output.json --split-threshold 0
```

**Note**: When outputting to stdout (without `-o` option), no splitting occurs.

### Field Descriptions

- `text`: The extracted string content (preserves newlines, tabs, spaces, and escape sequences)
- `occurrences`: Array of locations where the string appears
- `file`: File path (relative to the search directory)
- `positions`: Array of positions within the same file
- `line`: Line number (1-based)
- `column`: Column number (0-based)
- `length`: String length (character count)
- `context`: Context lines (target line and 2 lines before/after, total 5 lines, may be less at file boundaries)
- `column`: Column number (0-based)
- `length`: String length (character count)

## What Gets Extracted

### Blade Files (.blade.php)

**✅ Extracted:**
- Text nodes between HTML tags
- HTML attribute values
- JavaScript string literals in `<script>` tags

**❌ Excluded:**
- Already translated strings (`{{ __() }}`, `@lang()`, etc.)
- PHP variables (`{{ $variable }}`)
- Blade directives (`@if`, `@foreach`, etc.)
- Comments (HTML and Blade)
- Empty or whitespace-only strings

### PHP Files (.php)

**✅ Extracted:**
- Validation messages
- Exception messages
- Response messages
- User-facing error and success messages

**❌ Excluded:**
- Already translated strings (`__()`, `trans()`, etc.)
- Log messages (`Log::info()`, `logger()`, etc.)
- Console output (`echo`, `print`, `var_dump()`, etc.)
- Command output (`$this->info()`, `$this->error()`, etc.)
- Array keys
- Comments
- Empty or whitespace-only strings

### Examples

**Blade extraction:**
```html
<!-- Extracted: "Welcome to Laravel" -->
<h1>Welcome to Laravel</h1>

<!-- Extracted: "Enter your name" -->
<input placeholder="Enter your name">

<!-- Excluded: already translated -->
<p>{{ __('messages.welcome') }}</p>

<!-- Excluded: variable -->
<p>{{ $userName }}</p>
```

## Exclusion Dictionary

You can exclude specific strings from extraction using an exclusion dictionary file.

### Basic Usage

Create an `exclude-dict.txt` file in your project root, and it will be automatically loaded:

```bash
# Create exclusion dictionary in project root
cat > exclude-dict.txt << 'EOF'
# Comments: lines starting with # are ignored

# Exact matches (case-sensitive)
label
class
style
name

# Wildcard patterns
data-*
autocomplete*
*-icon

# Negation patterns (starting with !)
# Re-include strings that were excluded by previous patterns
!class-name
!data-important

# Array key patterns
'*' =>*
EOF

# Run extraction with exclusion dictionary
uvx laravel-i18n-refactor extract .
```

### Syntax

The exclusion dictionary supports both glob patterns and regular expressions:

| Syntax | Description | Example |
|--------|-------------|---------|
| `word` | Exact match (case-sensitive) | `label` excludes "label" |
| `*` | Wildcard matches any characters | `data-*` excludes "data-id", "data-name" |
| `[0-9]` | Character class | `[0-9]*` excludes strings starting with digits |
| `regex:PATTERN` | Regular expression | `regex:^\d+x\d+$` excludes "600x600", "1920x1080" |
| `!pattern` | Negation (include despite previous exclusion) | `!data-important` includes "data-important" |
| `# comment` | Comment line (ignored) | `# This is a comment` |

### Regular Expression Patterns

For more precise pattern matching, use the `regex:` prefix:

```text
# Exclude dimension patterns (e.g., 600x600, 1920x1080)
regex:^\d+x\d+$

# Exclude 3-4 digit numbers only
regex:^\d{3,4}$

# Exclude uppercase 2-3 letter codes
regex:^[A-Z]{2,3}$

# Exclude hex color codes
regex:^#[0-9a-fA-F]{3,6}$

# Exclude version numbers
regex:^\d+\.\d+\.\d+$
```

**Note**: Regular expressions are evaluated as Python regex patterns. Invalid regex patterns are silently ignored.

### Pattern Examples

**Glob patterns:**

```text
# Exclude HTML attributes
class
style
id

# Exclude data-* attributes (but keep specific ones)
data-*
!data-label
!data-message

# Form-related attributes
name
type
value
placeholder

# But keep user-facing placeholders
!placeholder-text

# Configuration keys
*_config
*.env
```

**Regular expression patterns:**

```text
# Exclude dimension patterns (600x600, 1920x1080)
regex:^\d+x\d+$

# Exclude hex color codes
regex:^#[0-9a-fA-F]{3,6}$

# Exclude version numbers
regex:^\d+\.\d+\.\d+$
```

### Embedded Exclusion Dictionary

The tool includes an embedded dictionary that excludes common 2-letter language codes (ISO 639-1). This is automatically merged with your custom dictionary.

**Note**: Custom dictionary patterns are evaluated after the embedded dictionary, so negation patterns (`!`) can override embedded exclusions.

```text
# "en" is excluded by embedded dictionary, but you can include it
!en
```


'required' => 'This field is required',

// Extracted: "User not found"
throw new Exception('User not found');

// Excluded: already translated
__('messages.welcome')

// Excluded: log message
Log::info('Processing started');

// Excluded: array key, but "John" is extracted
'name' => 'John',
```

## Development

Create and activate a virtual environment:

```bash
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

## Requirements

- Python 3.7 or higher
- beautifulsoup4 >= 4.12.0
- lxml >= 4.9.0

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Related Documentation

- [日本語版 README](README-ja.md)
