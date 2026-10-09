from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.sales import SalesInvoice
from app.schemas.sales import SalesInvoiceCreate, SalesInvoiceOut

router = APIRouter(prefix="/sales", tags=["Sales"])

@router.post("/", response_model=SalesInvoiceOut)
async def create_sale(
    data: SalesInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = SalesInvoice(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.get("/", response_model=list[SalesInvoiceOut])
async def list_sales(
    q: str | None = Query(None, description="جستجو در نام مشتری یا شماره فاکتور"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(SalesInvoice)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(SalesInvoice.customer_name.ilike(like), SalesInvoice.invoice_number.ilike(like)))
    stmt = stmt.order_by(SalesInvoice.sale_date.desc(), SalesInvoice.id.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()
