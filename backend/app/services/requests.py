"""منطق مشترک درخواست‌های خرید: ساخت خروجی، تاریخچه و ثبت رویداد."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.timeutil import utcnow
from app.models.portal import PurchaseRequest, PurchaseRequestItem, RequestEvent
from app.models.user import User
from app.schemas.portal import EventOut, RequestItemOut, RequestOut
from app.services.buyer import debt_totals


def add_event(db: AsyncSession, req: PurchaseRequest, actor: str, action: str, note: str | None = None) -> None:
    db.add(RequestEvent(request_id=req.id, actor=actor, action=action, note=note))
    req.updated_at = utcnow()


async def build_out(
    db: AsyncSession,
    requests: Iterable[PurchaseRequest],
    *,
    with_events: bool = False,
    with_debt: bool = False,
) -> list[RequestOut]:
    """تبدیل چند درخواست به خروجی با تعداد ثابتی کوئری (بدون N+1)."""
    requests = list(requests)
    if not requests:
        return []
    ids = [r.id for r in requests]

    items: dict[int, list] = defaultdict(list)
    for item in (
        await db.execute(select(PurchaseRequestItem).where(PurchaseRequestItem.request_id.in_(ids)).order_by(PurchaseRequestItem.id))
    ).scalars():
        items[item.request_id].append(RequestItemOut.model_validate(item))

    events: dict[int, list] = defaultdict(list)
    if with_events:
        for ev in (
            await db.execute(select(RequestEvent).where(RequestEvent.request_id.in_(ids)).order_by(RequestEvent.at, RequestEvent.id))
        ).scalars():
            events[ev.request_id].append(EventOut.model_validate(ev))

    user_ids = {r.buyer_id for r in requests} | {r.assigned_to_id for r in requests if r.assigned_to_id}
    names = {
        u.id: u.full_name
        for u in (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars()
    }
    debts = await debt_totals(db) if with_debt else {}

    out = []
    for r in requests:
        out.append(
            RequestOut(
                id=r.id, ref=r.ref, buyer_id=r.buyer_id, buyer_name=names.get(r.buyer_id),
                buyer_debt=debts.get(r.buyer_id, 0) if with_debt else None,
                note=r.note, status=r.status, department=r.department,
                assigned_to_id=r.assigned_to_id, assigned_to_name=names.get(r.assigned_to_id),
                decision_note=r.decision_note, created_at=r.created_at, updated_at=r.updated_at,
                items=items.get(r.id, []), events=events.get(r.id, []),
            )
        )
    return out
