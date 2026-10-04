from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from io import BytesIO

from app.core.database import get_db
from app.models.finance import FinanceTransaction
from app.api.upload import normalize_persian, read_ms_xml_spreadsheet, clean_amount

router = APIRouter(prefix="/upload", tags=["Upload"])


async def _read_uploaded_table(file: UploadFile) -> pd.DataFrame:
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
    return df


@router.post("/receivables-excel")
async def upload_receivables_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    df = await _read_uploaded_table(file)

    column_map = {
        "کد": "code",
        "عنوان": "party_name",
        "مانده": "amount",
    }
    rename_dict = {col: column_map[col] for col in df.columns if col in column_map}
    df = df.rename(columns=rename_dict)

    required_cols = ["party_name", "amount"]
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
            party_name = row.get("party_name")
            if pd.isna(party_name) or str(party_name).strip() == "":
                continue

            code = row.get("code")
            description = f"کد: {code}" if pd.notna(code) else None

            item = FinanceTransaction(
                type="receivable",
                amount=clean_amount(row.get("amount")),
                transaction_date=None,
                party_name=str(party_name).strip(),
                description=description,
            )
            db.add(item)
            created += 1
        except Exception as e:
            errors.append(f"ردیف {idx + 2}: {str(e)}")

    await db.commit()

    return {
        "message": "آپلود حساب‌های دریافتنی انجام شد",
        "created": created,
        "errors": errors[:30],
    }


@router.post("/payables-excel")
async def upload_payables_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    df = await _read_uploaded_table(file)

    column_map = {
        "کد": "code",
        "عنوان": "party_name",
        "مانده بستانکار": "amount",
    }
    rename_dict = {col: column_map[col] for col in df.columns if col in column_map}
    df = df.rename(columns=rename_dict)

    required_cols = ["party_name", "amount"]
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
            party_name = row.get("party_name")
            if pd.isna(party_name) or str(party_name).strip() == "":
                continue

            code = row.get("code")
            description = f"کد: {code}" if pd.notna(code) else None

            item = FinanceTransaction(
                type="payable",
                amount=clean_amount(row.get("amount")),
                transaction_date=None,
                party_name=str(party_name).strip(),
                description=description,
            )
            db.add(item)
            created += 1
        except Exception as e:
            errors.append(f"ردیف {idx + 2}: {str(e)}")

    await db.commit()

    return {
        "message": "آپلود مانده بستانکاری انجام شد",
        "created": created,
        "errors": errors[:30],
    }