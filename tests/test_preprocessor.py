"""Tests for base64 image stripping."""

from kiku.preprocessor import strip_base64_images


def test_strips_base64_image() -> None:
    text = (
        "Some text before\n"
        "![Screenshot](data:image/webp;base64,UklGRooJAABXRUJQ)\n"
        "Some text after"
    )
    cleaned, original, stripped = strip_base64_images(text)
    assert "base64" not in cleaned
    assert "[image removed]" in cleaned
    assert "Some text before" in cleaned
    assert "Some text after" in cleaned
    assert stripped > 0


def test_preserves_normal_images() -> None:
    text = "![alt](https://example.com/image.png)\nMore text"
    cleaned, _, stripped = strip_base64_images(text)
    assert stripped == 0
    assert cleaned == text


def test_no_images() -> None:
    text = "Just plain text\nNo images here"
    cleaned, _, stripped = strip_base64_images(text)
    assert stripped == 0
    assert cleaned == text


def test_multiple_base64_images() -> None:
    text = (
        "![a](data:image/png;base64,AAAA)\n"
        "middle\n"
        "![b](data:image/jpeg;base64,BBBB)\n"
    )
    cleaned, _, _ = strip_base64_images(text)
    assert cleaned.count("[image removed]") == 2
    assert "middle" in cleaned
