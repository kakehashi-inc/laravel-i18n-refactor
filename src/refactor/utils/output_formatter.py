"""
Output formatter for extracted strings.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, TextIO, Optional


def format_output(results: List[Dict[str, Any]], output_path: Optional[Path] = None) -> None:
    """
    Format and output the extraction results as JSON.

    Args:
        results: List of extraction results with structure:
            [
                {
                    "text": "extracted string",
                    "occurrences": [
                        {
                            "file": "path/to/file.php",
                            "positions": [
                                {"line": 10, "column": 5, "length": 15}
                            ]
                        }
                    ]
                }
            ]
        output_path: Output file path. If None, writes to stdout.
    """
    # Sort results by text for consistency
    sorted_results = sorted(results, key=lambda x: x.get('text', ''))

    # Convert to JSON with proper formatting
    json_output = json.dumps(
        sorted_results,
        ensure_ascii=False,
        indent=2,
        sort_keys=False
    )

    if output_path:
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_output)
            f.write('\n')  # Add trailing newline
    else:
        # Write to stdout
        print(json_output)


def write_json(data: List[Dict[str, Any]], file: TextIO) -> None:
    """
    Write JSON data to a file handle.

    Args:
        data: Data to serialize as JSON
        file: File handle to write to
    """
    json.dump(
        data,
        file,
        ensure_ascii=False,
        indent=2,
        sort_keys=False
    )
    file.write('\n')
