"""
Text Summarization Skill (Simple)
"""

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

    # Split by sentences
    sentences = text.split('.')

    # Filter out empty strings that may result from splitting
    sentences = [s.strip() for s in sentences if s.strip()]

    # Take the first `max_sentences` and join them back
    summary_sentences = sentences[:max_sentences]

    return ". ".join(summary_sentences) + "." if summary_sentences else ""
