"""
HTTP GET Skill
"""
import requests

def skill(url: str) -> str:
    """
    Performs an HTTP GET request to the given URL.

    :param url: The URL to fetch.
    :return: The content of the response.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.text
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL: {e}"
