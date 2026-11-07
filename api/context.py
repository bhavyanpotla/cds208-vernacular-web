"""Per-request context: which browser session and which learner is calling.

A ContextVar is enough — FastAPI runs each request in its own task, and the
event log only needs to read these two values while the request is in flight.
"""

from __future__ import annotations

from contextvars import ContextVar

SESSION: ContextVar[str | None] = ContextVar("session_id", default=None)
USER: ContextVar[int | None] = ContextVar("user_id", default=None)


def resolve(key: str):
    """The hook core.events calls for every logged event."""
    if key == "session_id":
        return SESSION.get()
    if key == "user_id":
        return USER.get()
    return None
