"""Shared fixtures for VAF v1 mock-API tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def vaf_headers() -> dict:
    """Authorization header accepted by the mock VAF auth dependency."""
    return {"Authorization": "Bearer vaf-test-token"}


@pytest.fixture
def tiny_audio() -> bytes:
    """Small placeholder audio payload — the mock never decodes it."""
    return b"RIFFmockWAVEmockmockmock"
