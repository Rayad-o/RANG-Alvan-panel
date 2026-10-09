from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.excel import (
    clean_amount,
    map_columns,
    read_tabular_file,
    require_columns,
)
from app.models.inventory import InventoryItem
from app.models.user import User

router = APIRouter(prefix="/inventory", tags=["Inventory"])

COLUMN_MAP = {
    "کد کالا": "code",
    "عنوان کالا": "title",
    "موجودی": "quantity",
    # نام‌های رایج دیگر
    "کد": "code",
    "عنوان": "title",
    "تعداد": "quantity",
}

REQUIRED = ["code", "title", "quantity"]


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


@router.post("/upload")
async def upload_inventory(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = map_columns(await read_tabular_file(file), COLUMN_MAP)
    require_columns(df, REQUIRED)

    created = 0
    skipped = 0
    errors: list[str] = []

    for idx, row in df.iterrows():
        try:
            code = _text(row.get("code"))
            title = _text(row.get("title"))
            if code is None or title is None:
                skipped += 1
                continue

            db.add(
                InventoryItem(
                    code=code,
                    title=title,
                    quantity=clean_amount(row.get("quantity")),
                )
            )
            created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"ردیف {idx + 2}: {exc}")

    await db.commit()

    return {
        "message": "آپلود موجودی انبار انجام شد",
        "created": created,
        "skipped": skipped,
        "errors": errors[:30],
    }


@router.get("/")
async def list_inventory(
    q: str | None = Query(None, description="جستجو در کد یا عنوان کالا"),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(InventoryItem)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(InventoryItem.code.ilike(like), InventoryItem.title.ilike(like)))
    result = await db.execute(stmt.order_by(InventoryItem.title).limit(limit).offset(offset))
    items = result.scalars().all()
    return [
        {
            "id": i.id,
            "code": i.code,
            "title": i.title,
            # Numeric به str تبدیل می‌شود تا سریال‌ساز JSON شناور اعشاری ندهند
            "quantity": None if i.quantity is None else str(i.quantity),
        }
        for i in items
    ]