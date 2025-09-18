"""
Text Split Skill
"""

def skill(text: str, delimiter: str = '\\n') -> list:
    """
    Splits text by a given delimiter.

    :param text: The text to split.
    :param delimiter: The delimiter to split by. Handles '\\n' for newlines.
    :return: A list of strings.
    """
    if delimiter == '\\n':
        return text.splitlines()
    return text.split(delimiter)
