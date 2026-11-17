"""One append-only audit log for every system. A refusal is recorded too:
what was attempted, by whom, and the rule that said no."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException


# The build seeds earlier decisions at their own dates: it sets CLOCK, so every
# record and refusal made during the build carries that time, not the build's.
CLOCK: datetime | None = None


def now() -> datetime:
    return CLOCK or datetime.now().replace(microsecond=0)


def record(cur: Any, actor: str, system: str, subject: str, action: str, *, project_id: str | None = None,
           outcome: str = "recorded", detail: str = "", reason: str | None = None, at: datetime | None = None) -> None:
    next_id = cur.execute("SELECT coalesce(max(audit_id), 0) + 1 FROM audit_log").fetchone()[0]
    cur.execute("INSERT INTO audit_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [next_id, at or now(), actor, system, project_id, subject, action, outcome, detail[:500], reason])


def refuse(cur: Any, actor: str, system: str, subject: str, action: str, why: str, *,
           project_id: str | None = None, status: int = 409, at: datetime | None = None) -> None:
    """Record the refusal, then refuse. Never a warning."""
    record(cur, actor, system, subject, action, project_id=project_id, outcome="refused", detail=why, at=at)
    raise HTTPException(status_code=status, detail=why)
