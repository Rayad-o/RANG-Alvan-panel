from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from decimal import Decimal
import pandas as pd
from io import BytesIO

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.inventory import InventoryItem
from app.api.upload import normalize_persian, read_ms_xml_spreadsheet, clean_amount

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post("/upload")
async def upload_inventory(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="فایل ارسال نشده است")

    filename = file.filename.lower()
    if not filename.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="فقط فایل Excel یا CSV مجاز است")

    content = await file.read()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(BytesIO(content))
        else:
            try:
                df = pd.read_excel(BytesIO(content), engine="calamine")
            except Exception:
                try:
                    df = read_ms_xml_spreadsheet(content)
                except Exception:
                    tables = pd.read_html(BytesIO(content))
                    if not tables:
                        raise ValueError("جدولی در فایل پیدا نشد")
                    df = tables[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"خواندن فایل ناموفق بود: {str(e)}")

    df.columns = [normalize_persian(str(c).strip()) for c in df.columns]

    column_map = {
        "کد کالا": "code",
        "عنوان کالا": "title",
        "موجودی": "quantity",
    }
    rename_dict = {col: column_map[col] for col in df.columns if col in column_map}
    df = df.rename(columns=rename_dict)

    required_cols = ["code", "title", "quantity"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"ستون‌های ضروری یافت نشد: {missing}. ستون‌های فایل: {list(df.columns)}"
        )

    created = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            code = row.get("code")
            title = row.get("title")
            if pd.isna(code) or str(code).strip() == "" or pd.isna(title):
                continue

            item = InventoryItem(
                code=str(code).strip(),
                title=str(title).strip(),
                quantity=clean_amount(row.get("quantity")),
            )
            db.add(item)
            created += 1
        except Exception as e:
            errors.append(f"ردیف {idx + 2}: {str(e)}")

    await db.commit()

    return {
        "message": "آپلود موجودی انبار انجام شد",
        "created": created,
        "errors": errors[:30],
    }


@router.get("/")
async def list_inventory(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(InventoryItem).order_by(InventoryItem.title))
    items = result.scalars().all()
    return [
        {
            "id": i.id,
            "code": i.code,
            "title": i.title,
            "quantity": str(i.quantity),
        }
        for i in items
    ]
