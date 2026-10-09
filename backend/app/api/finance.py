from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_
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
    type: str | None = Query(None, description="receivable یا payable"),
    q: str | None = Query(None, description="جستجو در نام طرف حساب یا توضیحات"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(FinanceTransaction)
    if type:
        stmt = stmt.where(FinanceTransaction.type == type)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(FinanceTransaction.party_name.ilike(like), FinanceTransaction.description.ilike(like)))
    stmt = stmt.order_by(FinanceTransaction.amount.desc(), FinanceTransaction.id.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()
