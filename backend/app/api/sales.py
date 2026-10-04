from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(SalesInvoice).order_by(SalesInvoice.sale_date.desc()))
    return result.scalars().all()
