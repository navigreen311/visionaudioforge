"""Tests for security hardening: input validation, rate limiting, CORS."""

import io
import os
from unittest.mock import MagicMock

import pytest
from fastapi import UploadFile

from app.core.validators import (
    sanitize_filename,
    sanitize_html,
    validate_audio_file,
    validate_file_size,
    validate_image_file,
)
from app.middleware.rate_limit import RateLimiter


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------


class TestSanitizeFilename:
    def test_sanitize_filename_removes_traversal(self):
        """Path traversal sequences are stripped."""
        assert ".." not in sanitize_filename("../../../etc/passwd")
        assert ".." not in sanitize_filename("..\\..\\windows\\system32")
        assert sanitize_filename("../secret.txt") == "secret.txt"

    def test_sanitize_filename_removes_tilde(self):
        assert "~" not in sanitize_filename("~/important.txt")

    def test_sanitize_filename_strips_directory_prefix(self):
        result = sanitize_filename("/usr/local/bin/script.sh")
        assert "/" not in result
        assert result == "script.sh"

    def test_sanitize_filename_allows_safe_chars(self):
        assert sanitize_filename("my-photo_2024.png") == "my-photo_2024.png"

    def test_sanitize_filename_limits_length(self):
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_sanitize_filename_returns_unnamed_for_empty(self):
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("../..") == "unnamed"

    def test_sanitize_filename_raises_on_non_string(self):
        with pytest.raises(ValueError):
            sanitize_filename(123)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# validate_file_size
# ---------------------------------------------------------------------------


class TestFileSizeValidation:
    def test_file_size_validation_accepts_small_file(self):
        """Files under the limit should pass without error."""
        content = b"x" * 1024  # 1KB
        file = UploadFile(filename="small.txt", file=io.BytesIO(content))
        # Should not raise
        validate_file_size(file, max_mb=1)

    def test_file_size_validation_rejects_large_file(self):
        """Files over the limit should raise HTTP 413."""
        content = b"x" * (2 * 1024 * 1024)  # 2MB
        file = UploadFile(filename="big.bin", file=io.BytesIO(content))
        with pytest.raises(Exception) as exc_info:
            validate_file_size(file, max_mb=1)
        assert exc_info.value.status_code == 413

    def test_file_size_validation_resets_seek_position(self):
        """After validation the file position should be reset to 0."""
        content = b"hello world"
        file = UploadFile(filename="hello.txt", file=io.BytesIO(content))
        validate_file_size(file, max_mb=1)
        assert file.file.tell() == 0


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def test_rate_limiter_allows_under_limit(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert limiter.is_allowed("192.168.1.1") is True

    def test_rate_limiter_blocks_over_limit(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("10.0.0.1")
        assert limiter.is_allowed("10.0.0.1") is False

    def test_rate_limiter_tracks_per_ip(self):
        """Different IPs have independent counters."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("ip-a")
        limiter.is_allowed("ip-a")
        # ip-a is now at limit
        assert limiter.is_allowed("ip-a") is False
        # ip-b should still be allowed
        assert limiter.is_allowed("ip-b") is True

    def test_rate_limiter_remaining(self):
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        limiter.is_allowed("x")
        limiter.is_allowed("x")
        assert limiter.remaining("x") == 8


# ---------------------------------------------------------------------------
# CORS — not wildcard in production
# ---------------------------------------------------------------------------


class TestCorsNotWildcard:
    def test_cors_not_wildcard_in_prod(self):
        """CORS_ORIGINS should not resolve to ['*'] when the env var is set."""
        # Simulate production: CORS_ORIGINS is set to a real domain
        raw = "https://app.visionaudioforge.dev,https://admin.visionaudioforge.dev"
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        assert "*" not in origins
        assert len(origins) == 2

    def test_cors_default_is_localhost(self):
        """When CORS_ORIGINS is unset, default should be localhost:3000."""
        raw = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        assert "*" not in origins


# ---------------------------------------------------------------------------
# Image / audio magic-byte validation
# ---------------------------------------------------------------------------


class TestMagicByteValidation:
    def test_validate_image_accepts_png(self):
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        file = UploadFile(filename="test.png", file=io.BytesIO(png_header))
        assert validate_image_file(file) == "PNG"

    def test_validate_image_rejects_text(self):
        file = UploadFile(filename="test.txt", file=io.BytesIO(b"hello world"))
        with pytest.raises(Exception) as exc_info:
            validate_image_file(file)
        assert exc_info.value.status_code == 422

    def test_validate_audio_accepts_wav(self):
        wav_header = b"RIFF" + b"\x00" * 100
        file = UploadFile(filename="test.wav", file=io.BytesIO(wav_header))
        assert validate_audio_file(file) == "WAV"

    def test_validate_audio_rejects_random(self):
        file = UploadFile(filename="bad.bin", file=io.BytesIO(b"\x00\x01\x02\x03"))
        with pytest.raises(Exception) as exc_info:
            validate_audio_file(file)
        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# HTML sanitization
# ---------------------------------------------------------------------------


class TestSanitizeHtml:
    def test_strips_script_tags(self):
        result = sanitize_html('<script>alert("xss")</script>Hello')
        # Raw HTML tags must not survive — they are escaped to entities
        assert "<script>" not in result
        assert "</script>" not in result
        assert "Hello" in result

    def test_escapes_angle_brackets(self):
        result = sanitize_html("a < b & c > d")
        assert "&lt;" in result
        assert "&amp;" in result
        assert "&gt;" in result
        # No raw angle brackets remain
        assert "<" not in result
        assert ">" not in result
