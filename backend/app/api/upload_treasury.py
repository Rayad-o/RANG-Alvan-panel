"""آپلود فایل‌های خزانه‌داری: بانک‌ها، چک‌ها، دریافت‌ها و دفتر پرداخت.

هر چهار endpoint از همان الگوی بقیهٔ آپلودها پیروی می‌کنند:
نگاشت سرستون (با نرمال‌سازی حروف عربی)، نادیده‌گرفتن سطرهای خالی/جمع‌کل
و پاسخ ``{created, skipped, errors}``.
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.excel import (
    clean_amount,
    clean_jalali_date,
    map_columns,
    normalize_persian,
    read_tabular_file,
    require_columns,
)
from app.models.treasury import BankAccount, PaymentLog, Receipt, TreasuryCheck
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["Upload"])


def _text(value) -> Optional[str]:
    """مقدار متنی تمیزشده یا None اگر خالی/NaN باشد."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _clean(value) -> Optional[str]:
    """مثل _text ولی حروف عربی (ي/ك) هم به فارسی تبدیل می‌شوند تا جستجوی فارسی کار کند."""
    text = _text(value)
    if text is None:
        return None
    return normalize_persian(text) or None


# ---------------------------------------------------------------------------
# بانک‌ها: «مرور بانک‌ها دریافت و پرداخت»
# ---------------------------------------------------------------------------
BANKS_COLUMN_MAP = {
    "کد تفصیلی": "code",
    "عنوان": "title",
    "اول دوره": "opening_balance",
    "دریافت ها": "receipts",
    "پرداخت ها": "payments",
    "مانده": "balance",
}

BANKS_REQUIRED = ["code", "title"]


@router.post("/banks-excel")
async def upload_banks_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = map_columns(await read_tabular_file(file), BANKS_COLUMN_MAP)
    require_columns(df, BANKS_REQUIRED)

    created = 0
    skipped = 0
    errors: list[str] = []

    for idx, row in df.iterrows():
        try:
            code = _clean(row.get("code"))
            title = _clean(row.get("title"))
            # سطرهای جمع‌کل و خالی عمداً نادیده گرفته می‌شوند
            if code is None or title is None:
                skipped += 1
                continue

            db.add(
                BankAccount(
                    code=code,
                    title=title,
                    opening_balance=clean_amount(row.get("opening_balance")),
                    receipts=clean_amount(row.get("receipts")),
                    payments=clean_amount(row.get("payments")),
                    balance=clean_amount(row.get("balance")),
                )
            )
            created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"ردیف {idx + 2}: {exc}")

    await db.commit()

    return {
        "message": "آپلود مرور بانک‌ها انجام شد",
        "created": created,
        "skipped": skipped,
        "errors": errors[:30],
    }


# ---------------------------------------------------------------------------
# چک‌ها: چهار گزارش چک (دریافتی/پرداختنی) در یک endpoint
# ---------------------------------------------------------------------------
CHECKS_COLUMN_MAP = {
    "تفصیلی": "code",
    "طرف مقابل": "counterparty",
    "مبلغ": "amount",
    "تاریخ سررسید": "due_date",
    "شماره": "check_no",
    "شماره اعلامیه": "announce_no",
    "تاریخ اعلامیه": "announce_date",
    "تاریخ وصول": "value_date",
    "تاریخ رسید": "deposit_date",
    "تاریخ وصول، واخواست": "protest_date",
    # نسخهٔ با کامای لاتین هم پذیرفته می‌شود
    "تاریخ وصول, واخواست": "protest_date",
    "حساب بانکی": "bank",
    "بانک": "bank",
    "وضعیت": "status_text",
    "نوع": "check_type",
    "صاحب چک": "owner",
    "شرح": "description",
}

CHECKS_REQUIRED = ["counterparty"]

# وضعیت‌های رایج گزارش‌های چک → slug برای نمایش برچسب در فرانت‌اند
STATUS_SLUGS = {
    "واگذار به بانک": "deposited",
    "واگذار به بانك": "deposited",
    "خرج شده": "spent",
    "پاس شده": "cleared",
}


def _status_slug(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return STATUS_SLUGS.get(text, text)


@router.post("/checks-excel")
async def upload_checks_excel(
    file: UploadFile = File(...),
    direction: Optional[str] = Query(
        None, description="received یا payable؛ پیش‌فرض تشخیص خودکار از روی سرستون‌ها"
    ),
    status: Optional[str] = Query(
        None, description="وضعیت همهٔ سطرها (مثلاً pending یاcleared)؛ پیش‌فرض از ستون وضعیت"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = map_columns(await read_tabular_file(file), CHECKS_COLUMN_MAP)
    require_columns(df, CHECKS_REQUIRED)

    # جهت چک: اگر پارامتر داده نشده باشد از سرستون‌های مخصوص چک‌های دریافتی
    # (وضعیت / تاریخ رسید) تشخیص داده می‌شود.
    direction = (direction or "").strip().lower()
    if direction in ("received", "payable"):
        explicit_direction: Optional[str] = direction
    else:
        explicit_direction = None
    auto_direction = (
        "received" if ("status_text" in df.columns or "deposit_date" in df.columns) else "payable"
    )

    created = 0
    skipped = 0
    errors: list[str] = []

    for idx, row in df.iterrows():
        try:
            counterparty = _clean(row.get("counterparty"))
            # سطر جمع‌کل/خلاصه: طرف مقابل خالی است
            if counterparty is None:
                skipped += 1
                continue

            row_direction = explicit_direction or auto_direction
            # پارامتر صریح برنده است؛ در غیر این صارت از ستون «وضعیت» و در نبود
            # هر دو، از جهت چک یک وضعیت پیش‌فرض ساخته می‌شود.
            row_status = status or _status_slug(_clean(row.get("status_text")))
            if not row_status:
                row_status = "pending" if row_direction == "payable" else "received"

            due_date = clean_jalali_date(row.get("due_date"))
            announce_date = clean_jalali_date(row.get("announce_date"))
            value_date = clean_jalali_date(row.get("value_date"))
            deposit_date = clean_jalali_date(row.get("deposit_date"))
            protest_date = clean_jalali_date(row.get("protest_date"))

            db.add(
                TreasuryCheck(
                    direction=row_direction,
                    status=row_status,
                    code=_clean(row.get("code")),
                    counterparty=counterparty,
                    amount=clean_amount(row.get("amount")),
                    due_date=due_date,
                    check_no=_clean(row.get("check_no")),
                    announce_no=_clean(row.get("announce_no")),
                    announce_date=announce_date,
                    value_date=value_date,
                    deposit_date=deposit_date,
                    protest_date=protest_date,
                    check_type=_clean(row.get("check_type")),
                    bank=_clean(row.get("bank")),
                    owner=_clean(row.get("owner")),
                    description=_clean(row.get("description")),
                )
            )
            created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"ردیف {idx + 2}: {exc}")

    await db.commit()

    return {
        "message": "آپلود گزارش چک‌ها انجام شد",
        "created": created,
        "skipped": skipped,
        "errors": errors[:30],
    }


# ---------------------------------------------------------------------------
# دریافت‌ها: «مرور دریافت به تفکیک نوع و تاریخ»
# ---------------------------------------------------------------------------
RECEIPTS_COLUMN_MAP = {
    "نوع دریافت": "kind",
    "طرف مقابل": "counterparty",
    "شماره": "ref_no",
    "تاریخ": "date",
    "مبلغ دریافت": "amount",
    "شرح": "description",
}

RECEIPTS_REQUIRED = ["counterparty", "amount"]


@router.post("/receipts-excel")
async def upload_receipts_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = map_columns(await read_tabular_file(file), RECEIPTS_COLUMN_MAP)
    require_columns(df, RECEIPTS_REQUIRED)

    created = 0
    skipped = 0
    errors: list[str] = []

    for idx, row in df.iterrows():
        try:
            counterparty = _clean(row.get("counterparty"))
            amount = clean_amount(row.get("amount"))
            if counterparty is None or amount == 0:
                skipped += 1  # سطر خالی یا جمع‌کل
                continue

            db.add(
                Receipt(
                    kind=_clean(row.get("kind")),
                    counterparty=counterparty,
                    ref_no=_clean(row.get("ref_no")),
                    date=clean_jalali_date(row.get("date")),
                    amount=amount,
                    description=_clean(row.get("description")),
                )
            )
            created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"ردیف {idx + 2}: {exc}")

    await db.commit()

    return {
        "message": "آپلود دریافت‌ها انجام شد",
        "created": created,
        "skipped": skipped,
        "errors": errors[:30],
    }


# ---------------------------------------------------------------------------
# دفتر پرداخت: «گزارش پرداخت به تفکیک نوع و روز»
# ---------------------------------------------------------------------------
PAYMENTS_COLUMN_MAP = {
    "نوع پرداخت": "kind",
    "طرف مقابل": "counterparty",
    "شماره": "ref_no",
    "تاریخ": "date",
    "اقلام": "item",
    "مبلغ پرداخت": "amount",
    "شرح": "description",
}

PAYMENTS_REQUIRED = ["counterparty", "amount"]


@router.post("/payments-excel")
async def upload_payments_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    df = map_columns(await read_tabular_file(file), PAYMENTS_COLUMN_MAP)
    require_columns(df, PAYMENTS_REQUIRED)

    created = 0
    skipped = 0
    errors: list[str] = []

    for idx, row in df.iterrows():
        try:
            counterparty = _clean(row.get("counterparty"))
            amount = clean_amount(row.get("amount"))
            if counterparty is None or amount == 0:
                skipped += 1
                continue

            # «اقلام» در فایل معمولاً «حواله،» با کامای انتهایی است
            item = _clean(row.get("item"))
            if item:
                item = item.rstrip(",").strip() or None

            db.add(
                PaymentLog(
                    kind=_clean(row.get("kind")),
                    counterparty=counterparty,
                    ref_no=_clean(row.get("ref_no")),
                    date=clean_jalali_date(row.get("date")),
                    item=item,
                    amount=amount,
                    description=_clean(row.get("description")),
                )
            )
            created += 1
        except Exception as exc:  # noqa: BLE001
            errors.append(f"ردیف {idx + 2}: {exc}")

    await db.commit()

    return {
        "message": "آپلود دفتر پرداخت انجام شد",
        "created": created,
        "skipped": skipped,
        "errors": errors[:30],
    }
