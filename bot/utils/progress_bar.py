"""
Progress bar generator for messages.
Used in bulk uploads, processing.
"""


def generate_progress_bar(
    current: int,
    total: int,
    length: int = 15,
    filled_char: str = "█",
    empty_char: str = "░"
) -> str:
    """
    Generate a text progress bar.

    Args:
        current: Current progress
        total: Total items
        length: Bar length in chars
        filled_char: Filled block char
        empty_char: Empty block char

    Returns:
        Progress bar string

    Example:
        generate_progress_bar(5, 10)
        → '[███████░░░░░░░░] 50%'
    """
    if total <= 0:
        percent = 0
    else:
        percent = min(
            100, int((current / total) * 100)
        )

    filled = int(length * current // max(total, 1))
    filled = min(filled, length)

    bar = (
        filled_char * filled
        + empty_char * (length - filled)
    )
    return f"[{bar}] {percent}%"


def generate_simple_bar(
    current: int, total: int
) -> str:
    """Simple progress with count."""
    bar = generate_progress_bar(current, total)
    return f"{bar} ({current}/{total})"