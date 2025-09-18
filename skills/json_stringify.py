"""
JSON Stringify Skill
"""
import json

def skill(data: dict) -> str:
    """
    Converts a Python dictionary to a JSON string.

    :param data: The dictionary to convert.
    :return: A JSON string representation of the dictionary.
    """
    try:
        return json.dumps(data, indent=2)
    except TypeError as e:
        return f'{{"error": "Could not serialize to JSON: {e}"}}'
