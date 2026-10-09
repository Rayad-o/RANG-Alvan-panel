"""API پنل خریدار: بدهی‌ها، فهرست کالاها و ثبت درخواست خرید."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.inventory import InventoryItem
from app.models.portal import BuyerDebt, PurchaseRequest, PurchaseRequestItem
from app.models.user import User
from app.schemas.portal import DebtOut, RequestCreate, RequestOut
from app.services.activity import log_activity
from app.services.buyer import DEBT_BLOCK_MESSAGE, OPEN_REQUEST_STATUSES, buyer_debt_total, is_blocked
from app.services.requests import add_event, build_out
from app.services.settings import get_settings

router = APIRouter(prefix="/buyer", tags=["Buyer"])

_buyer = require_roles("buyer")


def _debt_out(d: BuyerDebt, buyer_name: str | None = None) -> DebtOut:
    return DebtOut(
        id=d.id, buyer_id=d.buyer_id, buyer_name=buyer_name, amount=d.amount, paid_amount=d.paid_amount,
        remaining=max(d.amount - d.paid_amount, 0) if d.status != "voided" else 0,
        description=d.description, due_date=d.due_date, status=d.status,
        created_by=d.created_by, created_at=d.created_at,
    )


@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db), current_user: User = Depends(_buyer)):
    cfg = await get_settings(db)
    total = await buyer_debt_total(db, current_user.id)
    limit = cfg["buyer_debt_limit"]
    blocked = is_blocked(total, limit)
    open_requests = (
        await db.execute(
            select(func.count(PurchaseRequest.id)).where(
                PurchaseRequest.buyer_id == current_user.id, PurchaseRequest.status.in_(OPEN_REQUEST_STATUSES)
            )
        )
    ).scalar_one()
    open_debts = (
        await db.execute(
            select(func.count(BuyerDebt.id)).where(BuyerDebt.buyer_id == current_user.id, BuyerDebt.status == "open")
        )
    ).scalar_one()
    return {
        "total_debt": total,
        "debt_limit": limit,
        "blocked": blocked,
        "message": DEBT_BLOCK_MESSAGE if blocked else None,
        "open_requests": open_requests,
        "open_debts": open_debts,
    }


@router.get("/debts", response_model=list[DebtOut])
async def my_debts(db: AsyncSession = Depends(get_db), current_user: User = Depends(_buyer)):
    rows = (
        await db.execute(
            select(BuyerDebt)
            .where(BuyerDebt.buyer_id == current_user.id, BuyerDebt.status != "voided")
            .order_by(BuyerDebt.status.asc(), BuyerDebt.created_at.desc())  # "open" قبل از "paid"
        )
    ).scalars().all()
    return [_debt_out(d) for d in rows]


@router.get("/products")
async def products(db: AsyncSession = Depends(get_db), current_user: User = Depends(_buyer)):
    rows = (await db.execute(select(InventoryItem).order_by(InventoryItem.title))).scalars().all()
    return [{"id": p.id, "code": p.code, "title": p.title, "available": float(p.quantity or 0)} for p in rows]


@router.get("/requests", response_model=list[RequestOut])
async def my_requests(db: AsyncSession = Depends(get_db), current_user: User = Depends(_buyer)):
    rows = (
        await db.execute(
            select(PurchaseRequest)
            .where(PurchaseRequest.buyer_id == current_user.id)
            .order_by(PurchaseRequest.created_at.desc(), PurchaseRequest.id.desc())
            .limit(200)
        )
    ).scalars().all()
    return await build_out(db, rows, with_events=True)


@router.post("/requests", response_model=RequestOut, status_code=201)
async def create_request(
    data: RequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_buyer),
):
    # قاعدهٔ اصلی: بدهی بیشتر از سقف مجاز (پیش‌فرض ۲۰ میلیون تومان) = ثبت درخواست ممنوع
    cfg = await get_settings(db)
    total = await buyer_debt_total(db, current_user.id)
    if is_blocked(total, cfg["buyer_debt_limit"]):
        raise HTTPException(status_code=400, detail=DEBT_BLOCK_MESSAGE)

    # هر کالا فقط یک بار؛ تعدادهای تکراری جمع می‌شوند
    wanted: dict[int, float] = {}
    for item in data.items:
        wanted[item.product_id] = wanted.get(item.product_id, 0) + float(item.quantity)

    products = {
        p.id: p
        for p in (await db.execute(select(InventoryItem).where(InventoryItem.id.in_(wanted.keys())))).scalars()
    }
    missing = [pid for pid in wanted if pid not in products]
    if missing:
        raise HTTPException(status_code=400, detail="یکی از کالاهای انتخاب‌شده معتبر نیست")

    req = PurchaseRequest(buyer_id=current_user.id, note=(data.note or "").strip() or None)
    db.add(req)
    await db.flush()
    req.ref = f"RQ-{1000 + req.id}"
    for pid, qty in wanted.items():
        p = products[pid]
        db.add(PurchaseRequestItem(
            request_id=req.id, product_id=p.id, product_code=p.code, product_title=p.title, quantity=qty,
        ))
    add_event(db, req, current_user.full_name, "created")
    log_activity(db, current_user.full_name, "request_created", "request", f"{req.ref} • {len(wanted)} قلم")
    await db.commit()
    return (await build_out(db, [req], with_events=True))[0]


@router.post("/requests/{request_id}/cancel", response_model=RequestOut)
async def cancel_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_buyer),
):
    req = await db.get(PurchaseRequest, request_id)
    if req is None or req.buyer_id != current_user.id:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")
    if req.status != "submitted":
        raise HTTPException(status_code=400, detail="فقط درخواستی که هنوز بررسی نشده قابل لغو است")
    req.status = "cancelled"
    add_event(db, req, current_user.full_name, "cancelled")
    await db.commit()
    return (await build_out(db, [req], with_events=True))[0]
