from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.excel import (
    clean_amount,
    clean_jalali_date,
    map_columns,
    read_tabular_file,
    require_columns,
)
from app.models.sales import SalesInvoice
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["Upload"])

COLUMN_MAP = {
    "نوع تسویه": "settlement_type",
    "تاریخ": "sale_date",
    "نام مشتری": "customer_name",
    "خالص": "amount",
    "باقی مانده فاکتور": "remaining_amount",
    "باقی‌مانده فاکتور": "remaining_amount",
    "شماره فاکتور": "invoice_number",
}

REQUIRED = ["sale_date", "customer_name", "amount"]


@router.post("/sales-excel")
async def upload_sales_excel(
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
            customer = row.get("customer_name")
            if not str(customer or "").strip() or str(customer).lower() == "nan":
                skipped += 1
                continue

            amount = clean_amount(row.get("amount"))
            if amount <= 0:
                skipped += 1
                continue

            sale_date = clean_jalali_date(row.get("sale_date"))
            if sale_date is None:
                errors.append(
                    f"ردیف {idx + 2}: تاریخ «{row.get('sale_date')}» قابل خواندن نیست "
                    "(باید شمسی و به شکل ۱۴۰۵/۰۷/۰۲ باشد)"
                )
                continue

            remaining = (
                clean_amount(row.get("remaining_amount"))
                if "remaining_amount" in df.columns
                else Decimal("0")
            )

            settlement = row.get("settlement_type")
            description: Optional[str] = None
            if str(settlement or "").strip() and str(settlement).lower() != "nan":
                description = f"نوع تسویه: {str(settlement).strip()}"

            invoice_number = row.get("invoice_number")
            invoice_number = (
                str(invoice_number).strip()
                if str(invoice_number or "").strip() and str(invoice_number).lower() != "nan"
                else None
            )

            db.add(
                SalesInvoice(
                    invoice_number=invoice_number,
                    customer_name=str(customer).strip(),
                    amount=amount,
                    remaining_amount=remaining,
                    sale_date=sale_date,
                    status="pending" if remaining > 0 else "completed",
                    description=description,
                )
            )
            created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"ردیف {idx + 2}: {exc}")

    await db.commit()

    return {
        "message": "آپلود فاکتور فروش انجام شد",
        "created": created,
        "skipped": skipped,
        "errors": errors[:30],
    }