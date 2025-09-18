"""
Text Summarization Skill (Simple)
"""
import re

def skill(text: str, max_sentences: int = 3) -> str:
    """
    Summarizes text by taking the first few sentences.
    A real implementation would use a more sophisticated algorithm.

    :param text: The text to summarize.
    :param max_sentences: The maximum number of sentences in the summary.
    :return: The summarized text.
    """
    if not text:
        return ""

    # Normalize whitespace and split by sentences
    normalized_text = re.sub(r'\s+', ' ', text).strip()
    sentences = normalized_text.split('.')

    # Filter out empty strings that may result from splitting
    sentences = [s.strip() for s in sentences if s.strip()]

    # Take the first `max_sentences` and join them back
    summary_sentences = sentences[:max_sentences]

    if not summary_sentences:
        return ""

    result = ". ".join(summary_sentences)
    # Ensure it ends with a single period.
    if not result.endswith('.'):
        result += '.'

    return result
