"""Guard: every API path the console calls must resolve against the route table.

The bug this exists to prevent: a route module defines endpoints, the frontend
calls them, but ``app/api/router.py`` never includes the router — so the paths
404 at runtime while every unit test still passes. Ten modules shipped that way.

The test walks ``frontend/src``, extracts every ``/api/...`` string literal it
can see, and asserts each one unifies with a mounted FastAPI route.

"Can see" is the load-bearing phrase, and it was wrong for a long time. The
extractor only recognised a path written as a bare ``"/api/..."`` literal or as
``${SOME_BASE}/rest`` where the base itself held a path. The console mostly
calls the API as ``fetch(`${API}/api/thing`)`` with an *origin* in ``API`` -
neither form - so 38 of ~152 paths were invisible, including one that 404'd on
every page load. ``test_the_extractor_sees_each_way_the_console_calls_the_api``
below pins each calling convention so the net cannot quietly narrow again.
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

# Any quoted string. Only a template literal may span lines - '' and ""
# strings cannot in JavaScript, and letting them do so here made the pattern
# swallow whole blocks of code: a literal would open at a quote, run past its
# closing quote through several lines, and surface as a "path" such as
#   /api/alerts/incidents", {
# Each of those was a false unmounted route sitting on top of the real ones,
# which is the fastest way to make a guard's output ignorable.
_SQ = r"'((?:\\.|[^'\n])*?)'"
_DQ = r'"((?:\\.|[^"\n])*?)"'
_BQ = r"`((?:\\.|[^`])*?)`"
_STRING_LITERAL = re.compile(f"(?:{_SQ}|{_DQ}|{_BQ})", re.DOTALL)

# `const API_BASE = '/api/marketplace/byom';` — components build paths off these.
#
# The origin may be interpolated: ``const API = `${API_BASE_URL}/api/federated` ``
# is the same declaration with a host in front, and it is the shape most of the
# console uses. Without the optional prefix here that const is not recognised as
# a base, and the "read from the first /api/" rule below then reports
# `/api/federated` as an endpoint the console calls — which it does not; it calls
# `${API}/federations`.
_BASE_CONST = re.compile(
    r"""(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*['"`]"""
    r"""(?:\$\{[^}]*\})?(/api/[^'"`$]*)['"`]"""
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
        and "__tests__" not in p.parts
        and not p.name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
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

    # Reading from the first "/api/" of any literal is what let this scanner
    # finally see `${API}/api/thing`. It also means prose gets read: a comment
    # explaining "/api/… was a page asking for someone else" is a string
    # literal too, and a multi-line template can span into ordinary code.
    #
    # A URL path has no spaces, quotes, brackets or ellipses. Rejecting those
    # keeps the widening without the noise - and rejecting is safe here because
    # a real path never contains them, so nothing genuine is being hidden.
    if any(ch in path for ch in ' \t\n"\'`()[]{}<>,;') and "${" not in path:
        return None
    if "\u2026" in path or "..." in path:
        return None

    # A segment containing any interpolation is treated as a single wildcard.
    segments: list[str] = []
    for segment in path.strip("/").split("/"):
        if not segment:
            continue
        segments.append(WILDCARD if _INTERPOLATION.search(segment) else segment)
    return tuple(segments)


# How the console names an HTTP method at a call site.
_VERB_CALL = re.compile(
    r"\b(?:api|apiClient|axios|http|client)\s*\.\s*(get|post|put|patch|delete)\s*\(\s*$",
    re.I,
)
_FETCH_CALL = re.compile(r"\bfetch\s*\(\s*$")
_OPEN_CALL = re.compile(r"\bwindow\.open\s*\(\s*$")
_HREF = re.compile(r"\bhref\s*=\s*\{?\s*$")
_METHOD_OPT = re.compile(r"""method\s*:\s*['"](\w+)['"]""")

# The method could not be determined from the call site. Such a call is still
# checked for path existence; it is skipped by the method check rather than
# guessed at, because a wrong guess here fails the build for working code.
UNKNOWN_METHOD = "ANY"


def _call_span(text: str, open_paren: int) -> str:
    """The text of the call whose bracket opens at *open_paren*."""
    depth = 0
    for i in range(open_paren, min(len(text), open_paren + 1500)):
        char = text[i]
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
            if depth == 0:
                return text[open_paren : i + 1]
    return text[open_paren : open_paren + 1500]


def _method_at(text: str, index: int) -> str:
    """The HTTP method of the call whose first argument starts at *index*.

    `api.delete("/x")` says so in the callee. `fetch(url, {method: "DELETE"})`
    says so in its options, and a `fetch` without options is a GET - which is
    what the spec says and what every one of these call sites means.
    """
    prefix = text[max(0, index - 140) : index]

    verb = _VERB_CALL.search(prefix)
    if verb:
        return verb.group(1).upper()

    # A link or a new tab is a GET by construction.
    if _OPEN_CALL.search(prefix) or _HREF.search(prefix):
        return "GET"

    if _FETCH_CALL.search(prefix):
        open_paren = max(0, index - 140) + prefix.rfind("(")
        found = _METHOD_OPT.search(_call_span(text, open_paren))
        return found.group(1).upper() if found else "GET"

    return UNKNOWN_METHOD


def _extract_calls_from_source(text: str) -> set[tuple[str, str]]:
    """Every ``(method, /api/...)`` call one source file makes."""
    found: set[tuple[str, str]] = set()

    # Bases a file declares, so `${API_BASE}/validate` resolves to a real path.
    bases = dict(_BASE_CONST.findall(text))

    # A const only ever used as `${NAME}/...` is a prefix, not an endpoint —
    # its own value must not be reported as a path the console calls.
    prefix_only = {
        value for name, value in bases.items() if "${" + name + "}/" in text
    }

    for match in _STRING_LITERAL.finditer(text):
        body = next((g for g in match.groups() if g), "")
        if not body:
            continue
        if "/api/" not in body and not body.startswith("/api") and not body.startswith("${"):
            continue

        path: str | None = None

        if body.startswith("/api"):
            if body not in prefix_only:
                path = body

        else:
            # `${API_BASE}/models` — substitute a known base, keep the remainder.
            sub = re.match(r"^\$\{([A-Za-z_$][\w$]*)\}(/.*)?$", body)
            if sub and sub.group(1) in bases:
                path = bases[sub.group(1)] + (sub.group(2) or "")
            else:
                # `${API}/api/observability/dashboard` — an absolute URL built
                # from a host constant. This is the single largest way the
                # console calls the API and this scanner could not see any of
                # it: the literal does not start with "/api", and `API` holds an
                # origin rather than a path so it is not in `bases` either.
                #
                # That is not hypothetical. /api/observability/latency-history
                # was called on every load of the observability page and mounted
                # nowhere, 404ing for as long as the page existed, while this
                # test - written to catch exactly that - passed.
                #
                # Anything from the first "/api/" onwards is the path, whatever
                # precedes it. `_normalise` rejects the prose this also picks up.
                index = body.find("/api/")
                if index > 0 and body[index:] not in prefix_only:
                    path = body[index:]

        if path:
            found.add((_method_at(text, match.start()), path))

    return found


def _extract_from_source(text: str) -> set[str]:
    """Every ``/api/...`` path literal in one source file, method discarded.

    Built on the same parser as the method-aware one, so the two cannot drift.
    """
    return {path for _method, path in _extract_calls_from_source(text)}


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


def collect_frontend_calls() -> dict[tuple[str, tuple[str, ...]], set[str]]:
    """Map each ``(method, normalised path)`` the console calls to its callers."""
    calls: dict[tuple[str, tuple[str, ...]], set[str]] = {}
    for source in _iter_source_files():
        text = source.read_text(encoding="utf-8", errors="ignore")
        for method, raw in _extract_calls_from_source(text):
            if raw.split("?", 1)[0] in IGNORED_PATHS:
                continue
            segments = _normalise(raw)
            if segments is None:
                continue
            rel = source.relative_to(REPO_ROOT).as_posix()
            calls.setdefault((method, segments), set()).add(rel)
    return calls


# --------------------------------------------------------------------------
# The mounted route table
# --------------------------------------------------------------------------

_PATH_PARAM = re.compile(r"^\{.*\}$")


def collect_route_methods() -> dict[tuple[str, ...], set[str]]:
    """Every mounted API route as segments, with the methods it serves."""
    routes: dict[tuple[str, ...], set[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        if not path or not path.startswith("/api"):
            continue
        segments = tuple(
            WILDCARD if _PATH_PARAM.match(part) else part
            for part in path.strip("/").split("/")
            if part
        )
        methods = set(getattr(route, "methods", set()) or set())
        routes.setdefault(segments, set()).update(methods)
    return routes


def collect_route_segments() -> list[tuple[str, ...]]:
    """Return every mounted API route as comparable segments."""
    return list(collect_route_methods())


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


CALLING_CONVENTIONS = [
    # (source snippet, the path it must yield)
    ('api.get("/api/alerts")', "/api/alerts"),
    ("api.get('/api/alerts')", "/api/alerts"),
    ("api.get(`/api/alerts/${id}`)", "/api/alerts/\x00"),
    # The one this scanner could not see. An origin in `API`, the path after it.
    ("fetch(`${API}/api/observability/dashboard`)", "/api/observability/dashboard"),
    ("fetch(`${API_BASE}/api/edge/devices/${id}/logs`)", "/api/edge/devices/\x00/logs"),
    # A query string is not part of the path.
    ("fetch(`${API}/api/observability/sla?tier=standard`)", "/api/observability/sla"),
    # A declared base that itself holds a path.
    ('const B = "/api/marketplace/byom";\nfetch(`${B}/validate`)',
     "/api/marketplace/byom/validate"),
    # The same with the origin interpolated in front - the console's most common
    # shape, and the one that broke this test the first time it was widened.
    ('const API = `${API_BASE_URL}/api/federated`;\nfetch(`${API}/federations`)',
     "/api/federated/federations"),
]


@pytest.mark.parametrize("snippet,expected", CALLING_CONVENTIONS,
                         ids=[c[1] for c in CALLING_CONVENTIONS])
def test_the_extractor_sees_each_way_the_console_calls_the_api(snippet, expected):
    """Each calling style, pinned.

    This test exists because the net narrowed silently. The extractor handled a
    bare "/api/..." literal and `${BASE}/rest`, and the console overwhelmingly
    writes `fetch(`${API}/api/...`)` - which matched neither. 38 of ~152 paths
    were invisible, one of them a route that 404'd on every load of the
    observability page while this file passed.

    A guard that covers three quarters of its subject reads exactly like one
    that covers all of it. Adding a convention here is how the difference stays
    visible.
    """
    found = _extract_from_source(snippet)
    normalised = {_normalise(raw) for raw in found}
    normalised.discard(None)

    expected_segments = tuple(
        seg for seg in expected.strip("/").split("/") if seg
    )
    assert expected_segments in normalised, (
        f"the extractor did not see {expected!r} in {snippet!r} - "
        f"it found {sorted(found)}"
    )


def test_a_base_const_is_not_itself_reported_as_an_endpoint():
    """``const API = `${HOST}/api/federated``` declares a prefix, not a route.

    The console calls `${API}/federations`. Reporting `/api/federated` as an
    unmounted path fails the suite for a route nothing requests — which is
    exactly what happened the first time this extractor was widened, on the very
    change that widened it.
    """
    source = (
        "const API = `${API_BASE_URL}/api/federated`;\n"
        "fetch(`${API}/federations`);\n"
    )
    found = _extract_from_source(source)

    assert "/api/federated/federations" in found
    assert "/api/federated" not in found, (
        "the base const was reported as an endpoint in its own right"
    )


def test_a_string_literal_does_not_run_past_its_own_quote():
    """A quoted string cannot span lines, and neither may the pattern.

    When it could, one literal swallowed the code after it and produced paths
    like `/api/alerts/incidents", {` - false unmounted routes stacked on top of
    the real ones, which is how a guard's output becomes something people skip.
    """
    source = 'api.post("/api/alerts/incidents", {\n  body: JSON.stringify(x),\n});'
    found = _extract_from_source(source)

    assert found == {"/api/alerts/incidents"}, (
        f"expected exactly the one path, got {sorted(found)}"
    )


def test_the_extractor_still_sees_most_of_the_console():
    """A floor, so a future narrowing shows up as a failure rather than silence.

    At the time of writing it sees 207 distinct paths. The floor is deliberately
    below that - this guards against collapse, not against ordinary churn.
    """
    count = len(collect_frontend_paths())
    assert count >= 180, (
        f"the extractor now sees only {count} API paths, down from 207. "
        "Something about how the console writes paths has changed and the "
        "scanner no longer recognises it - add the new convention to "
        "CALLING_CONVENTIONS above."
    )


METHOD_CONVENTIONS = [
    # (source snippet, expected method for the path it contains)
    ('api.get("/api/alerts")', "GET"),
    ('api.delete(`/api/assets/${id}`)', "DELETE"),
    ('api.patch("/api/alerts/x", body)', "PATCH"),
    # A bare fetch is a GET, which is what the spec says and what these mean.
    ('fetch(`${API}/api/edge/devices`)', "GET"),
    # ...and an options object overrides it.
    ('fetch(`${API}/api/edge/devices/${id}`, { method: "DELETE" })', "DELETE"),
    ("fetch('/api/reviewops/auto-assign', {\n  method: 'POST',\n})", "POST"),
    # A link and a new tab are GETs by construction.
    ('window.open(`${API}/api/edge/devices/${id}/logs`, "_blank")', "GET"),
    ('<a href={`${API}/api/edge/exports/${id}/download`}>', "GET"),
]


@pytest.mark.parametrize("snippet,expected", METHOD_CONVENTIONS,
                         ids=[f"{m}-{i}" for i, (_, m) in enumerate(METHOD_CONVENTIONS)])
def test_the_extractor_reads_the_method_from_the_call_site(snippet, expected):
    """Each way the console names a method, pinned.

    Detection that silently degrades to ANY would make the method check below
    pass by examining nothing, which is the failure mode this whole file keeps
    running into.
    """
    calls = _extract_calls_from_source(snippet)
    assert calls, f"no API call found in {snippet!r}"
    methods = {method for method, _ in calls}
    assert expected in methods, f"expected {expected}, read {sorted(methods)}"


def test_most_call_sites_yield_a_method():
    """A floor on detection, so a rewrite that blinds it shows up here.

    Some calls genuinely cannot be read - a URL built into a variable several
    lines earlier, then passed to fetch. Those fall back to ANY and are covered
    by the path check rather than the method check. At the time of writing 255
    of 299 calls resolve to a real method.
    """
    calls = collect_frontend_calls()
    known = [c for c in calls if c[0] != UNKNOWN_METHOD]

    assert len(calls) >= 200, f"only {len(calls)} calls found at all"
    assert len(known) / len(calls) >= 0.75, (
        f"only {len(known)} of {len(calls)} calls yielded a method. Detection "
        "has regressed - see METHOD_CONVENTIONS above."
    )


def test_every_console_call_uses_a_method_the_route_serves():
    """A path that exists is not the same as a call that works.

    `ExportHistory`'s delete button sent DELETE /api/edge/exports/{id} to a path
    that only served GET. FastAPI answered 405, the component reported "Delete
    failed", the row stayed - and this file passed, because it compared paths
    and ignored methods, so the DELETE resolved against the GET sitting at the
    same path. Six such calls were mounted-by-coincidence when this check was
    added.

    Calls whose method could not be read from the source are skipped here; they
    are still checked for path existence by the test above.
    """
    routes = collect_route_methods()

    mismatched: list[str] = []
    for (method, segments), sources in sorted(collect_frontend_calls().items()):
        if method == UNKNOWN_METHOD:
            continue

        served: set[str] = set()
        for route_segments, route_methods in routes.items():
            if _matches(segments, route_segments):
                served |= route_methods
        if not served:
            continue  # no such path at all - the other test says so, better

        if method not in served:
            callers = ", ".join(sorted(sources)[:2])
            offered = ", ".join(sorted(served - {"HEAD", "OPTIONS"})) or "nothing"
            mismatched.append(
                f"{method} {_render(segments)} — path serves {offered}  "
                f"(called from {callers})"
            )

    assert not mismatched, (
        f"{len(mismatched)} console call(s) use a method their path does not "
        "serve. Each is a 405 at runtime, and each looks mounted to a check "
        "that only compares paths:\n  " + "\n  ".join(mismatched)
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
