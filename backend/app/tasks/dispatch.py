"""Task dispatch with a visible failure mode.

Both pipeline-run endpoints used to dispatch inside ``try: ... except: pass``.
With the broker down that meant the run row was created, no worker ever picked
it up, and the console polled a job that would stay ``pending`` forever with
nothing anywhere saying why.

Dispatch failures are recorded on the row instead, so a stuck queue looks like
a failed run rather than a hung one.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DispatchError(RuntimeError):
    """Raised when a task could not be handed to the broker."""


def dispatch(task: Any, *args: Any, **kwargs: Any) -> str | None:
    """Queue a Celery task and return its id.

    Raises:
        DispatchError: if the broker refused or was unreachable.
    """
    try:
        async_result = task.delay(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 — broker errors vary by transport
        logger.error("Could not queue %s: %s", getattr(task, "name", task), exc)
        raise DispatchError(str(exc)) from exc

    return getattr(async_result, "id", None)
