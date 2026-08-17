# Backend persistence

How durable state works in the backend: which subsystems own tables, how to run
migrations, and how to run the tests that need a database.

## Why this exists

Around forty subsystems kept their state in module-level dicts, typically
marked *"In-memory store for V1 (production would use DB table)"*. Two
consequences followed from that, and both are user-visible:

- **State was lost on restart.** A device registered with the fleet, a webhook
  wired to Slack, an evidence chain of custody — all gone on the next deploy,
  with nothing in the response to distinguish "no records" from "we forgot".
- **State was not shared between workers.** A session opened on one process was
  invisible to a request that landed on another, so the app could not run more
  than one worker.

## Storage choices

| State | Where | Why |
| --- | --- | --- |
| Registrations, evidence, configuration, history | Postgres | Must outlive a restart and be queryable |
| Capture sessions | Redis, 12h TTL | Ephemeral — a session that outlives a restart has nothing to resume — but must be shared across workers |
| Loaded model objects (`_MODEL_CACHE`) | Process memory | Live handles, per-process by nature, cheap to rebuild |
| Install-progress jobs | Process memory | An install job that outlives a restart has nothing to resume |

## Migrations

```bash
cd backend
alembic upgrade head        # apply
alembic downgrade -1        # roll back one
alembic current             # what is applied
```

| Revision | Contents |
| --- | --- |
| `001` | Initial schema (16 tables) |
| `002` | Edge fleet: devices, telemetry, OTA rollouts, remote config, packages, sync plans |
| `003` | Tables that had models and live code but no migration at all |
| `004` | Evidence integrity: bundles, chain of custody, integrity baselines |
| `005` | Plugins, marketplace installs, reviews, custom nodes, BYOM models and adapters |
| `006` | Mobile push and sync, webhooks and deliveries, event-bus log |

### About revision 003

`alembic/env.py` imported a hand-listed subset of model modules, so
`Base.metadata` was incomplete and `--autogenerate` never saw the rest.
Thirteen tables with models and working code had no migration anywhere —
`command_streams`, `incidents`, `operator_shifts`, `api_keys`, `annotations`,
the knowledge graph, semantic memories and ReviewOps. They existed only where
something had called `create_all`. `env.py` now imports the package.

`--autogenerate` also reports column- and type-level drift between `001` and
the current models (`agents`, `agent_memories`, `experiments`,
`experiment_epochs`, `model_registry`). Reconciling it means dropping and
retyping columns on populated tables, so it is deliberately **not** in `003`.
That reconciliation is still outstanding.

## Workspace scoping

Queries take `workspace_id` as an argument and filter on it. They do not read
an authenticated workspace from the session — that dependency lands separately
(see `docs/auth.md`). Where the console cannot supply one yet, the parameter is
optional and the query is unscoped rather than empty.

Two places need an actor and the console has none to send until auth lands:

- **Shifts** (`POST /api/command-center/shifts`) accept an optional
  `operator_id`, otherwise attribute the shift to the workspace owner, and
  fail with 422 when there is neither.
- **Custody events and push registrations** always record the actor as text and
  set the user foreign key only when it resolves, so a deleted account can
  neither reject the write nor erase who acted.

## Running the tests

Database-backed tests skip when no server is reachable, so CI — which runs
pytest with no Postgres service — is unaffected.

```bash
# All of them, skipping the DB-backed ones
cd backend && pytest tests/ -v

# With a database
docker compose up -d db redis
createdb vaf_ws_b_test        # or let your server's defaults apply
cd backend && pytest tests/ -v
```

Connection settings come from the environment, defaulting to
`postgresql+asyncpg://vaf:test@localhost:5432/vaf_ws_b_test`:

| Variable | Default |
| --- | --- |
| `TEST_DATABASE_URL` | *(unset — overrides everything below)* |
| `POSTGRES_HOST` | `localhost` |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_USER` | `vaf` |
| `POSTGRES_PASSWORD` | `test` |
| `POSTGRES_TEST_DB` | `vaf_ws_b_test` |
| `TEST_REDIS_URL` | `redis://localhost:6379/15` |

`tests/db_utils.py` provides the shared harness: `requires_postgres()` to skip,
`fresh_engine()` for an engine with the schema present, `db_session_factory()`,
and `seed_workspace()`.

### The restart test

Every converted subsystem has one. It writes through one engine, disposes it,
and reads back through a **brand-new** engine — a fresh connection pool and a
fresh identity map, so anything still readable genuinely came out of Postgres
rather than lingering in process memory.

```python
async with factory() as session:
    ...                                   # write

restarted_engine = await fresh_engine()   # nothing carries over
restarted = db_session_factory(restarted_engine)
async with restarted() as session:
    ...                                   # must still be there
```

`test_edge_fleet.py` also asserts two concurrent sessions see each other's
writes, and `test_capture.py` asserts a session created by one manager is
visible to another — the multi-worker case.

## Background work

Pipeline runs and training jobs execute in Celery workers, not in the request.

- The task is handed the `PipelineRun` row the request created and moves it
  `pending → running → completed/failed`, persisting results and timings. It
  used to invent its own run id and return a dict nobody stored, so the row the
  console polls stayed `pending` forever.
- Dispatch failures are visible. `app/tasks/dispatch.py` raises `DispatchError`
  and the endpoint marks the run failed with the reason, so a dead broker looks
  like a failed run rather than a hung one. Previously both run endpoints
  dispatched inside `try: ... except: pass`.
- A crashed training task records the failure on the experiment before
  re-raising, so the row reaches a terminal state.

```bash
celery -A app.celery_app worker --loglevel=info
```

## Route wiring

`backend/tests/test_route_wiring.py` extracts every `/api/...` path from
`frontend/src` and asserts each resolves against the mounted route table. It
exists because ten route modules defined endpoints `app/api/router.py` never
included, so they 404'd at runtime while every unit test passed. It also guards
duplicate handlers on the same method+path, which is how a stub with the wrong
response shape silently shadows the real implementation.
