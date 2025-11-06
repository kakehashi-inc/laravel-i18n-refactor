"""
Exclusion dictionary management utilities.

Handles loading of exclusion dictionaries from files.
"""

from pathlib import Path
from typing import Set


def load_exclusion_dict(file_path: Path) -> Set[str]:
    """
    Load exclusion dictionary from a file.

    Args:
        file_path: Path to the exclusion dictionary file

    Returns:
        Set of words to exclude (exact match including case)
    """
    exclusion_dict = set()

    if not file_path.exists():
        return exclusion_dict

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word:  # Skip empty lines
                    exclusion_dict.add(word)
    except (OSError, IOError):
        pass

    return exclusion_dict
