from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.excel import (
    clean_amount,
    map_columns,
    read_tabular_file,
    require_columns,
)
from app.models.accounting_expense import AccountingExpense
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["Upload"])

COLUMN_MAP = {
    "کد": "code",
    "عنوان": "title",
    "گردش بدهکار": "debit_turnover",
    "گردش بستانکار": "credit_turnover",
    "مانده بدهکار": "debit_balance",
    "مانده بستانکار": "credit_balance",
}

REQUIRED = ["code", "title"]


def _text(value) -> str | None:
    """مقدار متنی تمیزشده یا None اگر خالی/NaN باشد."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


@router.post("/expense-report")
async def upload_expense_report(
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

            # ردیف‌های جمع‌کل و ردیف‌های خالی عمداً نادیده گرفته می‌شوند
            if code is None or title is None:
                skipped += 1
                continue

            db.add(
                AccountingExpense(
                    code=code,
                    title=title,
                    debit_turnover=clean_amount(row.get("debit_turnover")),
                    credit_turnover=clean_amount(row.get("credit_turnover")),
                    debit_balance=clean_amount(row.get("debit_balance")),
                    credit_balance=clean_amount(row.get("credit_balance")),
                )
            )
            created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"ردیف {idx + 2}: {exc}")

    await db.commit()

    return {
        "message": "آپلود گزارش هزینه انجام شد",
        "created": created,
        "skipped": skipped,
        "errors": errors[:30],
    }