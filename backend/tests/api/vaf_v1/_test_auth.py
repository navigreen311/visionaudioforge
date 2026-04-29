"""Test-only auth dependency override for VAF v1 intel endpoints.

WS10 owns the real auth dependency at ``app/api/deps/vaf_auth.py``. Until
that lands, tests substitute this no-op stand-in via FastAPI's
``dependency_overrides`` mechanism. We do NOT create a competing
``vaf_auth.py`` under ``app/api/deps/``.
"""

from __future__ import annotations


async def noop_vaf_auth() -> str:
    """Always-pass auth dependency for unit tests."""
    return "test-token"
