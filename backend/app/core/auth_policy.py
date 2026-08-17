"""The single, explicit definition of what may be reached without identity.

This module exists so that "is this endpoint public?" has exactly one answer in
the codebase, and so tests can import that answer instead of re-stating it.

Design note: the allowlist is *deny by default*. Adding a route to the app does
not make it public; adding it here does, and that is a reviewable one-line diff
in a file whose whole purpose is to be scrutinised.
"""

from __future__ import annotations

# Exact paths reachable without a token. Trailing slashes are normalised away
# before matching, so "/api/health" also covers "/api/health/".
PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        # Liveness / readiness — probes cannot hold credentials.
        "/api/health",
        # Prometheus scrape target — protected at the network layer, not by JWT.
        "/api/metrics",
        # Credential exchange: you cannot present a token to obtain a token.
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        # OpenAPI surface.
        "/docs",
        "/redoc",
        "/openapi.json",
        "/docs/oauth2-redirect",
        # Bare root: Next.js/uptime probes hit it; it serves no data.
        "/",
    }
)

# Path *prefixes* reachable without a token. Kept deliberately short — a prefix
# opens everything beneath it, so each entry must be a static asset tree.
PUBLIC_PATH_PREFIXES: tuple[str, ...] = (
    "/static/",
    "/favicon",
)

# Methods that never carry credentials. OPTIONS is the CORS preflight: the
# browser sends it *without* the Authorization header by design, so rejecting it
# breaks every cross-origin call before the real request is ever made.
PUBLIC_METHODS: frozenset[str] = frozenset({"OPTIONS"})


def normalise_path(path: str) -> str:
    """Collapse a request path to its canonical allowlist form."""
    if len(path) > 1 and path.endswith("/"):
        return path.rstrip("/") or "/"
    return path


def is_public(path: str, method: str = "GET") -> bool:
    """Return True when *path* may be served without an authenticated identity."""
    if method.upper() in PUBLIC_METHODS:
        return True

    candidate = normalise_path(path)
    if candidate in PUBLIC_PATHS:
        return True

    return any(candidate.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES)
