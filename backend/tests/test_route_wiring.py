"""Guard: every API path the console calls must resolve against the route table.

The bug this exists to prevent: a route module defines endpoints, the frontend
calls them, but ``app/api/router.py`` never includes the router — so the paths
404 at runtime while every unit test still passes. Ten modules shipped that way.

The test walks ``frontend/src``, extracts every ``/api/...`` string literal it
can see, and asserts each one unifies with a mounted FastAPI route.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.main import app

# --------------------------------------------------------------------------
# Locations
# --------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
API_CLIENT = FRONTEND_SRC / "lib" / "api.ts"


# --------------------------------------------------------------------------
# Paths the console references but that are deliberately not FastAPI routes.
# Keep this list short and justified — every entry is a hole in the net.
# --------------------------------------------------------------------------

IGNORED_PATHS: set[str] = {
    # Websocket endpoints, not HTTP routes (declared via @app.websocket).
    "/api/ws",
}

# Segments the extractor produces for an interpolated value, e.g. `${id}`.
WILDCARD = "\x00"


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------

# Any single/double/backtick-quoted string. Backtick strings may contain ${...}.
_STRING_LITERAL = re.compile(r"""(['"`])((?:\\.|(?!\1).)*?)\1""", re.DOTALL)

# `const API_BASE = '/api/marketplace/byom';` — components build paths off these.
_BASE_CONST = re.compile(
    r"""(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*['"`](/api/[^'"`$]*)['"`]"""
)

_INTERPOLATION = re.compile(r"\$\{[^}]*\}")


# Files that *reason about* API paths rather than calling any. `authed-fetch.ts`
# decides whether a URL belongs to our API by testing a "/api" prefix, and the
# scanner cannot tell a prefix test from a call - it reported the bare prefix as
# an unmounted endpoint. Keep this list to files that genuinely handle routing,
# never to silence a path that really is missing.
_NON_CALLING_SOURCES = frozenset({"authed-fetch.ts"})


def _iter_source_files() -> list[Path]:
    """Return every TypeScript source file in the console that calls the API."""
    if not FRONTEND_SRC.is_dir():  # pragma: no cover - frontend always present
        return []
    files = [
        p
        for ext in ("*.ts", "*.tsx")
        for p in FRONTEND_SRC.rglob(ext)
        if ".next" not in p.parts
        and "node_modules" not in p.parts
        and p.name not in _NON_CALLING_SOURCES
    ]
    return sorted(files)


def _normalise(raw: str) -> tuple[str, ...] | None:
    """Turn a raw frontend path string into comparable segments.

    Interpolated segments collapse to a wildcard. Query strings and fragments
    are dropped. Returns ``None`` for anything that is not an API path.
    """
    path = raw.split("?", 1)[0].split("#", 1)[0]
    if not path.startswith("/api/") and path != "/api":
        return None

    # A segment containing any interpolation is treated as a single wildcard.
    segments: list[str] = []
    for segment in path.strip("/").split("/"):
        if not segment:
            continue
        segments.append(WILDCARD if _INTERPOLATION.search(segment) else segment)
    return tuple(segments)


def _extract_from_source(text: str) -> set[str]:
    """Return every ``/api/...`` path literal in one source file."""
    found: set[str] = set()

    # Bases a file declares, so `${API_BASE}/validate` resolves to a real path.
    bases = dict(_BASE_CONST.findall(text))

    # A const only ever used as `${NAME}/...` is a prefix, not an endpoint —
    # its own value must not be reported as a path the console calls.
    prefix_only = {
        value for name, value in bases.items() if "${" + name + "}/" in text
    }

    for _quote, body in _STRING_LITERAL.findall(text):
        if "/api/" not in body and not body.startswith("/api"):
            continue

        if body.startswith("/api"):
            if body not in prefix_only:
                found.add(body)
            continue

        # `${API_BASE}/models` — substitute a known base and keep the remainder.
        match = re.match(r"^\$\{([A-Za-z_$][\w$]*)\}(/.*)?$", body)
        if match and match.group(1) in bases:
            found.add(bases[match.group(1)] + (match.group(2) or ""))

    return found


def collect_frontend_paths() -> dict[tuple[str, ...], set[str]]:
    """Map each normalised console path to the files that reference it."""
    paths: dict[tuple[str, ...], set[str]] = {}
    for source in _iter_source_files():
        text = source.read_text(encoding="utf-8", errors="ignore")
        for raw in _extract_from_source(text):
            if raw.split("?", 1)[0] in IGNORED_PATHS:
                continue
            segments = _normalise(raw)
            if segments is None:
                continue
            rel = source.relative_to(REPO_ROOT).as_posix()
            paths.setdefault(segments, set()).add(rel)
    return paths


# --------------------------------------------------------------------------
# The mounted route table
# --------------------------------------------------------------------------

_PATH_PARAM = re.compile(r"^\{.*\}$")


def collect_route_segments() -> list[tuple[str, ...]]:
    """Return every mounted API route as comparable segments."""
    routes: list[tuple[str, ...]] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if not path or not path.startswith("/api"):
            continue
        segments = tuple(
            WILDCARD if _PATH_PARAM.match(part) else part
            for part in path.strip("/").split("/")
            if part
        )
        routes.append(segments)
    return routes


def _matches(called: tuple[str, ...], route: tuple[str, ...]) -> bool:
    """True if a called path can be served by a route.

    A wildcard on either side matches any single segment: the console's
    ``/api/memory/${id}`` unifies with ``/api/memory/{memory_id}``, and its
    ``/api/transform/audio/${op}`` unifies with the literal ``/audio/tts``.
    """
    if len(called) != len(route):
        return False
    return all(
        c == WILDCARD or r == WILDCARD or c == r for c, r in zip(called, route)
    )


def _render(segments: tuple[str, ...]) -> str:
    return "/" + "/".join("{*}" if s == WILDCARD else s for s in segments)


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


def test_frontend_source_is_discoverable():
    """The extractor must actually be looking at something."""
    assert FRONTEND_SRC.is_dir(), f"frontend source not found at {FRONTEND_SRC}"
    assert API_CLIENT.is_file(), f"api client not found at {API_CLIENT}"
    assert len(_iter_source_files()) > 50


def test_extractor_finds_a_meaningful_number_of_paths():
    """Guard the guard: a broken regex must not silently pass everything."""
    paths = collect_frontend_paths()
    assert len(paths) > 100, (
        f"only {len(paths)} console API paths extracted — the extractor is "
        "probably broken, which would make this whole test vacuous"
    )


def test_api_client_paths_are_mounted():
    """Every /api path in frontend/src/lib/api.ts resolves to a mounted route."""
    routes = collect_route_segments()
    text = API_CLIENT.read_text(encoding="utf-8", errors="ignore")

    unresolved = []
    for raw in sorted(_extract_from_source(text)):
        segments = _normalise(raw)
        if segments is None or raw.split("?", 1)[0] in IGNORED_PATHS:
            continue
        if not any(_matches(segments, route) for route in routes):
            unresolved.append(_render(segments))

    assert not unresolved, (
        "frontend/src/lib/api.ts calls API paths that no mounted router "
        "serves:\n  " + "\n  ".join(unresolved)
    )


def test_all_console_paths_are_mounted():
    """Every /api path anywhere in the console resolves to a mounted route."""
    routes = collect_route_segments()

    unresolved: list[str] = []
    for segments, sources in sorted(collect_frontend_paths().items()):
        if not any(_matches(segments, route) for route in routes):
            callers = ", ".join(sorted(sources)[:3])
            unresolved.append(f"{_render(segments)}  (called from {callers})")

    assert not unresolved, (
        f"{len(unresolved)} console API path(s) resolve to no mounted route — "
        "either include the router in app/api/router.py or fix the frontend "
        "path:\n  " + "\n  ".join(unresolved)
    )


@pytest.mark.parametrize(
    "path",
    [
        # Regression anchors: each of these 404'd because its module was
        # defined but never included in app/api/router.py.
        "/api/settings/api-keys",
        "/api/settings/users",
        "/api/settings/users/invite",
        "/api/settings/billing",
        "/api/settings/audit-log",
        "/api/settings/storage",
        "/api/security/sessions",
        "/api/security/2fa/status",
        "/api/security/login-history",
        "/api/security/password",
        "/api/marketplace/byom/validate",
        "/api/marketplace/byom/register",
        "/api/marketplace/byom/models",
        "/api/marketplace/installed",
        "/api/annotate/auto-label",
        "/api/memory/summary",
        "/api/memory/timeline",
        "/api/memory/decay-all",
    ],
)
def test_previously_unmounted_paths_stay_mounted(path: str):
    """Named guard for the exact paths the unmounted-router bug took down."""
    routes = collect_route_segments()
    segments = _normalise(path)
    assert segments is not None
    assert any(_matches(segments, route) for route in routes), (
        f"{path} is not mounted — a router was dropped from app/api/router.py"
    )


def test_no_duplicate_route_paths_with_same_method():
    """Two handlers on one path+method means the second is dead code.

    This is how a stub with the wrong response shape silently shadows the real
    implementation the console needs.
    """
    seen: dict[tuple[str, str], int] = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not path.startswith("/api") or not methods:
            continue
        for method in methods - {"HEAD", "OPTIONS"}:
            seen[(method, path)] = seen.get((method, path), 0) + 1

    duplicates = [f"{m} {p} (x{n})" for (m, p), n in sorted(seen.items()) if n > 1]
    assert not duplicates, (
        "duplicate handlers registered for the same method+path; the "
        "later one is unreachable:\n  " + "\n  ".join(duplicates)
    )
