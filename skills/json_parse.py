"""
JSON Parse Skill
"""
import json

def skill(json_string: str) -> dict:
    """
    Parses a JSON string into a Python dictionary.

    :param json_string: The JSON string to parse.
    :return: A dictionary representing the JSON object.
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}
