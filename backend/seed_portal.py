"""داده‌های نمونهٔ پنل خریدار و کارگران (بخش‌ها، بدهی‌ها، درخواست‌های خرید).

توسط seed_example.py فراخوانی می‌شود. حساب‌های نمونه (فقط برای تست):
    buyer@example.com        / buyer1234    خریدار (بدهی کم → می‌تواند درخواست بدهد)
    buyer2@example.com       / buyer1234    خریدار (بدهی بالای ۲۰ میلیون → ثبت درخواست ممنوع)
    accountant@example.com   / acc1234      حسابدار
    head@example.com         / head1234     رییس بخش «تولید رنگ»
    worker@example.com       / worker1234   کارکن بخش «تولید رنگ»
    worker2@example.com      / worker1234   کارکن بخش «تولید رنگ»
    store@example.com        / store1234    رییس بخش «انبار و ارسال»
    store-worker@example.com / worker1234   کارکن بخش «انبار و ارسال»
"""

from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.future import select

from app.core.security import hash_password
from app.core.timeutil import local_today, utcnow
from app.models import (
    BuyerDebt,
    DebtPayment,
    Department,
    InventoryItem,
    PurchaseRequest,
    PurchaseRequestItem,
    RequestEvent,
    User,
)
from app.models.user import UserRole

DEPARTMENTS = ["تولید رنگ", "انبار و ارسال", "بسته‌بندی"]

# (ایمیل، نام، رمز، نقش، بخش)
PORTAL_USERS = [
    ("accountant@example.com", "لیلا نوری", "acc1234", UserRole.accountant, None),
    ("head@example.com", "کاوه مرادی", "head1234", UserRole.dept_head, "تولید رنگ"),
    ("worker@example.com", "امید رستمی", "worker1234", UserRole.dept_staff, "تولید رنگ"),
    ("worker2@example.com", "سحر قنبری", "worker1234", UserRole.dept_staff, "تولید رنگ"),
    ("store@example.com", "بهرام یزدانی", "store1234", UserRole.dept_head, "انبار و ارسال"),
    ("store-worker@example.com", "نیما عباسی", "worker1234", UserRole.dept_staff, "انبار و ارسال"),
    ("buyer@example.com", "شرکت ساختمانی آرمان", "buyer1234", UserRole.buyer, None),
    ("buyer2@example.com", "فروشگاه رنگ نگین", "buyer1234", UserRole.buyer, None),
]


async def seed_portal(session, rng: random.Random) -> dict:
    now = utcnow()
    today = local_today()

    session.add_all(Department(name=n) for n in DEPARTMENTS)
    users: dict[str, User] = {}
    for email, name, password, role, dept in PORTAL_USERS:
        u = User(email=email, full_name=name, hashed_password=hash_password(password), role=role, department=dept)
        users[email] = u
        session.add(u)
    await session.flush()

    buyer, buyer2 = users["buyer@example.com"], users["buyer2@example.com"]
    accountant = users["accountant@example.com"]

    # ---- بدهی‌ها ----
    def debt(b, amount, desc, due_days, paid=0, status="open", ago_days=0):
        d = BuyerDebt(
            buyer_id=b.id, amount=Decimal(amount), paid_amount=Decimal(paid), description=desc,
            due_date=today + timedelta(days=due_days), status=status, created_by=accountant.full_name,
            created_at=now - timedelta(days=ago_days),
        )
        session.add(d)
        return d

    d_paid = debt(buyer, 12_000_000, "فاکتور ۱۰۱۸ — رنگ پلاستیک", -20, paid=12_000_000, status="paid", ago_days=40)
    d_a = debt(buyer, 5_000_000, "فاکتور ۱۰۲۴ — تینر و قلم‌مو", 10, ago_days=6)
    d_b = debt(buyer, 3_000_000, "فاکتور ۱۰۲۸ — آستری", 20, paid=1_000_000, ago_days=3)   # مانده ۲ میلیون
    d_c = debt(buyer2, 25_000_000, "فاکتور ۱۰۱۲ — رنگ روغنی (عمده)", -7, paid=5_000_000, ago_days=30)  # مانده ۲۰ میلیون
    d_d = debt(buyer2, 10_000_000, "فاکتور ۱۰۳۰ — ضدزنگ و تینر", 5, ago_days=4)
    await session.flush()

    for d, amount, days_ago in [(d_paid, 12_000_000, 25), (d_b, 1_000_000, 1), (d_c, 5_000_000, 12)]:
        session.add(DebtPayment(
            debt_id=d.id, amount=Decimal(amount), note="پرداخت نقدی", recorded_by=accountant.full_name,
            paid_at=now - timedelta(days=days_ago),
        ))
    # مانده خریدار: ۷ میلیون (مجاز) — خریدار۲: ۳۰ میلیون (> ۲۰ میلیون → ممنوع)

    # ---- درخواست‌های خرید ----
    products = (await session.execute(select(InventoryItem).order_by(InventoryItem.id))).scalars().all()
    pick = lambda n: rng.sample(products, n)

    head, worker, worker2 = users["head@example.com"], users["worker@example.com"], users["worker2@example.com"]

    # (خریدار، وضعیت، بخش، کارکن، چند ساعت پیش، یادداشت، رد)
    plans = [
        (buyer, "submitted", None, None, 2, "برای پروژهٔ ساختمانی خیابان گلستان", None),
        (buyer, "forwarded", "تولید رنگ", None, 20, "تحویل تا آخر هفته", None),
        (buyer, "assigned", "تولید رنگ", worker, 30, None, None),
        (buyer, "in_progress", "تولید رنگ", worker2, 52, "رنگ سفید طبق نمونهٔ قبلی", None),
        (buyer, "done", "تولید رنگ", worker, 120, None, None),
        (buyer2, "rejected", None, None, 200, None, "بدهی معوق خریدار؛ پس از تسویه دوباره درخواست دهید"),
        (buyer2, "done", "انبار و ارسال", users["store-worker@example.com"], 400, None, None),
    ]
    for b, status, dept, assignee, hours_ago, note, reject in plans:
        created = now - timedelta(hours=hours_ago)
        req = PurchaseRequest(
            buyer_id=b.id, note=note, status=status, department=dept,
            assigned_to_id=assignee.id if assignee else None, decision_note=reject,
            created_at=created, updated_at=created,
        )
        session.add(req)
        await session.flush()
        req.ref = f"RQ-{1000 + req.id}"
        for p in pick(rng.randint(1, 3)):
            session.add(PurchaseRequestItem(
                request_id=req.id, product_id=p.id, product_code=p.code, product_title=p.title,
                quantity=Decimal(rng.choice([5, 10, 20, 40])),
            ))

        def ev(hours_after, actor, action, text=None):
            session.add(RequestEvent(request_id=req.id, at=created + timedelta(hours=hours_after), actor=actor, action=action, note=text))

        ev(0, b.full_name, "created")
        if status == "rejected":
            ev(3, accountant.full_name, "rejected", reject)
            req.updated_at = created + timedelta(hours=3)
            continue
        if status == "submitted":
            continue
        ev(2, accountant.full_name, "forwarded", f"به بخش «{dept}»")
        if status == "forwarded":
            req.updated_at = created + timedelta(hours=2)
            continue
        head_user = users["store@example.com"] if dept == "انبار و ارسال" else head
        ev(5, head_user.full_name, "assigned", f"به {assignee.full_name}")
        if status == "assigned":
            req.updated_at = created + timedelta(hours=5)
            continue
        ev(8, assignee.full_name, "started")
        if status == "in_progress":
            req.updated_at = created + timedelta(hours=8)
            continue
        ev(30, assignee.full_name, "completed", "آماده تحویل")
        req.updated_at = created + timedelta(hours=30)

    return {"departments": len(DEPARTMENTS), "users": len(PORTAL_USERS), "debts": 5, "requests": len(plans)}
