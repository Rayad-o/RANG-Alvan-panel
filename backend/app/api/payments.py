import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.timeutil import utcnow
from app.models.control import PaymentRequest, Supplier
from app.models.user import User
from app.schemas.control import DecisionNote, PaymentCreate, PaymentOut
from app.services.activity import log_activity
from app.services.risk import score_payment
from app.services.settings import get_settings, required_role, role_allows

router = APIRouter(prefix="/payments", tags=["Payments"])

_manager = require_roles("manager", "admin")


def _out(payment: PaymentRequest, cfg: dict) -> PaymentOut:
    out = PaymentOut.model_validate(payment)
    out.required_role = required_role(payment.amount, cfg, payment.risk_score)
    return out


@router.get("/", response_model=list[PaymentOut])
async def list_payments(
    q: str | None = Query(None, description="جستجو در شرح، طرف حساب یا شماره"),
    risk: str | None = Query(None, description="high / med / low"),
    status: str | None = Query(None, description="pending / approved / stopped"),
    supplier_id: int | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = await get_settings(db)
    high = cfg["high_risk_threshold"]
    stmt = select(PaymentRequest)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                PaymentRequest.party_name.ilike(like),
                PaymentRequest.description.ilike(like),
                PaymentRequest.ref.ilike(like),
                PaymentRequest.po_ref.ilike(like),
            )
        )
    if risk == "high":
        stmt = stmt.where(PaymentRequest.risk_score >= high)
    elif risk == "med":
        stmt = stmt.where(PaymentRequest.risk_score >= 40, PaymentRequest.risk_score < high)
    elif risk == "low":
        stmt = stmt.where(PaymentRequest.risk_score < 40)
    if status:
        stmt = stmt.where(PaymentRequest.status == status)
    if supplier_id:
        stmt = stmt.where(PaymentRequest.supplier_id == supplier_id)

    rows = (
        await db.execute(
            stmt.order_by(PaymentRequest.created_at.desc(), PaymentRequest.id.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return [_out(p, cfg) for p in rows]


@router.post("/", response_model=PaymentOut, status_code=201)
async def create_payment(
    data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supplier = await db.get(Supplier, data.supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="تأمین‌کننده یافت نشد")

    cfg = await get_settings(db)
    payment = PaymentRequest(
        supplier_id=supplier.id,
        party_name=supplier.name,
        description=data.description,
        po_ref=(data.po_ref or "").strip() or None,
        amount=data.amount,
        created_by=current_user.full_name,
        created_at=utcnow(),
    )
    db.add(payment)
    await db.flush()

    score, reasons = await score_payment(db, supplier, payment, cfg)
    payment.risk_score = score
    payment.risk_reasons = json.dumps(reasons, ensure_ascii=False)
    payment.ref = f"#{4400 + payment.id}"

    log_activity(
        db, current_user.full_name, "payment_created", "payment",
        f"{payment.ref} • {supplier.name} • ریسک {score}",
    )
    await db.commit()
    await db.refresh(payment)
    return _out(payment, cfg)


async def _get_decidable(db: AsyncSession, payment_id: int, allowed: tuple[str, ...]) -> PaymentRequest:
    payment = await db.get(PaymentRequest, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="پرداخت یافت نشد")
    if payment.status not in allowed:
        raise HTTPException(status_code=400, detail="وضعیت فعلی این پرداخت اجازهٔ این اقدام را نمی‌دهد")
    return payment


@router.post("/{payment_id}/approve", response_model=PaymentOut)
async def approve_payment(
    payment_id: int,
    body: DecisionNote | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_manager),
):
    payment = await _get_decidable(db, payment_id, ("pending", "stopped"))
    cfg = await get_settings(db)

    needed = required_role(payment.amount, cfg, payment.risk_score)
    if not role_allows(current_user.role.value, needed):
        label = "مدیرعامل/ادمین" if needed == "admin" else "مدیر"
        raise HTTPException(status_code=403, detail=f"تأیید این پرداخت (مبلغ/ریسک) نیازمند نقش {label} است")

    payment.status = "approved"
    payment.decided_by = current_user.full_name
    payment.decided_at = utcnow()
    payment.decision_note = body.note if body else None
    log_activity(db, current_user.full_name, "payment_approved", "payment", f"{payment.ref} • {payment.party_name}")
    await db.commit()
    await db.refresh(payment)
    return _out(payment, cfg)


@router.post("/{payment_id}/stop", response_model=PaymentOut)
async def stop_payment(
    payment_id: int,
    body: DecisionNote | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_manager),
):
    payment = await _get_decidable(db, payment_id, ("pending",))
    cfg = await get_settings(db)

    payment.status = "stopped"
    payment.decided_by = current_user.full_name
    payment.decided_at = utcnow()
    payment.decision_note = body.note if body else None
    log_activity(db, current_user.full_name, "payment_stopped", "payment", f"{payment.ref} • {payment.party_name}")
    await db.commit()
    await db.refresh(payment)
    return _out(payment, cfg)
