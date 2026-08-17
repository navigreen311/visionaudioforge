# Authentication, tenancy and the trust boundary

Owner: WS-A. This document is the contract other workstreams build against.

---

## TL;DR for other workstreams

**You do not need to add anything to your routes to make them require a login.**
They already do. What you *do* need:

```python
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_workspace_id

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("")
async def list_assets(
    workspace_id: UUID = Depends(get_workspace_id),   # <- always this
    db: AsyncSession = Depends(get_db),
):
    return await AssetService(db).list(workspace_id=workspace_id)
```

Rules:

1. **Never** take `workspace_id` from a path parameter, query parameter, header
   or request body. A caller who can name a workspace can name someone else's.
2. **Never** default a workspace. There is no `00000000-…-0001` any more, on
   either side of the wire.
3. If your endpoint needs the user row as well, use
   `Depends(get_current_user)` — it reuses the identity the middleware already
   resolved and only loads the row.

---

## How a request is authenticated

`AuthenticationMiddleware` (`app/middleware/auth.py`) wraps the entire
application. It is deny-by-default:

```
request ──▶ CORS ──▶ RequestID ──▶ Timing ──▶ GZip ──▶ Audit ──▶ Auth ──▶ route
                                                                  │
                                            no/!valid credential ─┴─▶ 401
```

It accepts either:

| Header | Used by | Workspace source |
| --- | --- | --- |
| `Authorization: Bearer <jwt>` | the console, SDK users | `workspace_id` claim |
| `X-API-Key: <key>` | machine-to-machine | the API key row |

On success it publishes the caller on the ASGI scope, which surfaces as
`request.state`:

| `request.state.…` | Type | Meaning |
| --- | --- | --- |
| `identity` | `Identity \| None` | the whole resolved caller |
| `user_id` | `UUID \| None` | subject of the token / owner of the key |
| `workspace_id` | `UUID \| None` | tenant, when the token carries the claim |
| `auth_method` | `"jwt" \| "api_key" \| None` | how they got in |
| `request_id` | `str` | set by `RequestIDMiddleware` |

### Why middleware and not a dependency per route

57 of 63 route modules required no identity. Sprinkling
`Depends(get_current_user)` across them has two failure modes that middleware
does not:

- It is **unreviewable**: answering "is anything public?" means reading 63
  files, and re-reading them after every merge.
- It **fails open**: the route module added next month is public until someone
  notices. `tests/test_auth_enforcement.py` exists precisely because
  "someone notices" is not a control.

Middleware inverts that. A new route is protected the instant it is registered;
making it public is a one-line diff to a file whose only job is to be read
carefully.

### The public allowlist

`app/core/auth_policy.py` is the single definition of what is reachable
anonymously:

- `/api/health`, `/api/metrics` — probes and scrapes cannot hold credentials.
- `/api/auth/login`, `/api/auth/register`, `/api/auth/refresh` — you cannot
  present a token to obtain a token.
- `/docs`, `/redoc`, `/openapi.json`, `/docs/oauth2-redirect` — the OpenAPI
  surface.
- `/` and `/static/*`, `/favicon*`.
- Every `OPTIONS` request: a CORS preflight is sent by the browser *without*
  the `Authorization` header by design, so challenging it breaks every
  cross-origin call before the real request is ever made.

To add an entry: edit `PUBLIC_PATHS`, and say in the commit message why the
endpoint can be served to a stranger.

### The `AUTH_REQUIRED` switch

`settings.AUTH_REQUIRED` defaults to `True`. It exists so that opting out is
*deliberate and visible* rather than an accident of how a test constructs its
client. The backend test suite opts out in exactly one place —
`tests/conftest.py` — and individual tests opt back in with
`@pytest.mark.auth_enforced`.

Do not set `AUTH_REQUIRED=false` in any deployed environment.

---

## Where `workspace_id` comes from

```
JWT "workspace_id" claim  ──(present)──▶ request.state.workspace_id ──▶ get_workspace_id()
                          ──(absent)───▶ users.workspace_id lookup ─────▶ get_workspace_id()
                                                                  └─(none)─▶ 403
```

`get_workspace_id` never returns a default. A caller with no resolvable
workspace gets `403 Authenticated user is not attached to a workspace`.

### Open handoff to whoever owns `app/services/auth_service.py`

Tokens are currently minted as `{"sub": str(user.id)}`. Adding the workspace
makes resolution completely I/O-free:

```python
token_data = {"sub": str(user.id), "workspace_id": str(user.workspace_id)}
```

Both call sites are `AuthService.register` and `AuthService.login` (and the
re-mint inside `AuthService.refresh`). Nothing breaks without it — the
dependency falls back to a `users.workspace_id` lookup — but every
tenant-scoped request pays for a query until it lands.

WS-A did not make this change because `app/services/**` belongs to another
workstream.

### Enforcing the filter

Making the correct workspace *available* is WS-A's job and is done. Actually
applying `WHERE workspace_id = :workspace_id` inside each handler and service
is WS-B's. `tests/test_auth_enforcement.py` proves the plumbing carries the
right value; it does not prove every query uses it.

---

## WebSockets

`/ws/live/stream/{session_id}` and `/ws/agents/stream` stream live video and
copilot chat, and they were as open as everything else. They are now behind the
same middleware — which is one of the reasons it is raw ASGI rather than
`BaseHTTPMiddleware`, since the latter passes `websocket` scopes straight
through without ever seeing them.

The browser `WebSocket` constructor cannot set request headers, so the token
travels in the query string. Use the helper rather than building the URL by
hand:

```ts
import { authenticatedWsUrl } from "@/lib/session";

const ws = new WebSocket(authenticatedWsUrl(`${wsUrl}/ws/live/stream/${sessionId}`));
```

`?token=` is honoured for websocket handshakes **only**. Bearer tokens in URLs
end up in access logs, browser history and `Referer` headers, so plain HTTP
still requires the header. An unauthenticated handshake is closed with code
`1008` (policy violation).

### Call it at connect time, not at module scope

`authenticatedWsUrl` reads `localStorage`, which does not exist during SSR, and
a token captured at import time is stale by the time the socket opens. Build
the base URL wherever you like; append the token inside the connect callback.

That is why `CopilotChat` takes a plain `wsUrl` prop and appends the token
itself in `connectWs` — its caller (`(dashboard)/agents/page.tsx`) computes the
URL at module scope, where there is no session to read.

Current consumers:

| File | Socket |
| --- | --- |
| `src/app/(dashboard)/capture/page.tsx` | `/ws/live/stream/{session_id}` |
| `src/components/agents/CopilotChat.tsx` | `/ws/agents/stream` |

`src/lib/socket.ts` builds a **socket.io** client, which the backend does not
serve (the two WebSocket routes are raw ASGI). It is unused dead code as far as
this boundary is concerned; if socket.io is ever wired up it will need its own
auth handshake.

---

## Middleware restoration

All four custom middlewares were commented out in `main.py` with:

> compatibility issue with uvicorn 0.42 + starlette 0.52 on Windows

The version pin was a red herring. `BaseHTTPMiddleware` and
`RequestResponseEndpoint` both still import and run on the installed stack
(starlette 1.6, uvicorn 0.52, FastAPI 0.141). Two real defects were hiding
behind that note:

**1. `AuditMiddleware` leaked orphan tasks.** It called
`asyncio.ensure_future(_write_audit_log(...))` and dropped the handle. The
event loop keeps only a weak reference to a task, so an audit write could be
garbage-collected before it ran — silently losing the row the compliance claim
depends on. When the database was unreachable, the task's exception was never
retrieved, producing bare tracebacks on stderr; on the Windows Proactor loop,
tasks outliving the loop raise `RuntimeError: Event loop is closed` during
shutdown. That is the Windows-specific symptom the comment was pointing at.

*Fix:* tasks are held in a module-level set until done, with a done-callback
that logs failures. Gated by `settings.AUDIT_ENABLED` (default `True`).

**2. `BaseHTTPMiddleware` drops response headers on the error path.**
`RequestIDMiddleware` and `TimingMiddleware` mutated the `Response` object
returned by `call_next`. When the downstream raises, `call_next` raises too and
that line never runs — so a 500 carried no `X-Request-ID`, exactly when you
need one. `ServerErrorMiddleware` sits outside the user stack, so its response
never passes back through them either.

*Fix:* both are now raw ASGI and stamp the `http.response.start` message, so
denials (401) and errors (500) carry the headers. `RequestIDMiddleware` also
records the id on the ASGI scope — a dict shared by every layer — which is how
the global exception handler can quote it, whereas a contextvar set inside
`BaseHTTPMiddleware.dispatch` is reset before the handler runs.

Order (outermost first): `CORS → RequestID → Timing → GZip → Audit → Auth`.
Auth is innermost so that an unauthenticated request is still timed, logged and
stamped with a traceable id.

---

## Error responses

The global handler used to return `str(exc)` to the caller, handing an
anonymous client the shape of the failure — SQL fragments, absolute paths, key
names. It now returns:

```json
{ "detail": "Internal server error", "request_id": "0f0c…" }
```

with the same id in the `X-Request-ID` header, and logs the full traceback
server-side under that id. Set `DEBUG_ERRORS=true` to get `exception` and
`traceback` back in the body. It defaults to `False` and is deliberately
separate from `DEBUG`, so turning on verbose local logging does not also start
leaking stack frames.

---

## Console (frontend)

| File | Role |
| --- | --- |
| `src/middleware.ts` | Edge guard. Anonymous visitors are redirected to `/login?next=…` before any dashboard HTML is streamed. |
| `src/app/(dashboard)/layout.tsx` | Confirms the session against `/api/auth/me` and renders a spinner — never protected content — until it resolves. |
| `src/lib/session.ts` | Session primitives shared by the axios client, the store and the edge middleware. |
| `src/stores/auth.ts` | Holds `user`, `token` and `workspaceId`, all from the server. |

The edge middleware uses a negative matcher — public routes are named,
everything else is protected — for the same reason the backend does: a page
added tomorrow is guarded because nobody had to remember to guard it.

### The session cookie is not a security control

`src/middleware.ts` reads a JS-readable `vaf_session` cookie and checks its
`exp` **without verifying the signature**; the edge runtime has no business
holding the JWT secret. Forging that cookie gets you dashboard *chrome* and
nothing else — every API call still goes through the backend middleware, which
verifies properly. Treat the frontend guard as routing, not authorisation.

### `getWorkspaceId()`

`src/lib/api.ts` used to fall back to
`00000000-0000-0000-0000-000000000001`, which meant every browser asked the API
for the same tenant — there was nothing to isolate. It now reads the token's
`workspace_id` claim, then the `user.workspace_id` from `/api/auth/me`, and
**throws** when there is no session. That is intentional: the console is gated,
so reaching it without a session is a bug worth seeing rather than one to
paper over with somebody else's tenant id.

---

## Running the checks

```powershell
# everything WS-A owns, in one go
pwsh scripts/verify-auth.ps1
```

or by hand:

```bash
cd backend
../../vaf-venv/Scripts/python.exe -m pytest tests/test_auth_enforcement.py tests/test_auth.py tests/test_auth_wiring.py -v

cd ../frontend
npx tsc --noEmit
```

`tests/test_auth_enforcement.py::test_every_route_requires_authentication`
enumerates the live routing table. If it fails, either a genuinely public route
needs adding to `PUBLIC_PATHS` — with a reason — or the trust boundary just
regressed.
