"""موتور امتیازدهی ریسک پرداخت.

قواعد ساده و قابل‌توضیح هستند (نه جعبه‌سیاه): هر امتیاز با یک دلیل فارسی همراه است
و فقط ناهنجاری را نشان می‌دهد؛ تصمیم نهایی با انسان است.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.control import PaymentRequest, PurchaseInvoice, Supplier


async def score_payment(
    db: AsyncSession, supplier: Supplier, payment: PaymentRequest, cfg: dict
) -> tuple[int, list[str]]:
    controls = cfg["controls"]
    if not controls.get("risk_score", True):
        return 0, []

    score = 0
    reasons: list[str] = []
    as_of = payment.created_at
    amount = float(payment.amount)

    # ۱) ناهنجاری مبلغ نسبت به سابقهٔ پرداخت به همین تأمین‌کننده (۹۰ روز)
    avg, count = (
        await db.execute(
            select(func.avg(PaymentRequest.amount), func.count(PaymentRequest.id)).where(
                PaymentRequest.supplier_id == supplier.id,
                PaymentRequest.id != payment.id,
                PaymentRequest.status != "stopped",
                PaymentRequest.created_at <= as_of,
                PaymentRequest.created_at >= as_of - timedelta(days=90),
            )
        )
    ).one()
    if not count:
        score += 15
        reasons.append("تأمین‌کننده سابقهٔ پرداخت قبلی ندارد")
    else:
        ratio = amount / float(avg) if avg else 0
        if ratio > 2:
            score += 40
            reasons.append(f"مبلغ {round((ratio - 1) * 100)}٪ بالاتر از میانگین پرداخت‌های قبلی")
        elif ratio > 1.5:
            score += 20
            reasons.append(f"مبلغ {round((ratio - 1) * 100)}٪ بالاتر از میانگین پرداخت‌های قبلی")

    # ۲) تأمین‌کنندهٔ پرریسک
    if supplier.is_high_risk:
        score += 20
        reasons.append("تأمین‌کننده در فهرست پرریسک است")

    # ۳) تغییر تأییدنشدهٔ حساب بانکی
    if (
        controls.get("bank_change_alert", True)
        and supplier.bank_changed_at
        and not supplier.bank_verified
        and as_of - timedelta(days=14) <= supplier.bank_changed_at <= as_of
    ):
        score += 25
        reasons.append("حساب بانکی تأمین‌کننده اخیراً تغییر کرده و تأیید نشده است")

    # ۴) پرداخت تکراری (همان تأمین‌کننده و همان مبلغ در ۷ روز)
    if controls.get("duplicate_detection", True):
        dup = (
            await db.execute(
                select(func.count(PaymentRequest.id)).where(
                    PaymentRequest.supplier_id == supplier.id,
                    PaymentRequest.amount == payment.amount,
                    PaymentRequest.id != payment.id,
                    PaymentRequest.created_at <= as_of,
                    PaymentRequest.created_at >= as_of - timedelta(days=7),
                )
            )
        ).scalar_one()
        if dup:
            score += 30
            reasons.append("پرداخت مشابه (همین مبلغ و تأمین‌کننده) در ۷ روز اخیر ثبت شده است")

    # ۵) تطبیق با فاکتور سفارش
    if controls.get("three_way_match", True) and payment.po_ref:
        statuses = (
            await db.execute(select(PurchaseInvoice.status).where(PurchaseInvoice.po_number == payment.po_ref))
        ).scalars().all()
        if not statuses:
            score += 10
            reasons.append(f"برای سفارش {payment.po_ref} فاکتوری ثبت نشده است")
        elif "mismatch" in statuses:
            score += 20
            reasons.append(f"فاکتور سفارش {payment.po_ref} با رسید انبار مغایرت دارد")

    return min(score, 100), reasons
