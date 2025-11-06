"""
Output formatter for extracted strings.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional


def format_output(results: List[Dict[str, Any]], output_path: Optional[Path] = None, split_threshold: Optional[int] = None) -> None:
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
        split_threshold: Threshold for splitting output into multiple files.
    """
    # Sort results by text for consistency
    sorted_results = sorted(results, key=lambda x: x.get("text", ""))

    if output_path:
        # Write to file(s) with splitting if necessary
        _write_to_files(sorted_results, output_path, split_threshold)
    else:
        # Write to stdout without splitting
        json_output = json.dumps(sorted_results, ensure_ascii=False, indent=2, sort_keys=False)
        print(json_output)


def _write_to_files(results: List[Dict[str, Any]], output_path: Path, split_threshold: Optional[int]) -> None:
    """
    Write results to one or more files, splitting if necessary.

    Args:
        results: Sorted list of extraction results
        output_path: Base output file path
        split_threshold: Threshold for splitting output into multiple files
    """
    total_items = len(results)

    if split_threshold == None or total_items <= split_threshold:
        # No splitting needed, write to single file
        _write_json_file(results, output_path)
    else:
        # Split into multiple files
        num_files = (total_items + split_threshold - 1) // split_threshold  # Ceiling division

        # Prepare file path components
        parent = output_path.parent
        stem = output_path.stem  # filename without extension
        suffix = output_path.suffix  # .json

        for file_index in range(num_files):
            start_idx = file_index * split_threshold
            end_idx = min(start_idx + split_threshold, total_items)
            chunk = results[start_idx:end_idx]

            # Generate filename
            if file_index == 0:
                # First file keeps original name
                file_path = output_path
            else:
                # Subsequent files get -2, -3, etc.
                file_path = parent / f"{stem}-{file_index + 1}{suffix}"

            _write_json_file(chunk, file_path)


def _write_json_file(data: List[Dict[str, Any]], file_path: Path) -> None:
    """
    Write data to a JSON file.

    Args:
        data: Data to write
        file_path: Output file path
    """
    json_output = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(json_output)
        f.write("\n")  # Add trailing newline
