from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.control import PurchaseInvoice, Supplier
from app.models.user import User
from app.schemas.control import DecisionNote, PurchaseInvoiceCreate, PurchaseInvoiceOut
from app.services.activity import log_activity
from app.services.settings import get_settings

router = APIRouter(prefix="/purchase-invoices", tags=["Purchase invoices"])


def match_status(received: Decimal, invoiced: Decimal, tolerance_pct: float, enabled: bool) -> str:
    """نتیجهٔ تطبیق رسید انبار با فاکتور."""
    if not enabled or received == invoiced:
        return "matched"
    base = max(received, invoiced)
    diff_pct = float(abs(received - invoiced) / base * 100) if base else 0.0
    return "review" if diff_pct <= tolerance_pct else "mismatch"


@router.get("/", response_model=list[PurchaseInvoiceOut])
async def list_invoices(
    q: str | None = Query(None, description="جستجو در شماره، تأمین‌کننده یا سفارش"),
    status: str | None = Query(None, description="matched / review / mismatch / resolved"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(PurchaseInvoice)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                PurchaseInvoice.number.ilike(like),
                PurchaseInvoice.supplier_name.ilike(like),
                PurchaseInvoice.po_number.ilike(like),
            )
        )
    if status:
        stmt = stmt.where(PurchaseInvoice.status == status)
    result = await db.execute(
        stmt.order_by(PurchaseInvoice.created_at.desc(), PurchaseInvoice.id.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all()


@router.post("/", response_model=PurchaseInvoiceOut, status_code=201)
async def create_invoice(
    data: PurchaseInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supplier = await db.get(Supplier, data.supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="تأمین‌کننده یافت نشد")

    cfg = await get_settings(db)
    invoice = PurchaseInvoice(
        **data.model_dump(),
        supplier_name=supplier.name,
        status=match_status(
            data.received_qty,
            data.invoiced_qty,
            cfg["match_tolerance_pct"],
            cfg["controls"]["three_way_match"],
        ),
    )
    db.add(invoice)
    log_activity(
        db, current_user.full_name, "invoice_created", "invoice",
        f"{invoice.number} • {supplier.name} • {invoice.status}",
    )
    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/resolve", response_model=PurchaseInvoiceOut)
async def resolve_invoice(
    invoice_id: int,
    body: DecisionNote | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    invoice = await db.get(PurchaseInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="فاکتور یافت نشد")
    if invoice.status not in ("mismatch", "review"):
        raise HTTPException(status_code=400, detail="این فاکتور مغایرتی ندارد")
    invoice.status = "resolved"
    invoice.note = body.note if body else None
    log_activity(
        db, current_user.full_name, "invoice_resolved", "invoice",
        f"{invoice.number} • {invoice.supplier_name}",
    )
    await db.commit()
    await db.refresh(invoice)
    return invoice
