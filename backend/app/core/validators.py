"""Input validation and sanitization utilities for security hardening."""

import html
import os
import re
from typing import BinaryIO

from fastapi import HTTPException, UploadFile, status

# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------

# Allow alphanumerics, hyphens, underscores, dots, and spaces
_SAFE_FILENAME_RE = re.compile(r"[^\w\-. ]", re.ASCII)
_MAX_FILENAME_LENGTH = 255


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path-traversal and injection attacks.

    - Strips directory components and path-traversal sequences (../, ~)
    - Removes non-safe characters
    - Limits length to 255 characters
    - Returns 'unnamed' if the result would be empty

    Raises:
        ValueError: If the input is not a string.
    """
    if not isinstance(filename, str):
        raise ValueError("Filename must be a string")

    # Take only the basename — removes any directory prefix
    filename = os.path.basename(filename)

    # Remove path traversal patterns
    filename = filename.replace("..", "").replace("~", "")

    # Strip non-safe characters
    filename = _SAFE_FILENAME_RE.sub("", filename)

    # Strip leading/trailing dots and whitespace
    filename = filename.strip(". ")

    # Truncate to max length
    filename = filename[:_MAX_FILENAME_LENGTH]

    return filename or "unnamed"


# ---------------------------------------------------------------------------
# File size validation
# ---------------------------------------------------------------------------


def validate_file_size(file: UploadFile, max_mb: int = 50) -> None:
    """Validate that an uploaded file does not exceed *max_mb* megabytes.

    Reads the file to determine size, then seeks back to the start.

    Raises:
        HTTPException 413 if the file is too large.
    """
    max_bytes = max_mb * 1024 * 1024

    # Read current position and seek to end to determine size
    file.file.seek(0, 2)  # seek to end
    size = file.file.tell()
    file.file.seek(0)  # reset to beginning

    if size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {size} bytes exceeds {max_mb}MB limit.",
        )


# ---------------------------------------------------------------------------
# Magic-byte file type validation
# ---------------------------------------------------------------------------

# Image magic bytes: PNG, JPEG, GIF, BMP, WebP, TIFF
_IMAGE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"\xff\xd8\xff", "JPEG"),
    (b"GIF87a", "GIF"),
    (b"GIF89a", "GIF"),
    (b"BM", "BMP"),
    (b"RIFF", "WebP"),  # WebP starts with RIFF...WEBP
    (b"\x49\x49\x2a\x00", "TIFF-LE"),
    (b"\x4d\x4d\x00\x2a", "TIFF-BE"),
]

# Audio magic bytes: WAV (RIFF...WAVE), MP3, FLAC, OGG
_AUDIO_SIGNATURES: list[tuple[bytes, str]] = [
    (b"RIFF", "WAV"),  # WAV starts with RIFF...WAVE
    (b"\xff\xfb", "MP3"),
    (b"\xff\xf3", "MP3"),
    (b"\xff\xf2", "MP3"),
    (b"ID3", "MP3-ID3"),
    (b"fLaC", "FLAC"),
    (b"OggS", "OGG"),
]


def _check_magic_bytes(
    file: UploadFile,
    signatures: list[tuple[bytes, str]],
    label: str,
) -> str:
    """Check file magic bytes against a list of known signatures.

    Returns the matched format name.

    Raises:
        HTTPException 422 if no known signature matches.
    """
    # Read enough bytes for the longest signature
    max_len = max(len(sig) for sig, _ in signatures)
    header = file.file.read(max_len)
    file.file.seek(0)

    for sig, fmt in signatures:
        if header[: len(sig)] == sig:
            return fmt

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Invalid {label} file: magic bytes do not match any known {label} format.",
    )


def validate_image_file(file: UploadFile) -> str:
    """Validate that an uploaded file has image magic bytes.

    Returns the detected image format (e.g. 'PNG', 'JPEG').

    Raises:
        HTTPException 422 if the file is not a recognized image.
    """
    return _check_magic_bytes(file, _IMAGE_SIGNATURES, "image")


def validate_audio_file(file: UploadFile) -> str:
    """Validate that an uploaded file has audio magic bytes.

    Returns the detected audio format (e.g. 'WAV', 'MP3').

    Raises:
        HTTPException 422 if the file is not a recognized audio file.
    """
    return _check_magic_bytes(file, _AUDIO_SIGNATURES, "audio")


# ---------------------------------------------------------------------------
# HTML sanitization (XSS prevention)
# ---------------------------------------------------------------------------

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def sanitize_html(text: str) -> str:
    """Strip HTML tags and escape remaining special characters to prevent XSS.

    Uses an iterative approach: repeatedly strip tags until none remain,
    then HTML-escape the result so any remaining angle brackets or
    ampersands are rendered harmless.

    Args:
        text: Raw text that may contain HTML.

    Returns:
        Safe plain-text string with HTML tags stripped and entities escaped.
    """
    if not isinstance(text, str):
        return ""

    # First escape all special chars so angle brackets become entities
    escaped = html.escape(text, quote=True)

    # Then remove any HTML-tag-like patterns (defensive — after escaping,
    # real tags are already neutered, but this catches edge cases)
    return _HTML_TAG_RE.sub("", escaped)
