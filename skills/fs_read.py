"""
Filesystem Read Skill
"""
from pathlib import Path

def skill(filepath: str) -> str:
    """
    Reads the content of a file.

    :param filepath: The path to the file.
    :return: The content of the file as a string.
    """
    try:
        return Path(filepath).read_text()
    except Exception as e:
        return f"Error reading file: {e}"
