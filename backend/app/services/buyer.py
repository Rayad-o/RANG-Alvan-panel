from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.portal import BuyerDebt

# پیام دقیقی که طبق خواستهٔ کارفرما هنگام عبور بدهی از سقف نمایش داده می‌شود
DEBT_BLOCK_MESSAGE = "لطفا اول بدهی خود را پرداخت کنید"

OPEN_REQUEST_STATUSES = ("submitted", "forwarded", "assigned", "in_progress")


def _money(value) -> Decimal:
    return Decimal(str(round(float(value or 0), 2)))


async def buyer_debt_total(db: AsyncSession, buyer_id: int) -> Decimal:
    """جمع مانده بدهی‌های باز یک خریدار (تومان)."""
    total = (
        await db.execute(
            select(func.coalesce(func.sum(BuyerDebt.amount - BuyerDebt.paid_amount), 0)).where(
                BuyerDebt.buyer_id == buyer_id, BuyerDebt.status == "open"
            )
        )
    ).scalar_one()
    return _money(total)


async def debt_totals(db: AsyncSession) -> dict[int, Decimal]:
    """جمع بدهی باز هر خریدار (یک کوئری برای همه)."""
    rows = (
        await db.execute(
            select(BuyerDebt.buyer_id, func.sum(BuyerDebt.amount - BuyerDebt.paid_amount))
            .where(BuyerDebt.status == "open")
            .group_by(BuyerDebt.buyer_id)
        )
    ).all()
    return {buyer_id: _money(total) for buyer_id, total in rows}


def is_blocked(total: Decimal, limit) -> bool:
    """بدهی «بیشتر از» سقف مجاز یعنی ممنوع؛ دقیقاً برابر با سقف مجاز است."""
    return total > Decimal(str(limit))
