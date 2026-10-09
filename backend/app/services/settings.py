import copy
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.control import AppSetting

ROLE_RANK = {"staff": 0, "manager": 1, "admin": 2}

DEFAULTS: dict = {
    # کلیدهای کنترل (قواعد هشدار)
    "controls": {
        "risk_score": True,          # امتیازدهی ریسک پرداخت
        "bank_change_alert": True,   # هشدار تغییر حساب بانکی تأمین‌کننده
        "duplicate_detection": True, # تشخیص پرداخت تکراری
        "three_way_match": True,     # تطبیق سفارش/رسید/فاکتور
        "task_escalation": True,     # هشدار وظایف عقب‌افتادهٔ بحرانی
    },
    # سقف تأیید: تا مبلغ upto (تومان) حداقل نقش تأییدکننده role است؛ upto=None یعنی بالاتر از همه
    "approval_tiers": [
        {"upto": 100_000_000, "role": "manager"},
        {"upto": 500_000_000, "role": "manager"},
        {"upto": 2_000_000_000, "role": "admin"},
        {"upto": None, "role": "admin"},
    ],
    # درصد اختلاف مجاز بین مقدار رسیدشده و فاکتورشده برای «نیازمند بررسی» (بیشتر از آن «مغایرت»)
    "match_tolerance_pct": 2,
    # از این امتیاز به بالا فقط admin می‌تواند تأیید کند
    "high_risk_threshold": 70,
    # خریداری که بدهی‌اش از این مبلغ (تومان) بیشتر باشد نمی‌تواند درخواست خرید ثبت کند
    "buyer_debt_limit": 20_000_000,
}


async def get_settings(db: AsyncSession) -> dict:
    result = copy.deepcopy(DEFAULTS)
    for row in (await db.execute(AppSetting.__table__.select())).all():
        try:
            stored = json.loads(row.value)
        except ValueError:
            continue
        if isinstance(result.get(row.key), dict) and isinstance(stored, dict):
            result[row.key].update(stored)
        else:
            result[row.key] = stored
    return result


async def save_settings(db: AsyncSession, values: dict) -> None:
    for key, value in values.items():
        row = await db.get(AppSetting, key)
        payload = json.dumps(value, ensure_ascii=False)
        if row is None:
            db.add(AppSetting(key=key, value=payload))
        else:
            row.value = payload


def required_role(amount, cfg: dict, risk_score: int = 0) -> str:
    """حداقل نقش لازم برای تأیید یک پرداخت (بر اساس مبلغ و امتیاز ریسک)."""
    role = "admin"
    for tier in cfg["approval_tiers"]:
        if tier["upto"] is None or float(amount) <= float(tier["upto"]):
            role = tier["role"]
            break
    if risk_score >= cfg["high_risk_threshold"]:
        role = "admin"
    return role


def role_allows(user_role: str, needed: str) -> bool:
    return ROLE_RANK.get(user_role, -1) >= ROLE_RANK.get(needed, 99)
