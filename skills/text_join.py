"""
Text Join Skill
"""

def skill(text_list: list, separator: str = '\\n') -> str:
    """
    Joins a list of strings with a given separator.

    :param text_list: The list of strings to join.
    :param separator: The separator to use. Handles '\\n' for newlines.
    :return: The joined string.
    """
    if separator == '\\n':
        return "\\n".join(text_list)
    return separator.join(text_list)
