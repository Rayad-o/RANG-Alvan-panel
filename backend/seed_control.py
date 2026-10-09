"""داده‌های نمونهٔ ماژول کنترل (تأمین‌کننده، پرداخت، فاکتور خرید، وظایف).

توسط seed_example.py فراخوانی می‌شود. امتیاز ریسک پرداخت‌ها با موتور واقعی
(app/services/risk.py) محاسبه می‌شود، نه عدد ثابت.
"""

from __future__ import annotations

import json
import random
from datetime import timedelta
from decimal import Decimal

from app.api.purchase_invoices import match_status
from app.core.timeutil import utcnow
from app.models import ActivityLog, PaymentRequest, PurchaseInvoice, Supplier, Task
from app.services.risk import score_payment
from app.services.settings import DEFAULTS, required_role

# (نام، دسته، حساب، پرریسک؟)
SUPPLIERS = [
    ("شرکت پارس‌مواد", "مواد اولیه", "IR********3812", True),
    ("پتروشیمی آریا", "مواد پایه", "IR********9217", False),
    ("رنگین‌مواد", "مواد اولیه", "IR********4550", False),
    ("سپهر شیمی", "خدمات", "IR********1198", False),
    ("شیمی‌نو", "لجستیک", "IR********7731", False),
    ("بسته‌بندی سبز", "بسته‌بندی", "IR********2264", False),
]

# (چند روز پیش، ساعت، تأمین‌کننده، مبلغ (میلیون)، شرح، سفارش، وضعیت نهایی)
PAYMENTS = [
    (45, 10, 0, 280, "خرید رزین", None, "approved"),
    (30, 11, 0, 320, "خرید رزین", None, "approved"),
    (15, 9, 0, 360, "خرید رزین", "PO-5690", "approved"),
    (40, 10, 1, 520, "مواد پایه", None, "approved"),
    (22, 14, 1, 1140, "مواد پایه", "PO-5660", "approved"),
    (9, 13, 1, 540, "مواد پایه", "PO-5718", "approved"),
    (38, 9, 2, 400, "مواد اولیه", None, "approved"),
    (20, 15, 2, 450, "مواد اولیه", "PO-5655", "approved"),
    (8, 10, 2, 380, "مواد اولیه", "PO-5702", "approved"),
    (25, 11, 3, 95, "خدمات آزمایشگاه", None, "approved"),
    (11, 12, 3, 110, "خدمات آزمایشگاه", None, "approved"),
    (28, 10, 4, 80, "حمل و لجستیک", None, "approved"),
    (12, 16, 4, 90, "حمل و لجستیک", None, "approved"),
    (6, 12, 4, 96, "حمل و لجستیک", None, "approved"),
    (14, 9, 5, 60, "بسته‌بندی", None, "approved"),
    (5, 10, 5, 64, "بسته‌بندی", None, "approved"),
    # روزهای اخیر
    (4, 11, 1, 610, "مواد پایه", None, "approved"),
    (3, 14, 3, 100, "خدمات آزمایشگاه", None, "approved"),
    (3, 16, 2, 410, "مواد اولیه", None, "approved"),
    (2, 10, 4, 98, "حمل و لجستیک", None, "approved"),
    (2, 15, 1, 450, "مواد پایه", None, "approved"),
    (1, 9, 0, 340, "خرید رزین", None, "approved"),
    (1, 16, 2, 280, "تجهیزات کارخانه", None, "stopped"),
    # امروز
    (0, 0, 3, 105, "خدمات آزمایشگاه", None, "approved"),
    (0, 0, 1, 320, "خرید رزین پایه", None, "approved"),
    (0, 0, 5, 62, "بسته‌بندی", None, "pending"),
    (0, 0, 0, 870, "پرداخت مواد اولیه", "PO-5721", "pending"),
    (0, 0, 2, 880, "پرداخت مواد اولیه", "PO-5702", "pending"),
    (0, 0, 4, 96, "حمل و لجستیک", None, "pending"),
]

# (شماره، تأمین‌کننده، سفارش، سفارش‌شده، رسیدشده، فاکتورشده، مبلغ (میلیون))
PURCHASE_INVOICES = [
    ("8231", 0, "PO-5721", 500, 500, 580, 870),
    ("8228", 1, "PO-5718", 1200, 1200, 1200, 1140),
    ("8219", 2, "PO-5702", 820, 820, 820, 490),
    ("8204", 3, "PO-5688", 300, 300, 305, 210),
    ("8199", 0, "PO-5690", 360, 360, 360, 360),
    ("8190", 4, "PO-5680", 100, 100, 100, 96),
    ("8184", 5, "PO-5675", 200, 190, 190, 64),
    ("8176", 2, "PO-5660", 450, 450, 450, 450),
    ("8170", 1, "PO-5655", 600, 600, 600, 520),
    ("8165", 4, "PO-5650", 90, 90, 110, 90),
]

# (واحد، وظیفه، مسئول، اولویت، سررسید نسبت به الان (ساعت)، تکمیل‌شده؟)
TASKS = [
    ("حسابداری", "ثبت ۱۲ فاکتور خرید", "رضا کاظمی", "critical", -48, False),
    ("خرید", "تکمیل سفارش مواد اولیه", "نگار فرهادی", "high", -24, False),
    ("انبار", "تأیید رسید کالا", "امیر نادری", "high", -8, False),
    ("فروش", "پیگیری چک‌های برگشتی", "سارا احمدی", "high", -30, False),
    ("حسابداری", "تطبیق صورت‌حساب بانکی", "رضا کاظمی", "medium", -5, False),
    ("فروش", "ثبت وضعیت سفارش مشتری", "علی رضایی", "medium", 4, False),
    ("منابع انسانی", "تکمیل پرونده ۳ نفر", "مریم صالحی", "medium", 6, False),
    ("انبار", "شمارش دوره‌ای موجودی", "امیر نادری", "medium", 30, False),
    ("خرید", "استعلام قیمت تینر", "نگار فرهادی", "low", 52, False),
    ("حسابداری", "بستن حساب‌های ماه قبل", "رضا کاظمی", "high", -72, True),
    ("فروش", "ارسال پیش‌فاکتور به مشتریان", "علی رضایی", "medium", -40, True),
    ("انبار", "تحویل کالا به حمل‌ونقل", "امیر نادری", "medium", -20, True),
    ("خرید", "بررسی قرارداد تأمین‌کنندگان", "نگار فرهادی", "low", -10, True),
    ("منابع انسانی", "مرخصی‌های هفته", "مریم صالحی", "low", -3, True),
]

ACTIVITY = [
    (200, "رضا کاظمی", "bank_changed", "supplier", "رنگین‌مواد"),
    (150, "سارا احمدی", "payment_approved", "payment", "شیمی‌نو"),
    (90, "علی رضایی", "task_completed", "task", "ارسال پیش‌فاکتور به مشتریان"),
    (45, "رضا کاظمی", "invoice_created", "invoice", "8231 • شرکت پارس‌مواد • mismatch"),
]


async def seed_control(session, rng: random.Random) -> dict:
    now = utcnow()
    cfg = DEFAULTS

    suppliers = [
        Supplier(code=f"SUP-{1021 + i * 13}", name=name, category=category, bank_account=bank, is_high_risk=risky)
        for i, (name, category, bank, risky) in enumerate(SUPPLIERS)
    ]
    # تغییر حساب بانکی امروز برای «رنگین‌مواد» که هنوز تأیید نشده است
    suppliers[2].bank_changed_at = now - timedelta(hours=8)
    suppliers[2].bank_changed_by = "واحد حسابداری"
    suppliers[2].bank_verified = False
    session.add_all(suppliers)
    await session.flush()

    # فاکتورهای خرید (قبل از پرداخت‌ها، چون امتیاز ریسک به آن‌ها نگاه می‌کند)
    for k, (number, si, po, ordered, received, invoiced, amount) in enumerate(PURCHASE_INVOICES):
        session.add(
            PurchaseInvoice(
                number=number,
                supplier_id=suppliers[si].id,
                supplier_name=suppliers[si].name,
                po_number=po,
                ordered_qty=Decimal(ordered),
                received_qty=Decimal(received),
                invoiced_qty=Decimal(invoiced),
                unit="kg",
                amount=Decimal(amount * 1_000_000),
                status=match_status(
                    Decimal(received), Decimal(invoiced), cfg["match_tolerance_pct"], cfg["controls"]["three_way_match"]
                ),
                created_at=now - timedelta(days=k * 2, hours=2),
            )
        )
    await session.flush()

    # پرداخت‌ها به ترتیب زمانی، با امتیاز ریسک واقعی
    schedule = []
    for days_ago, hour, si, mil, desc, po, final in PAYMENTS:
        if days_ago == 0:  # امروز: زمان‌ها نسبت به الان پخش می‌شوند تا در آینده نباشند
            created = now - timedelta(minutes=rng.randint(20, 400))
        else:
            created = (now - timedelta(days=days_ago)).replace(hour=hour, minute=rng.randint(0, 59))
        schedule.append((created, si, mil, desc, po, final))
    schedule.sort(key=lambda x: x[0])

    for created, si, mil, desc, po, final in schedule:
        supplier = suppliers[si]
        payment = PaymentRequest(
            supplier_id=supplier.id,
            party_name=supplier.name,
            description=desc,
            po_ref=po,
            amount=Decimal(mil * 1_000_000),
            created_by=rng.choice(["رضا کاظمی", "سارا احمدی"]),
            created_at=created,
        )
        session.add(payment)
        await session.flush()
        score, reasons = await score_payment(session, supplier, payment, cfg)
        payment.risk_score = score
        payment.risk_reasons = json.dumps(reasons, ensure_ascii=False)
        payment.ref = f"#{4400 + payment.id}"
        if final != "pending":
            payment.status = final
            payment.decided_by = "مدیر سیستم" if required_role(payment.amount, cfg, score) == "admin" else "سارا احمدی"
            payment.decided_at = created + timedelta(hours=2)
            if final == "stopped":
                payment.decision_note = "مغایرت با سفارش خرید؛ منتظر توضیح تأمین‌کننده"

    for unit, title, owner, priority, due_h, done in TASKS:
        session.add(
            Task(
                unit=unit, title=title, owner=owner, priority=priority,
                due_at=now + timedelta(hours=due_h),
                status="done" if done else "open",
                completed_at=(now + timedelta(hours=due_h - 2)) if done else None,
            )
        )

    for minutes_ago, actor, action, entity, detail in ACTIVITY:
        session.add(
            ActivityLog(created_at=now - timedelta(minutes=minutes_ago), actor=actor, action=action, entity=entity, detail=detail)
        )

    return {
        "suppliers": len(SUPPLIERS), "payments": len(PAYMENTS),
        "invoices": len(PURCHASE_INVOICES), "tasks": len(TASKS),
    }
