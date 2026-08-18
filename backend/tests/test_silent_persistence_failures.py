"""A net for database writes that fail without anyone finding out.

Three such bugs shipped and survived every existing test. They were not the
same bug, and no single check catches all three — which is why this file is
explicit about what each half does and does not cover.

  1. AuditMiddleware built AuditLog with `resource_type=`, not a column. Every
     request raised TypeError inside the write. It was *not* swallowed: it
     logged "audit log write failed" with a traceback, on every single request,
     for the life of the project. Nobody read it, and no test asserted a row
     was ever written.

  2. audit_logs.workspace_id was NOT NULL, so unattributable events — every
     failed login — were deliberately skipped with an early return.

  3. CopilotService.chat() wrapped conversation_manager.store_message, which
     commits, in a bare `except Exception: pass`.

PART ONE (static) catches shape 3: a silent, broad handler guarding a call that
reaches a database write. It works on the *call graph*, not on grep, because
the write is never in the handler's line of sight — store_message is one level
down, and a textual search for a commit next to a silent handler finds nothing.

PART TWO (runtime) patches the session factory to raise, and asserts the
failure becomes observable on the paths that matter most.

NEITHER CATCHES SHAPE 1. A write that is correctly reported and still never
succeeds can only be caught by asserting the happy path — that a row reaches
the session, built against the real model. tests/test_audit_middleware.py does
that for the audit trail. This file is not a substitute for it.

Run:

    cd backend
    pytest tests/test_silent_persistence_failures.py -v
"""

from __future__ import annotations

import ast
import logging
import pathlib
import uuid
from collections import defaultdict

import pytest

APP_ROOT = pathlib.Path(__file__).resolve().parent.parent / "app"

# Methods that write. `execute` is deliberately absent: SQLAlchemy uses it for
# reads far more often than writes, and including it flags every select()
# wrapped in a fallback.
WRITE_METHODS = frozenset({"commit", "add", "add_all", "flush", "merge"})

# Names too ambiguous to resolve by identifier alone. Matching is by bare
# function name — a deliberate over-approximation — so a name shared between a
# persisting helper and an unrelated method produces false positives.
AMBIGUOUS_NAMES = frozenset({"execute", "run", "process", "handle", "save"})

# Handlers allowed to be silent around a persisting call, with the reason.
# Empty on purpose: every case found so far was a bug. Add an entry only with a
# justification that survives being read aloud.
ALLOWED_SILENT: dict[tuple[str, str], str] = {}


# ---------------------------------------------------------------------------
# Call-graph construction
# ---------------------------------------------------------------------------


def _called_names(node: ast.AST) -> set[str]:
    """Every function/method name invoked anywhere under *node*."""
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
            elif isinstance(func, ast.Name):
                names.add(func.id)
    return names


def _parse_tree(root: pathlib.Path) -> dict[pathlib.Path, ast.Module]:
    trees: dict[pathlib.Path, ast.Module] = {}
    for path in sorted(root.rglob("*.py")):
        try:
            trees[path] = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - a broken file is its own failure
            continue
    return trees


def _persisting_functions(trees) -> set[str]:
    """Names of functions that reach a database write, transitively.

    A function persists if it writes directly, or calls something that does,
    iterated to a fixed point. That iteration is the whole point: the copilot
    bug sat two hops from the commit.
    """
    calls: dict[str, set[str]] = defaultdict(set)
    persisting: set[str] = set()

    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names = _called_names(node)
                calls[node.name] |= names
                if names & WRITE_METHODS:
                    persisting.add(node.name)

    changed = True
    while changed:
        changed = False
        for name, called in calls.items():
            if name not in persisting and (called & persisting):
                persisting.add(name)
                changed = True

    return (persisting | WRITE_METHODS) - AMBIGUOUS_NAMES


def _silent_persistence_handlers(trees, persisting, root: pathlib.Path):
    """(relpath, line, guarded calls) for every silent handler around a write."""
    found = []
    for path, tree in trees.items():
        rel = path.relative_to(root.parent).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            guarded: set[str] = set()
            for stmt in node.body:
                guarded |= _called_names(stmt)
            hits = guarded & persisting
            if not hits:
                continue
            for handler in node.handlers:
                is_silent = all(isinstance(s, ast.Pass) for s in handler.body)
                is_broad = handler.type is None or (
                    isinstance(handler.type, ast.Name)
                    and handler.type.id == "Exception"
                )
                if is_silent and is_broad:
                    found.append((rel, handler.lineno, sorted(hits)))
    return found


# ---------------------------------------------------------------------------
# Part one — the static net
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app_trees():
    return _parse_tree(APP_ROOT)


def test_call_graph_is_non_trivial(app_trees):
    """Guard the guard. An empty call graph makes the sweep below vacuous."""
    persisting = _persisting_functions(app_trees)
    assert len(app_trees) > 100, f"only parsed {len(app_trees)} modules"
    assert len(persisting) > 50, (
        f"only {len(persisting)} persisting functions found — the call graph "
        "collapsed and the sweep below proves nothing"
    )


def test_no_database_write_fails_silently(app_trees):
    """No broad, silent handler may guard a call that reaches a write.

    If this fails, that handler is discarding a database failure with no trace.
    Log it (`except Exception as exc: logger.warning(...)`) or let it
    propagate. Add to ALLOWED_SILENT only with a reason you would defend.
    """
    persisting = _persisting_functions(app_trees)
    offenders = [
        f"{rel}:{line} guards {hits}"
        for rel, line, hits in _silent_persistence_handlers(
            app_trees, persisting, APP_ROOT
        )
        if (rel, ",".join(hits)) not in ALLOWED_SILENT
    ]
    assert not offenders, (
        "database writes discarded without a trace:\n  " + "\n  ".join(offenders)
    )


def test_the_net_has_teeth(tmp_path):
    """Prove the analysis flags the shape it claims to.

    Written against a synthetic tree rather than the real one, so it keeps
    working once the real offenders are gone. A net that passes only because
    there is nothing left to catch is itself untested.
    """
    root = tmp_path / "app"
    (root / "svc").mkdir(parents=True)
    (root / "svc" / "writer.py").write_text(
        "async def store_thing(db, obj):\n"
        "    db.add(obj)\n"
        "    await db.commit()\n",
        encoding="utf-8",
    )
    # The offender: two hops from the commit, invisible to a textual search.
    (root / "svc" / "caller.py").write_text(
        "async def handle_it(db, obj):\n"
        "    try:\n"
        "        await store_thing(db, obj)\n"
        "    except Exception:\n"
        "        pass\n",
        encoding="utf-8",
    )

    trees = _parse_tree(root)
    persisting = _persisting_functions(trees)

    assert "store_thing" in persisting, "fixed point failed to propagate"
    found = _silent_persistence_handlers(trees, persisting, root)
    assert any("caller.py" in rel for rel, _, _ in found), (
        "the analysis missed a silent handler two hops from a commit"
    )


def test_reads_wrapped_in_a_fallback_are_not_flagged(tmp_path):
    """A swallowed SELECT is a degradation, not a lost write.

    search_service.py enriches results from the database and falls back to
    placeholder metadata when that fails. Flagging it would make the net noise,
    and a noisy net gets an allowlist entry instead of a fix.
    """
    root = tmp_path / "app"
    (root / "svc").mkdir(parents=True)
    (root / "svc" / "reader.py").write_text(
        "async def enrich(db, stmt, result):\n"
        "    try:\n"
        "        row = (await db.execute(stmt)).scalar_one_or_none()\n"
        "        if row:\n"
        "            result['name'] = row.name\n"
        "    except Exception:\n"
        "        pass\n",
        encoding="utf-8",
    )

    trees = _parse_tree(root)
    found = _silent_persistence_handlers(trees, _persisting_functions(trees), root)
    assert found == [], f"a read-only fallback was flagged: {found}"


# ---------------------------------------------------------------------------
# Part two — the runtime net
# ---------------------------------------------------------------------------


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _drain(audit_module) -> None:
    """Let the fire-and-forget audit tasks finish."""
    import asyncio

    for _ in range(50):
        if not audit_module._pending:
            return
        await asyncio.sleep(0.01)


@pytest.mark.anyio
async def test_audit_write_failure_is_reported(monkeypatch, caplog):
    """The audit trail must say so when it cannot record.

    Its write is fire-and-forget, so this log line is the only thing standing
    between a dead audit trail and total silence. Bug 1 lived here: the line
    fired on every request and nobody was watching.
    """
    from app.middleware import audit as audit_module

    def _explode(*args, **kwargs):
        raise RuntimeError("simulated database outage")

    monkeypatch.setattr("app.database.async_session_factory", _explode, raising=False)
    monkeypatch.setattr(audit_module.settings, "AUDIT_ENABLED", True)

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def send(message):
        return None

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/assets",
        "headers": [],
        "client": ("10.0.0.7", 1234),
        "state": {"workspace_id": uuid.uuid4(), "user_id": uuid.uuid4()},
    }

    with caplog.at_level(logging.WARNING):
        await audit_module.AuditMiddleware(app)(scope, lambda: None, send)
        await _drain(audit_module)

    assert any("audit" in r.getMessage().lower() for r in caplog.records), (
        "the audit trail failed to write and said nothing"
    )


@pytest.mark.anyio
async def test_copilot_write_failure_is_reported(monkeypatch, caplog):
    """Losing conversation history must not be silent.

    Bug 3 lived here, on the mock-mode branch — which is what runs whenever
    ANTHROPIC_API_KEY is unset, i.e. by default.
    """
    from app.services.agents import copilot as copilot_module

    class BrokenManager:
        async def get_history(self, *a, **k):
            return []

        async def get_context_window(self, *a, **k):
            return []

        async def store_message(self, *a, **k):
            raise RuntimeError("simulated database outage")

    monkeypatch.setattr(copilot_module, "conversation_manager", BrokenManager())

    service = copilot_module.CopilotService()
    assert not service.is_available, "expected mock mode with no API key"

    with caplog.at_level(logging.WARNING):
        chunks = [
            chunk
            async for chunk in service.chat(
                message="hello",
                workspace_id=str(uuid.uuid4()),
                agent_id="agent-1",
                db=object(),
            )
        ]

    assert chunks, "the stream should still complete — degrade, do not fail"
    assert any(
        "store assistant message" in r.getMessage().lower() for r in caplog.records
    ), "the assistant message was lost with no trace"
