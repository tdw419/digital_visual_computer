"""
Filesystem Write Skill
"""
from pathlib import Path

def skill(filepath: str, content: str) -> str:
    """
    Writes content to a file.

    :param filepath: The path to the file.
    :param content: The content to write.
    :return: A status message.
    """
    try:
        Path(filepath).write_text(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing to file: {e}"
