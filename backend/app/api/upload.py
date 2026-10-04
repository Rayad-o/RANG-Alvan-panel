from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
import pandas as pd
import xml.etree.ElementTree as ET
from io import BytesIO

from app.core.database import get_db
from app.models.sales import SalesInvoice

router = APIRouter(prefix="/upload", tags=["Upload"])


def clean_amount(value):
    if pd.isna(value):
        return Decimal("0")
    text = str(value).strip().replace(",", "").replace("،", "")
    try:
        return Decimal(text)
    except Exception:
        return Decimal("0")


def normalize_persian(text: str) -> str:
    """تبدیل حروف عربی به معادل فارسی‌شان برای مقایسه‌ی درست نام ستون‌ها."""
    return (
        text.replace("ي", "ی")  # ي عربی -> ی فارسی
            .replace("ك", "ک")  # ك عربی -> ک فارسی
    )


def read_ms_xml_spreadsheet(content: bytes) -> pd.DataFrame:
    """خواندن فایل‌های SpreadsheetML (XML اکسل ۲۰۰۳) که بعضی نرم‌افزارها با پسوند .xls تولید می‌کنند."""
    ns = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}
    root = ET.fromstring(content)
    worksheet = root.find("ss:Worksheet", ns)
    table = worksheet.find("ss:Table", ns)
    rows = table.findall("ss:Row", ns)

    data = []
    for row in rows:
        cells = row.findall("ss:Cell", ns)
        values = []
        for cell in cells:
            data_el = cell.find("ss:Data", ns)
            values.append(data_el.text if data_el is not None else None)
        data.append(values)

    if not data:
        raise ValueError("جدولی در فایل پیدا نشد")

    header_idx = 0
    for i, r in enumerate(data):
        non_empty = [v for v in r if v not in (None, "")]
        if len(non_empty) > 1:
            header_idx = i
            break

    header = data[header_idx]
    body = data[header_idx + 1:]

    width = len(header)
    body = [r + [None] * (width - len(r)) for r in body]
    body = [r[:width] for r in body]

    return pd.DataFrame(body, columns=header)


@router.post("/sales-excel")
async def upload_sales_excel(
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
                # calamine هم .xls و هم .xlsx واقعی را پشتیبانی می‌کند
                df = pd.read_excel(BytesIO(content), engine="calamine")
            except Exception:
                try:
                    # بعضی نرم‌افزارها خروجی .xls می‌دهند که در واقع XML اکسل ۲۰۰۳ است
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
        "نوع تسویه": "settlement_type",
        "تاریخ": "sale_date",
        "نام مشتری": "customer_name",
        "خالص": "amount",
        "باقی مانده فاکتور": "remaining_amount",
        "باقی‌مانده فاکتور": "remaining_amount",
    }

    rename_dict = {}
    for col in df.columns:
        if col in column_map:
            rename_dict[col] = column_map[col]

    df = df.rename(columns=rename_dict)

    required_cols = ["sale_date", "customer_name", "amount"]
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
            customer = row.get("customer_name")
            if pd.isna(customer) or str(customer).strip() == "":
                continue

            amount = clean_amount(row.get("amount"))
            remaining = (
                clean_amount(row.get("remaining_amount"))
                if "remaining_amount" in df.columns
                else Decimal("0")
            )

            if amount <= 0:
                continue

            status = "pending" if remaining > 0 else "completed"

            settlement = row.get("settlement_type")
            description = None
            if pd.notna(settlement):
                description = f"نوع تسویه: {settlement}"

            item = SalesInvoice(
                customer_name=str(customer).strip(),
                amount=amount,
                remaining_amount=remaining,
                sale_date=str(row.get("sale_date")).strip(),
                status=status,
                description=description,
            )
            db.add(item)
            created += 1
        except Exception as e:
            errors.append(f"ردیف {idx + 2}: {str(e)}")

    await db.commit()

    return {
        "message": "آپلود فاکتور فروش انجام شد",
        "created": created,
        "errors": errors[:30],
    }
