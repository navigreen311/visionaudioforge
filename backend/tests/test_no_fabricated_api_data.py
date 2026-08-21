"""No endpoint answers with records it made up.

`GET /api/experiments/{id}` used to answer 200 for *any* UUID. Its handler
wrapped the database call in `except Exception` and fell back to a generator:

    train_loss = 2.5 * math.exp(-3.0 * progress) + 0.05
    accuracy   = 1.0 - math.exp(-3.0 * progress)

Twenty epochs of that, named after the first eight characters of whatever id you
asked for, marked "completed", and attributed to workspace 00000000-…-0000. The
Train page drew it as a chart. It looked like a successful training run because
it was shaped like one.

The list endpoint did the same with three fixture experiments, and both catches
were bare `except Exception`, so a real database failure was indistinguishable
from an empty result and answered 200.

Two things are checked here. The behaviour - an unknown experiment is a 404 -
and the shape that produced it, because the behaviour test only covers the
endpoint someone thought to write a test for.
"""

from __future__ import annotations

import ast
import pathlib
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token

ROUTES = pathlib.Path(__file__).resolve().parent.parent / "app" / "api" / "routes"

pytestmark_anyio = pytest.mark.anyio


# ---------------------------------------------------------------------------
# The shape
# ---------------------------------------------------------------------------

#: Module-level record lists a route module may legitimately return.
#:
#: A capability list is not fabricated data - it describes what this build can
#: do, and no database row could supply it. Everything else needs a reason.
ALLOWED: dict[str, str] = {
    "SUPPORTED_FORMATS": (
        "edge.py: the export formats this build can actually produce (ONNX, "
        "TFLite, ...). A capability, not a record - no database row could "
        "supply it."
    ),
    "SEED_PLUGINS": (
        "marketplace.py: written into installed_plugins the first time a "
        "workspace is viewed, not returned from memory. The rows a caller then "
        "reads are real rows. Worth revisiting - a new workspace does start "
        "with three plugins nobody installed - but it is a seeding decision, "
        "not a handler answering from a literal."
    ),
    "_CATALOGUE": (
        "marketplace_stubs.py: KNOWN GAP. A five-item plugin catalogue that "
        "list/get/install/uninstall all read, with install and uninstall "
        "mutating the module list - so it is shared between tenants and lost "
        "on restart. The real marketplace router mounts ahead of it and only "
        "the paths it does not define fall through here. Replacing it needs a "
        "plugin registry, which does not exist yet."
    ),
}


def _module_record_lists(tree: ast.Module) -> dict[str, int]:
    """Module-level constants whose value is a list of dicts."""
    found: dict[str, int] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            value = node.value
            if isinstance(value, ast.List) and value.elts and isinstance(value.elts[0], ast.Dict):
                found[target.id] = len(value.elts)
    return found


def _handler_reads(tree: ast.Module, names: set[str]) -> set[tuple[str, str]]:
    """(function, constant) for every read of *names* inside a function body."""
    reads: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in names and isinstance(sub.ctx, ast.Load):
                reads.add((node.name, sub.id))
    return reads


def test_no_handler_answers_from_records_defined_in_its_own_source():
    """A handler's answer comes from the platform, not from a literal above it.

    This is the rule the console's no-fabricated-panel-data test applies, on the
    other side of the wire.

    It looks for any *read* of the constant inside a function, not just
    ``return CONST``. The first version of this test checked only the return and
    passed against the very code it was written for: the list handler wrote
    ``items = _MOCK_EXPERIMENTS[skip : skip + limit]`` and the detail handler
    wrote ``for mock in _MOCK_EXPERIMENTS`` - neither is a return, both are the
    defect.

    What it still cannot see: a handler that fabricates without a constant to
    read, as ``_mock_epochs()`` did when it built twenty epochs from an
    exponential. The behaviour tests below cover that for experiments; there is
    no general static form of it.
    """
    offenders: list[str] = []

    for path in sorted(ROUTES.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        constants = _module_record_lists(tree)
        if not constants:
            continue

        for function, name in sorted(_handler_reads(tree, set(constants))):
            if name in ALLOWED:
                continue
            offenders.append(
                f"{name} ({constants[name]} records) read by {path.name}:{function}"
            )

    assert not offenders, (
        "These handlers answer from records defined in their own source. "
        "Whatever they return is invented and indistinguishable from real data "
        "to the caller. Read it from the database, or add it to ALLOWED with a "
        "reason:\n  " + "\n  ".join(sorted(set(offenders)))
    )


def test_no_handler_falls_back_to_fabricated_data_on_error():
    """`except Exception` must not turn a failure into a plausible answer.

    Both experiment handlers did exactly that, so a database outage and an empty
    workspace were the same 200 - and the outage was the one that looked fine.
    """
    offenders: list[str] = []

    for path in sorted(ROUTES.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        constants = _module_record_lists(tree)
        if not constants:
            continue

        for handler in ast.walk(tree):
            if not isinstance(handler, ast.ExceptHandler):
                continue
            caught = handler.type
            is_broad = caught is None or (
                isinstance(caught, ast.Name)
                and caught.id in {"Exception", "BaseException"}
            )
            if not is_broad:
                continue
            for sub in ast.walk(handler):
                if (
                    isinstance(sub, ast.Name)
                    and sub.id in constants
                    and isinstance(sub.ctx, ast.Load)
                    and sub.id not in ALLOWED
                ):
                    offenders.append(f"{path.name}: except Exception reads {sub.id}")

    assert not offenders, (
        "A catch-all that answers with invented records makes a real failure "
        "look like an empty result:\n  " + "\n  ".join(sorted(set(offenders)))
    )


# ---------------------------------------------------------------------------
# The behaviour
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    transport = ASGITransport(app=__import__("app.main", fromlist=["app"]).app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _auth(workspace_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        {"sub": str(uuid.uuid4()), "workspace_id": str(workspace_id)}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
@pytest.mark.auth_enforced
async def test_an_experiment_that_does_not_exist_is_a_404(client):
    """The regression, stated plainly.

    Before: 200, with a name derived from the id, status "completed", twenty
    epochs of exponential-decay metrics, and someone else's workspace on it.
    """
    workspace_id = uuid.uuid4()
    unknown = uuid.uuid4()

    response = await client.get(
        f"/api/experiments/{unknown}", headers=_auth(workspace_id)
    )

    assert response.status_code == 404, (
        f"expected 404 for an id that has never existed, got "
        f"{response.status_code}: {response.text[:300]}"
    )


@pytest.mark.anyio
@pytest.mark.auth_enforced
async def test_a_workspace_with_no_experiments_lists_none(client):
    """An empty workspace is empty, not three fixtures from another tenant."""
    workspace_id = uuid.uuid4()

    response = await client.get("/api/experiments", headers=_auth(workspace_id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"] == [], f"a fresh workspace listed experiments: {body['items']}"
    assert body["total"] == 0
