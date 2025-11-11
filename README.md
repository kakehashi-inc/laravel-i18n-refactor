# Laravel i18n Refactor Tool

A CLI tool to help with Laravel internationalization by extracting hardcoded strings from Blade templates and PHP files.

## Features

- 🔍 Automatically detects hardcoded strings in Laravel projects
- 📝 Supports both Blade templates and PHP files
- 🎯 Smart filtering to exclude already translated strings
- 📊 Consolidates duplicate strings across multiple files
- 📁 Outputs structured JSON for easy integration

## Usage

### String Extraction (extract)

#### Command Line Options

```text
laravel-i18n-refactor extract <directory> [OPTIONS]

Arguments:
  directory                 Target directory to search

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

  --exclude-dict FILE       Path to a text file containing strings to exclude (one per line)

  -h, --help                Show this help message

Examples:
  # Extract from Blade templates only
  uvx laravel-i18n-refactor extract resources/views -n "**/*.blade.php" -o output.json

  # Exclude multiple directories
  uvx laravel-i18n-refactor extract ~/sources/test-project -e Archive -e temp -o output.json
```

#### Output Format

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

#### Exclusion Dictionary

You can exclude specific strings from extraction using an exclusion dictionary file.

##### Syntax

The exclusion dictionary supports both glob patterns and regular expressions:

| Syntax | Description | Example |
|--------|-------------|---------|
| `word` | Exact match (case-sensitive) | `label` excludes "label" |
| `*` | Wildcard matches any characters | `data-*` excludes "data-id", "data-name" |
| `[0-9]` | Character class | `[0-9]*` excludes strings starting with digits |
| `regex:PATTERN` | Regular expression | `regex:^\d+x\d+$` excludes "600x600", "1920x1080" |
| `!pattern` | Negation (include despite previous exclusion) | `!data-important` includes "data-important" |
| `# comment` | Comment line (ignored) | `# This is a comment` |

**Note**: Regular expressions are evaluated as Python regex patterns. Invalid regex patterns are silently ignored.

### AI Translation (translate)

This tool supports translating extracted strings using various AI providers.

#### Translation Command

```bash
laravel-i18n-refactor translate <provider> --model <model-name> -i <input-file> [OPTIONS]
```

#### Available Providers

| Provider | Command | Description |
|----------|---------|-------------|
| OpenAI | `openai` |  |
| Anthropic | `anthropic` |  |
| Gemini | `gemini` |  |
| OpenAI-Compatible | `openai-compat` | OpenAI-compatible endpoints (LM Studio, LocalAI, etc.) |
| Anthropic-Compatible | `anthropic-compat` | Anthropic-compatible endpoints (MiniMax M2, etc.) |
| Ollama | `ollama` |  |

#### Common Options (All Providers)

| Option | Description |
|--------|-------------|
| `-i, --input FILE` | Input JSON file(s) to translate (can be specified multiple times) |
| `--lang CODE:DESCRIPTION` | Target language (e.g., "ja:Japanese", "en:American English") |
| `--list-models` | List available models for the provider |
| `--dry-run` | Preview translation without making API calls |

#### Provider-Specific Options

#### OpenAI

| Option | Environment Variable | Description |
|--------|---------------------|-------------|
| `--model` | `OPENAI_MODEL` | Model name (required) |
| `--api-key` | `OPENAI_API_KEY` | OpenAI API key |
| `--organization` | `OPENAI_ORGANIZATION` | Organization ID |
| `--temperature` | `OPENAI_TEMPERATURE` | Sampling temperature |
| `--max-tokens` | `OPENAI_MAX_TOKENS` | Maximum tokens |
| `--batch-size` | `OPENAI_BATCH_SIZE` | Batch size (default: 10) |

#### Anthropic (Claude)

| Option | Environment Variable | Description |
|--------|---------------------|-------------|
| `--model` | `ANTHROPIC_MODEL` | Model name (required) |
| `--api-key` | `ANTHROPIC_API_KEY` | Anthropic API key |
| `--temperature` | `ANTHROPIC_TEMPERATURE` | Sampling temperature |
| `--max-tokens` | `ANTHROPIC_MAX_TOKENS` | Maximum tokens (default: 4096) |

#### Google Gemini

| Option | Environment Variable | Description |
|--------|---------------------|-------------|
| `--model` | `GEMINI_MODEL` | Model name (required) |
| `--api-key` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | Google API key |
| `--temperature` | `GEMINI_TEMPERATURE` | Sampling temperature |
| `--max-tokens` | `GEMINI_MAX_TOKENS` | Maximum output tokens |
| `--top-p` | `GEMINI_TOP_P` | Nucleus sampling |
| `--top-k` | `GEMINI_TOP_K` | Top-k sampling |

#### OpenAI-Compatible

| Option | Environment Variable | Description |
|--------|---------------------|-------------|
| `--model` | `OPENAI_COMPAT_MODEL` | Model name (required) |
| `--api-base` | `OPENAI_COMPAT_API_BASE` | API base URL (required) |
| `--api-key` | `OPENAI_COMPAT_API_KEY` | API key (if required) |
| `--temperature` | `OPENAI_COMPAT_TEMPERATURE` | Sampling temperature |
| `--max-tokens` | `OPENAI_COMPAT_MAX_TOKENS` | Maximum tokens |

Reference value:

api-base: <http://localhost:1234/v1>

#### Anthropic-Compatible

| Option | Environment Variable | Description |
|--------|---------------------|-------------|
| `--model` | `ANTHROPIC_COMPAT_MODEL` | Model name (required) |
| `--api-base` | `ANTHROPIC_COMPAT_API_BASE` | API base URL (required) |
| `--api-key` | `ANTHROPIC_COMPAT_API_KEY` | API key (required) |
| `--temperature` | `ANTHROPIC_COMPAT_TEMPERATURE` | Sampling temperature |
| `--max-tokens` | `ANTHROPIC_COMPAT_MAX_TOKENS` | Maximum tokens (default: 4096) |

#### Ollama

| Option | Environment Variable | Description |
|--------|---------------------|-------------|
| `--model` | `OLLAMA_MODEL` | Model name (required) |
| `--api-base` | `OLLAMA_HOST` | Ollama server URL (default: http://localhost:11434) |
| `--temperature` | `OLLAMA_TEMPERATURE` | Sampling temperature |
| `--max-tokens` | `OLLAMA_MAX_TOKENS` | Maximum tokens |
| `--num-ctx` | `OLLAMA_NUM_CTX` | Context window size |
| `--top-p` | `OLLAMA_TOP_P` | Nucleus sampling |
| `--top-k` | `OLLAMA_TOP_K` | Top-k sampling |
| `--repeat-penalty` | `OLLAMA_REPEAT_PENALTY` | Repetition penalty |

## Development

### Development Environment Setup

```bash
# Clone the repository
git clone https://github.com/kakehashi-inc/laravel-i18n-refactor.git
cd laravel-i18n-refactor

python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Related Documentation

- [日本語版 README](README-ja.md)
