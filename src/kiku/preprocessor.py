"""Strip base64-encoded images and other binary blobs from conversation exports."""

import re

_BASE64_IMAGE_PATTERN = re.compile(
    r"!\[[^\]]*\]\(data:image/[a-zA-Z]+;base64,[A-Za-z0-9+/=\s]+\)"
)


def strip_base64_images(text: str) -> tuple[str, int, int]:
    """Remove base64-encoded inline images from markdown text.

    Returns:
        Tuple of (cleaned_text, original_size, stripped_size).
    """
    original_size = len(text)
    cleaned = _BASE64_IMAGE_PATTERN.sub("[image removed]", text)
    stripped_size = original_size - len(cleaned)
    return cleaned, original_size, stripped_size
