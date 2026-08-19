"""What the workspace filter covers, counted rather than asserted in prose.

``docs/auth.md`` makes claims about the reach of ``app/core/tenancy.py``: which
statement forms are scoped, which models are scopable, and how much raw SQL
touches tenant rows. Claims like that rot the moment someone adds a model or a
``text()`` call, and the previous version of that document was wrong about bulk
writes for as long as it existed.

So the numbers are computed here instead. Run this and the document is either
confirmed or contradicted:

    cd backend
    pytest tests/test_tenancy_coverage.py -v -s

The report is printed even when the tests pass, because the useful output is the
census, not the green tick.
"""

from __future__ import annotations

import ast
import pathlib

import pytest
from sqlalchemy import inspect as sa_inspect

import app.models  # noqa: F401 — registers every mapper
from app.core.tenancy import EXEMPT_TABLES, _parent_scope
from app.models.base import Base

APP_ROOT = pathlib.Path(__file__).resolve().parent.parent / "app"


# ---------------------------------------------------------------------------
# Model census
# ---------------------------------------------------------------------------


def _classify_models():
    """(own, via_parent, exempt, unscopable) by mapped class name."""
    own, via_parent, exempt, unscopable = [], [], [], []
    for mapper in Base.registry.mappers:
        table = mapper.local_table
        if table is None:
            continue
        name = mapper.class_.__name__
        if table.name in EXEMPT_TABLES:
            exempt.append(name)
        elif "workspace_id" in mapper.columns:
            own.append(name)
        elif _parent_scope(mapper) is not None:
            via_parent.append(name)
        else:
            unscopable.append(name)
    return sorted(own), sorted(via_parent), sorted(exempt), sorted(unscopable)


def test_report_model_coverage(capsys):
    """Print the census. Never fails — its job is to inform, not to gate."""
    own, via_parent, exempt, unscopable = _classify_models()
    total = len(own) + len(via_parent) + len(exempt) + len(unscopable)

    with capsys.disabled():
        print("\n\n--- workspace filter: model coverage ---")
        print(f"  scoped by own workspace_id : {len(own)}")
        print(f"  scoped through a parent    : {len(via_parent)}")
        print(f"  exempt (deliberately)      : {len(exempt)}  {exempt}")
        print(f"  not scopable               : {len(unscopable)}")
        if unscopable:
            print("    " + ", ".join(unscopable))
            print("    (rows hanging off a user, or genuinely global — see docs/auth.md)")
        print(f"  total mapped classes       : {total}")

    assert total > 0


def test_the_exemptions_have_not_drifted():
    """Widening this list makes a table readable from every tenant."""
    assert EXEMPT_TABLES == frozenset({"users", "workspaces", "audit_logs"})


# ---------------------------------------------------------------------------
# Raw SQL census
# ---------------------------------------------------------------------------

# `SELECT 1` and friends: liveness probes that touch no tenant row.
_PROBES = {"select 1", "select now()", "select version()"}


def _raw_sql_calls(root: pathlib.Path):
    """Every real SQLAlchemy text() call under *root*.

    Matches `text(...)` and `sa.text(...)` by AST rather than by grep. A textual
    search for "text(" reports 24 files here, almost all of them false: it also
    matches extract_text(, search_by_text(, write_text(, encode_text( and
    retrieve_context(. The real figure is four.
    """
    found = []
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_text = (isinstance(func, ast.Name) and func.id == "text") or (
                isinstance(func, ast.Attribute) and func.attr == "text"
            )
            if not is_text:
                continue
            if node.args and isinstance(node.args[0], ast.Constant):
                sql = " ".join(str(node.args[0].value).split())
            else:
                sql = "<non-literal — needs manual review>"
            found.append((path.relative_to(root.parent).as_posix(), node.lineno, sql))
    return found


def test_report_raw_sql(capsys):
    calls = _raw_sql_calls(APP_ROOT)
    with capsys.disabled():
        print("\n--- workspace filter: raw SQL under app/ ---")
        print(f"  real text() calls: {len(calls)} in {len({c[0] for c in calls})} files")
        for rel, line, sql in calls:
            print(f"    {rel}:{line}  {sql[:70]}")
    assert calls is not None


def test_no_raw_sql_touches_tenant_rows():
    """Raw SQL bypasses the ORM filter entirely, so it has to be checked by eye.

    This asserts the audited conclusion holds: every text() statement under
    app/ is a liveness probe. If this fails, someone added raw SQL — decide
    whether it crosses tenants, give it its own predicate if so, and update
    docs/auth.md.
    """
    offenders = [
        f"{rel}:{line}  {sql}"
        for rel, line, sql in _raw_sql_calls(APP_ROOT)
        if sql.strip().lower().rstrip(";") not in _PROBES
    ]
    assert not offenders, (
        "raw SQL that is not a liveness probe — audit it against docs/auth.md:\n  "
        + "\n  ".join(offenders)
    )


# ---------------------------------------------------------------------------
# Statement-form coverage
# ---------------------------------------------------------------------------


def test_report_statement_forms(capsys):
    """Which statement shapes the hook sees, as the source actually says.

    Read off the module rather than restated, so this cannot drift from it.
    """
    source = (APP_ROOT / "core" / "tenancy.py").read_text(encoding="utf-8")
    covered = {
        "SELECT": "execute_state.is_select" in source,
        "UPDATE": "execute_state.is_update" in source,
        "DELETE": "execute_state.is_delete" in source,
        "INSERT": "execute_state.is_insert" in source,
    }
    with capsys.disabled():
        print("\n--- workspace filter: statement forms ---")
        for form, is_covered in covered.items():
            note = ""
            if form == "INSERT":
                note = "  (deliberate: no existing row to confine)"
            print(f"  {form:<7} {'covered' if is_covered else 'not covered'}{note}")
        print("  Core update(Model.__table__) and raw text() are NOT covered.")
        print("  Both verified in test_session_scoping.py / docs/auth.md.\n")

    assert covered["SELECT"], "the read filter has gone missing"
    assert covered["UPDATE"] and covered["DELETE"], (
        "the write filter has gone missing — bulk statements cross tenants again"
    )
