from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.excel import (
    clean_amount,
    map_columns,
    read_tabular_file,
    require_columns,
)
from app.models.finance import FinanceTransaction
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["Upload"])


def _text(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


async def _import_ledger(
    file: UploadFile,
    db: AsyncSession,
    amount_column: str,
    transaction_type: str,
    message: str,
) -> dict:
    """منطق مشترک آپلود دفتر حساب‌های دریافتنی/پرداختنی."""
    df = map_columns(await read_tabular_file(file), {"کد": "code", "عنوان": "party_name", amount_column: "amount"})
    require_columns(df, ["party_name", "amount"])

    created = 0
    skipped = 0
    errors: list[str] = []

    for idx, row in df.iterrows():
        try:
            party_name = _text(row.get("party_name"))
            if party_name is None:
                skipped += 1
                continue

            code = _text(row.get("code"))

            db.add(
                FinanceTransaction(
                    type=transaction_type,
                    amount=clean_amount(row.get("amount")),
                    # دفتر حساب‌ها تاریخ ندارد؛ None یعنی «تاریخ نامشخص»
                    transaction_date=None,
                    party_name=party_name,
                    description=f"کد: {code}" if code else None,
                )
            )
            created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"ردیف {idx + 2}: {exc}")

    await db.commit()

    return {"message": message, "created": created, "skipped": skipped, "errors": errors[:30]}


@router.post("/receivables-excel")
async def upload_receivables_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _import_ledger(
        file,
        db,
        amount_column="مانده",
        transaction_type="receivable",
        message="آپلود حساب‌های دریافتنی انجام شد",
    )


@router.post("/payables-excel")
async def upload_payables_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _import_ledger(
        file,
        db,
        amount_column="مانده بستانکار",
        transaction_type="payable",
        message="آپلود مانده بستانکاری انجام شد",
    )