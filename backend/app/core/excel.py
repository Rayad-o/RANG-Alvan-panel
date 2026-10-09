"""خواندن فایل‌های اکسل/CSV و پاک‌سازی مقادیر.

این ماژول جایگزین چهار کپی-پیست یکسان از منطق خواندن فایل شده است.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Optional

import pandas as pd
from fastapi import HTTPException, UploadFile

ALLOWED_SUFFIXES = (".xlsx", ".xls", ".xlsm", ".csv")

SS_NS = "urn:schemas-microsoft-com:office:spreadsheet"
_SS = {"ss": SS_NS}

ZERO = Decimal("0")

# ارقام فارسی/عربی → ارقام لاتین
_DIGIT_MAP: dict[int, str] = {}
for _digits in ("۰۱۲۳۴۵۶۷۸۹", "٠١٢٣٤٥٦٧٨٩"):
    for _i, _ch in enumerate(_digits):
        _DIGIT_MAP[ord(_ch)] = str(_i)

# جداکننده‌های عددی فارسی/عربی
_STRIP_CHARS = str.maketrans(
    {
        ",": "",  # جداکننده هزارگان لاتین
        "٬": "",  # جداکننده هزارگان عربی
        "،": "",  # کامای عربی
        " ": "",
        "\u00a0": "",  # فاصله غیرقابل شکستن
        "\u200c": "",  # نیم‌فاصله
    }
)


class FileReadError(Exception):
    """خطای خواندن فایل ورودی."""


# ---------------------------------------------------------------------------
# پاک‌سازی متن
# ---------------------------------------------------------------------------
def normalize_persian(text: str) -> str:
    """تبدیل حروف عربی به معادل فارسی و یکسان‌سازی فاصله‌ها برای مقایسه نام ستون‌ها."""
    return (
        text.replace("ي", "ی")  # ي عربی -> ی فارسی
        .replace("ك", "ک")  # ك عربی -> ک فارسی
        .replace("\u200c", " ")  # نیم‌فاصله
        .replace("\u00a0", " ")
        .strip()
    )


def _is_na(value) -> bool:
    if value is None:
        return True
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(result) if isinstance(result, (bool,)) else False


def clean_amount(value) -> Decimal:
    """تبدیل مقدار خام اکسل به Decimal.

    ارقام فارسی/عربی، جداکننده هزارگان، اعشار فارسی و اعداد حسابداری
    منفی مثل ``(1,234)`` و ``1234-`` را مدیریت می‌کند.
    مقدار نامعتبر به‌جای خطا دادن، صفر برمی‌گرداند (رفتار قبلی).
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return ZERO
    if _is_na(value):
        return ZERO

    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))

    text = str(value).strip()
    if not text:
        return ZERO

    text = text.translate(_DIGIT_MAP).translate(_STRIP_CHARS)
    text = text.replace("٫", ".").replace("،", ".")

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    if text.endswith("-"):
        negative = True
        text = text[:-1]
    if text.startswith("-"):
        negative = True
        text = text[1:]
    if text.startswith("+"):
        text = text[1:]

    text = re.sub(r"[^\d.]", "", text)
    if not text or text == ".":
        return ZERO

    try:
        result = Decimal(text)
    except (InvalidOperation, ValueError):
        return ZERO

    return -result if negative else result


def clean_jalali_date(value) -> Optional[str]:
    """تاریخ شمسی را به قالب ثابت ``YYYY/MM/DD`` تبدیل می‌کند.

    ورودی‌های رایج: ``1405/7/2``، ``1405-07-02``، ``14050702`` (عدد اکسل)
    و ارقام فارسی. اگر تاریخ قابل تشخیص نباشد ``None`` برمی‌گرداند.
    """
    if isinstance(value, bool) or value is None or _is_na(value):
        return None

    if isinstance(value, int):
        digits = f"{value:08d}"
    elif isinstance(value, float):
        if value != int(value):
            return None
        digits = f"{int(value):08d}"
    else:
        text = str(value).translate(_DIGIT_MAP).strip()
        # تاریخ دارای جداکننده (۱۴۰۵/۷/۳ یا 1405-7-3): اجزا را جدا بخوان تا ماه/روز تک‌رقمی درست شوند
        parts = [p for p in re.split(r"\D+", text) if p]
        if len(parts) >= 3 and len(parts[0]) == 4:
            digits = f"{parts[0]}{parts[1].zfill(2)}{parts[2][:2].zfill(2)}"
        else:
            digits = "".join(parts)

    if len(digits) < 8:
        return None

    year, month, day = digits[:4], digits[4:6], digits[6:8]
    if not (year.isdigit() and month.isdigit() and day.isdigit()):
        return None

    year, month, day = int(year), int(month), int(day)

    # سال شمسی امروز حدود ۱۴۰۴ است؛ اعداد بزرگ‌تر یعنی تاریخ میلادی
    # که بدون کتابخانه تبدیل نمی‌شود. به‌جای ذخیره داده غلط، None برمی‌گردانیم.
    if not (1200 <= year <= 1600):
        return None
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None

    return f"{year:04d}/{month:02d}/{day:02d}"


# ---------------------------------------------------------------------------
# خواندن SpreadsheetML (XML اکسل ۲۰۰۳)
# ---------------------------------------------------------------------------
def read_ms_xml_spreadsheet(content: bytes) -> pd.DataFrame:
    """خواندن فایل‌های SpreadsheetML که بعضی نرم‌افزارها با پسوند .xls تولید می‌کنند.

    نکته مهم: در این قالب، صفت ``ss:Index`` یعنی «این سلول در ستون چندم قرار دارد».
    نادیده‌گرفتن آن (کاری که نسخه قبلی می‌کرد) باعث می‌شد ستون‌های دارای سلول
    خالی یا ادغام‌شده به‌هم بریزند و داده‌ها جابه‌جا ذخیره شوند.
    """
    root = ET.fromstring(content)

    table = None
    for worksheet in root.findall(".//ss:Worksheet", _SS):
        table = worksheet.find("ss:Table", _SS)
        if table is not None:
            break
    if table is None:
        raise FileReadError("جدولی در فایل پیدا نشد")

    data: list[list[Optional[str]]] = []
    for row in table.findall("ss:Row", _SS):
        values: list[Optional[str]] = []
        column = 0
        for cell in row.findall("ss:Cell", _SS):
            raw_index = cell.get(f"{{{SS_NS}}}Index")
            if raw_index is not None:
                try:
                    column = int(raw_index) - 1
                except ValueError:
                    column = len(values)
            # پر کردن سلول‌های جاافتاده تا ستون‌ها هم‌تراز بمانند
            while len(values) < column:
                values.append(None)
            data_el = cell.find("ss:Data", _SS)
            values.append(data_el.text if data_el is not None else None)
            column += 1
        data.append(values)

    if not data:
        raise FileReadError("جدولی در فایل پیدا نشد")

    # سطر هدر: اولین سطری که بیش از یک سلول پر دارد
    header_idx = 0
    for i, row in enumerate(data):
        if len([v for v in row if v not in (None, "")]) > 1:
            header_idx = i
            break

    header = [str(v).strip() if v is not None else f"ستون{i + 1}"
              for i, v in enumerate(data[header_idx])]
    width = len(header)
    body = [(r + [None] * width)[:width] for r in data[header_idx + 1:]]

    return pd.DataFrame(body, columns=header)


# ---------------------------------------------------------------------------
# خواندن فایل
# ---------------------------------------------------------------------------
def _excel_engines() -> list[str]:
    """لیست موتورهای خواندن xlsx به ترتیب اولویت، فقط برای موتورهای نصب‌شده."""
    engines = []
    # calamine هم xlsx و هم xls واقعی (BIFF) را می‌خواند، ولی بستهٔ جداگانه است
    try:
        import python_calamine  # noqa: F401

        engines.append("calamine")
    except ImportError:
        pass
    engines.append("openpyxl")
    engines.append("xlrd")  # فقط برای xls واقعی
    return engines


def _read_excel(content: bytes) -> pd.DataFrame:
    errors = []

    # ۱) موتورهای استاندارد اکسل
    for engine in _excel_engines():
        try:
            return pd.read_excel(BytesIO(content), engine=engine)
        except ImportError:
            continue  # این موتور نصب نیست
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{engine}: {exc}")

    # ۲) SpreadsheetML (XML اکسل ۲۰۰۳)
    try:
        return read_ms_xml_spreadsheet(content)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"xml: {exc}")

    # ۳) جدول HTML (بعضی خروجی‌های تحت وب)
    try:
        tables = pd.read_html(BytesIO(content))
        if tables:
            return tables[0]
        errors.append("html: جدولی در فایل پیدا نشد")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"html: {exc}")

    raise FileReadError("؛ ".join(errors) or "خواندن فایل ناموفق بود")


async def read_tabular_file(file: UploadFile) -> pd.DataFrame:
    """خواندن فایل اکسل/CSV آپلودشده و برگرداندن DataFrame با نام ستون‌های یکسان‌شده."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="فایل ارسال نشده است")

    filename = file.filename.lower()
    if not filename.endswith(ALLOWED_SUFFIXES):
        raise HTTPException(
            status_code=400,
            detail="فقط فایل Excel یا CSV مجاز است",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="فایل خالی است")

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(BytesIO(content))
        else:
            df = _read_excel(content)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"خواندن فایل ناموفق بود: {exc}")

    df.columns = [normalize_persian(str(c)) for c in df.columns]
    return df


def map_columns(df: pd.DataFrame, column_map: dict[str, str]) -> pd.DataFrame:
    """تغییر نام ستون‌های موجود طبق نگاشت داده‌شده (ستون‌های ناشناخته دست‌نخورده می‌مانند)."""
    rename = {col: column_map[col] for col in df.columns if col in column_map}
    return df.rename(columns=rename)


def require_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                f"ستون‌های ضروری یافت نشد: {missing}. "
                f"ستون‌های فایل: {list(df.columns)}"
            ),
        )