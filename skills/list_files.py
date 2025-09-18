"""
List Files Skill
"""
from pathlib import Path

def skill(directory: str) -> list:
    """
    Lists files in a given directory.

    :param directory: The path to the directory.
    :return: A list of files and directories.
    """
    try:
        return [str(p) for p in Path(directory).iterdir()]
    except Exception as e:
        return [f"Error listing files: {e}"]
