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

```
laravel-i18n-refactor extract <directory> [OPTIONS]

Arguments:
  directory              Target directory to search for files

Options:
  -n, --name PATTERN    File name pattern (default: "**/*.php")
  -o, --output FILE     Output JSON file path (default: stdout)
  -h, --help           Show this help message
```

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
            "length": 25
          }
        ]
      }
    ]
  }
]
```

### Field Descriptions

- `text`: The extracted string content (preserves newlines, tabs, spaces, and escape sequences)
- `occurrences`: Array of locations where the string appears
- `file`: File path (relative to the search directory)
- `positions`: Array of positions within the same file
- `line`: Line number (1-based)
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

**PHP extraction:**
```php
// Extracted: "This field is required"
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
