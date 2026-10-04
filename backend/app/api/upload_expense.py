from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from io import BytesIO

from app.core.database import get_db
from app.models.accounting_expense import AccountingExpense
from app.api.upload import normalize_persian, read_ms_xml_spreadsheet, clean_amount

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/expense-report")
async def upload_expense_report(
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
        "کد": "code",
        "عنوان": "title",
        "گردش بدهکار": "debit_turnover",
        "گردش بستانکار": "credit_turnover",
        "مانده بدهکار": "debit_balance",
        "مانده بستانکار": "credit_balance",
    }

    rename_dict = {col: column_map[col] for col in df.columns if col in column_map}
    df = df.rename(columns=rename_dict)

    required_cols = ["code", "title"]
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
                continue  # رد کردن ردیف جمع‌کل یا ردیف خالی

            item = AccountingExpense(
                code=str(code).strip(),
                title=str(title).strip(),
                debit_turnover=clean_amount(row.get("debit_turnover")),
                credit_turnover=clean_amount(row.get("credit_turnover")),
                debit_balance=clean_amount(row.get("debit_balance")),
                credit_balance=clean_amount(row.get("credit_balance")),
            )
            db.add(item)
            created += 1
        except Exception as e:
            errors.append(f"ردیف {idx + 2}: {str(e)}")

    await db.commit()

    return {
        "message": "آپلود گزارش هزینه انجام شد",
        "created": created,
        "errors": errors[:30],
    }
