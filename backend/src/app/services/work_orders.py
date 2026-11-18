"""Maintenance work orders: the governed write path.

A property manager raises a work order against a current tenancy, with a
quote. Then:

  - at or under the agreed limit, it is approved within that limit - no
    second person, but recorded like any other decision
  - over it, someone other than the person who raised it must decide
  - over the higher limit, only the head of property management may approve
  - a decision needs a note; completion needs the actual cost, and a cost
    well over the quote needs a reason
  - a work order for a tenancy that has ended is refused

Every step is audit-logged. A refusal is recorded too, and returned as a
sentence a person can act on - never a warning that can be clicked past.
Each rule is checked again at the moment it applies, on the server.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.app.pipeline import reference as ref
from src.app.services import audit

SYSTEM = "work_orders"
CATEGORIES = ref.MAINTENANCE


def _refuse(cur, actor: str, subject: str, action: str, why: str, status: int = 409) -> None:
    audit.refuse(cur, actor, SYSTEM, subject, action, why, project_id=subject, status=status)


def _role(actor: str) -> str | None:
    return ref.WO_PEOPLE.get(actor)


def money(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def raise_order(cur, actor: str, tenancy_id: str, category: str, priority: str, description: str, quote_cents: int,
                at: datetime | None = None) -> dict[str, Any]:
    at = at or audit.now()
    subject = tenancy_id or "-"
    if not _role(actor):
        _refuse(cur, actor, subject, "raise", "Only a property manager or the head of property management raises a work order.", 403)
    if category not in CATEGORIES:
        _refuse(cur, actor, subject, "raise", f"Choose a category: {', '.join(CATEGORIES)}.", 422)
    if priority not in ("urgent", "routine"):
        _refuse(cur, actor, subject, "raise", "Priority is urgent or routine.", 422)
    if len((description or "").strip()) < 10:
        _refuse(cur, actor, subject, "raise", "Say what the job is, in a sentence: the tradesperson and the approver both read it.", 422)
    if not isinstance(quote_cents, int) or quote_cents <= 0:
        _refuse(cur, actor, subject, "raise", "A work order needs the quote, in dollars and cents.", 422)
    cur.execute("SELECT office_code, end_on FROM tenancy WHERE tenancy_id = ?", [tenancy_id])
    row = cur.fetchone()
    if not row:
        _refuse(cur, actor, subject, "raise", f"There is no tenancy {tenancy_id}.", 404)
    office, end_on = row
    if end_on is not None:
        _refuse(cur, actor, subject, "raise",
                f"Tenancy {tenancy_id} ended on {end_on.strftime('%d/%m/%Y')}. Raise the job against the current tenancy, or as an owner's job.")
    cur.execute("SELECT coalesce(max(CAST(substr(wo_id, 4) AS INTEGER)), 0) + 1 FROM work_order")
    wo_id = f"WO-{cur.fetchone()[0]:04d}"
    within = quote_cents <= ref.WO_AUTO_LIMIT_CENTS
    status = "approved" if within else "awaiting approval"
    cur.execute("INSERT INTO work_order VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)",
                [wo_id, tenancy_id, office, category, priority, description.strip()[:400], quote_cents, actor, at, status,
                 "within the agreed limit" if within else None, at if within else None,
                 f"At or under {money(ref.WO_AUTO_LIMIT_CENTS)}: approved within the agreed limit." if within else None])
    audit.record(cur, actor, SYSTEM, tenancy_id, "raised", project_id=wo_id,
                 detail=f"{category}, {priority}, quote {money(quote_cents)}" + ("; approved within the agreed limit" if within else ""), at=at)
    return {"wo_id": wo_id, "status": status}


def decide(cur, actor: str, wo_id: str, approve: bool, note: str, at: datetime | None = None) -> dict[str, Any]:
    at = at or audit.now()
    cur.execute("SELECT raised_by, status, quote_cents, tenancy_id FROM work_order WHERE wo_id = ?", [wo_id])
    row = cur.fetchone()
    if not row:
        _refuse(cur, actor, wo_id, "decide", f"There is no work order {wo_id}.", 404)
    raised_by, status, quote, tenancy_id = row
    if not _role(actor):
        _refuse(cur, actor, wo_id, "decide", "Only a property manager or the head of property management decides a work order.", 403)
    if actor == raised_by:
        _refuse(cur, actor, wo_id, "decide", "You raised this work order, so you cannot decide it. Someone else must.", 403)
    if status != "awaiting approval":
        _refuse(cur, actor, wo_id, "decide", f"{wo_id} is {status}; only a work order awaiting approval is decided.")
    if len((note or "").strip()) < 5:
        _refuse(cur, actor, wo_id, "decide", "Record the reason for the decision.", 422)
    if approve and quote > ref.WO_HEAD_LIMIT_CENTS and _role(actor) != "head":
        _refuse(cur, actor, wo_id, "approve",
                f"The quote of {money(quote)} is over {money(ref.WO_HEAD_LIMIT_CENTS)}: only the head of property management may approve it.", 403)
    cur.execute("SELECT end_on FROM tenancy WHERE tenancy_id = ?", [tenancy_id])
    end_on = cur.fetchone()[0]
    if approve and end_on is not None:
        _refuse(cur, actor, wo_id, "approve", f"Tenancy {tenancy_id} has since ended. Re-raise the job against the current tenancy.")
    new = "approved" if approve else "rejected"
    cur.execute("UPDATE work_order SET status = ?, decided_by = ?, decided_at = ?, decision_note = ? WHERE wo_id = ?",
                [new, actor, at, note.strip()[:300], wo_id])
    audit.record(cur, actor, SYSTEM, tenancy_id, new, project_id=wo_id, detail=note.strip()[:200], at=at)
    return {"wo_id": wo_id, "status": new}


def complete(cur, actor: str, wo_id: str, cost_cents: int, note: str, at: datetime | None = None) -> dict[str, Any]:
    at = at or audit.now()
    cur.execute("SELECT status, quote_cents, tenancy_id FROM work_order WHERE wo_id = ?", [wo_id])
    row = cur.fetchone()
    if not row:
        _refuse(cur, actor, wo_id, "complete", f"There is no work order {wo_id}.", 404)
    status, quote, tenancy_id = row
    if not _role(actor):
        _refuse(cur, actor, wo_id, "complete", "Only a property manager or the head of property management completes a work order.", 403)
    if status != "approved":
        _refuse(cur, actor, wo_id, "complete", f"{wo_id} is {status}. Only approved work is completed - and paid.")
    if not isinstance(cost_cents, int) or cost_cents <= 0:
        _refuse(cur, actor, wo_id, "complete", "Enter the invoiced cost.", 422)
    over = cost_cents * 100 > quote * (100 + ref.WO_VARIANCE_PCT)
    if over and len((note or "").strip()) < 10:
        _refuse(cur, actor, wo_id, "complete",
                f"The cost of {money(cost_cents)} is more than {ref.WO_VARIANCE_PCT}% over the quote of {money(quote)}. Say why before it is paid.", 422)
    cur.execute("UPDATE work_order SET status = 'completed', completed_cost_cents = ?, completed_at = ?, completion_note = ? WHERE wo_id = ?",
                [cost_cents, at, (note or "").strip()[:300] or None, wo_id])
    audit.record(cur, actor, SYSTEM, tenancy_id, "completed", project_id=wo_id,
                 detail=f"cost {money(cost_cents)} against quote {money(quote)}" + (f"; {note.strip()[:120]}" if over else ""), at=at)
    return {"wo_id": wo_id, "status": "completed"}
