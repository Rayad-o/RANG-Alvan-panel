from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.finance import FinanceTransaction
from app.schemas.finance import FinanceTransactionCreate, FinanceTransactionOut

router = APIRouter(prefix="/finance", tags=["Finance"])

@router.post("/", response_model=FinanceTransactionOut)
async def create_finance(
    data: FinanceTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = FinanceTransaction(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.get("/", response_model=list[FinanceTransactionOut])
async def list_finance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(FinanceTransaction).order_by(FinanceTransaction.transaction_date.desc()))
    return result.scalars().all()
