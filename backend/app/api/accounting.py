"""API حسابدار: ثبت بدهی خریداران، ثبت پرداخت و فهرست خریداران."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.buyer import _debt_out
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.timeutil import utcnow
from app.models.portal import BuyerDebt, DebtPayment, PurchaseRequest
from app.models.user import User, UserRole
from app.schemas.portal import BuyerRow, DebtCreate, DebtOut, DebtPay, VoidNote
from app.services.activity import log_activity
from app.services.buyer import OPEN_REQUEST_STATUSES, debt_totals, is_blocked
from app.services.settings import get_settings

router = APIRouter(prefix="/accounting", tags=["Accounting"])

# مشاهده: حسابدار، مدیر سیستم، مدیر — ثبت و تغییر: فقط حسابدار و مدیر سیستم
_view = require_roles("accountant", "admin", "manager")
_edit = require_roles("accountant", "admin")


async def _active_buyer(db: AsyncSession, buyer_id: int) -> User:
    buyer = await db.get(User, buyer_id)
    if buyer is None or buyer.role != UserRole.buyer:
        raise HTTPException(status_code=404, detail="خریدار یافت نشد")
    return buyer


@router.get("/buyers", response_model=list[BuyerRow])
async def list_buyers(
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_view),
):
    cfg = await get_settings(db)
    stmt = select(User).where(User.role == UserRole.buyer)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.full_name.ilike(like), User.email.ilike(like)))
    buyers = (await db.execute(stmt.order_by(User.full_name))).scalars().all()

    totals = await debt_totals(db)
    open_counts = dict(
        (await db.execute(
            select(PurchaseRequest.buyer_id, func.count(PurchaseRequest.id))
            .where(PurchaseRequest.status.in_(OPEN_REQUEST_STATUSES))
            .group_by(PurchaseRequest.buyer_id)
        )).all()
    )
    return [
        BuyerRow(
            id=b.id, full_name=b.full_name, email=b.email, is_active=b.is_active,
            total_debt=totals.get(b.id, Decimal(0)),
            blocked=is_blocked(totals.get(b.id, Decimal(0)), cfg["buyer_debt_limit"]),
            open_requests=open_counts.get(b.id, 0),
        )
        for b in buyers
    ]


@router.get("/debts", response_model=list[DebtOut])
async def list_debts(
    q: str | None = Query(None, description="جستجو در نام خریدار یا شرح"),
    status: str | None = Query(None, description="open / paid / voided"),
    buyer_id: int | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_view),
):
    stmt = select(BuyerDebt, User.full_name).join(User, User.id == BuyerDebt.buyer_id)
    if status:
        stmt = stmt.where(BuyerDebt.status == status)
    if buyer_id:
        stmt = stmt.where(BuyerDebt.buyer_id == buyer_id)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.full_name.ilike(like), BuyerDebt.description.ilike(like)))
    rows = (
        await db.execute(stmt.order_by(BuyerDebt.created_at.desc(), BuyerDebt.id.desc()).limit(limit).offset(offset))
    ).all()
    return [_debt_out(d, name) for d, name in rows]


@router.post("/debts", response_model=DebtOut, status_code=201)
async def create_debt(
    data: DebtCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_edit),
):
    buyer = await _active_buyer(db, data.buyer_id)
    debt = BuyerDebt(
        buyer_id=buyer.id, amount=data.amount, paid_amount=0,
        description=(data.description or "").strip() or None, due_date=data.due_date,
        created_by=current_user.full_name,
    )
    db.add(debt)
    await db.flush()
    log_activity(db, current_user.full_name, "debt_created", "debt", f"{buyer.full_name} • {data.amount:,.0f} تومان")
    await db.commit()
    return _debt_out(debt, buyer.full_name)


@router.post("/debts/{debt_id}/pay", response_model=DebtOut)
async def pay_debt(
    debt_id: int,
    data: DebtPay,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_edit),
):
    debt = await db.get(BuyerDebt, debt_id)
    if debt is None:
        raise HTTPException(status_code=404, detail="بدهی یافت نشد")
    if debt.status != "open":
        raise HTTPException(status_code=400, detail="این بدهی دیگر باز نیست")
    remaining = debt.amount - debt.paid_amount
    if data.amount > remaining:
        raise HTTPException(status_code=400, detail=f"مبلغ پرداختی بیشتر از مانده بدهی ({remaining:,.0f} تومان) است")

    debt.paid_amount = debt.paid_amount + data.amount
    if debt.paid_amount >= debt.amount:
        debt.status = "paid"
    db.add(DebtPayment(debt_id=debt.id, amount=data.amount, note=data.note, recorded_by=current_user.full_name, paid_at=utcnow()))
    buyer = await db.get(User, debt.buyer_id)
    log_activity(db, current_user.full_name, "debt_paid", "debt", f"{buyer.full_name} • {data.amount:,.0f} تومان")
    await db.commit()
    return _debt_out(debt, buyer.full_name)


@router.post("/debts/{debt_id}/void", response_model=DebtOut)
async def void_debt(
    debt_id: int,
    data: VoidNote,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_edit),
):
    debt = await db.get(BuyerDebt, debt_id)
    if debt is None:
        raise HTTPException(status_code=404, detail="بدهی یافت نشد")
    if debt.status != "open":
        raise HTTPException(status_code=400, detail="فقط بدهی باز قابل ابطال است")
    debt.status = "voided"
    debt.void_note = data.note
    buyer = await db.get(User, debt.buyer_id)
    log_activity(db, current_user.full_name, "debt_voided", "debt", f"{buyer.full_name} • {data.note}")
    await db.commit()
    return _debt_out(debt, buyer.full_name)
