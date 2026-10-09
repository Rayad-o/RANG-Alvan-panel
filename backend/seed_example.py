"""ساخت دیتابیس نمونه (example.db) با داده‌های آزمایشی فارسی.

اجرا (از پوشهٔ backend):
    python seed_example.py                # ساخت/بازسازی example.db
    python seed_example.py --db sqlite+aiosqlite:///./other.db --force

این اسکریپت جدول‌های دیتابیس مقصد را پاک و دوباره می‌سازد؛ برای همین فقط روی
example.db بدون تأیید کار می‌کند و برای هر دیتابیس دیگری باید --force بدهید.

حساب‌های نمونه (فقط برای تست):
    admin@example.com   / admin1234   (مدیر سیستم)
    manager@example.com / manager1234 (مدیر)
    staff@example.com   / staff1234   (کارمند)
و حساب‌های پنل خریدار و کارگران (فهرست کامل در seed_portal.py):
    buyer@example.com / buyer1234 • accountant@example.com / acc1234 • head@example.com / head1234 • worker@example.com / worker1234
"""

from __future__ import annotations

import argparse
import asyncio
import random
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.security import hash_password
from app.models import (  # noqa: F401  (ثبت مدل‌ها روی Base)
    AccountingExpense,
    FinanceTransaction,
    InventoryItem,
    SalesInvoice,
    User,
)
from app.models.user import UserRole
from seed_control import seed_control
from seed_portal import seed_portal

DEFAULT_DB = "sqlite+aiosqlite:///./example.db"

USERS = [
    ("admin@example.com", "مدیر سیستم", "admin1234", UserRole.admin),
    ("manager@example.com", "سارا احمدی", "manager1234", UserRole.manager),
    ("staff@example.com", "علی رضایی", "staff1234", UserRole.staff),
]

CUSTOMERS = [
    "شرکت آلفا", "فروشگاه بهار", "رضا محمدی", "پخش سپهر", "نوین تجارت",
    "کیان صنعت", "بازرگانی آریا", "ساختمانی پارس", "فروشگاه گل‌رنگ", "حسین کریمی",
    "رنگ‌سازی نیکان", "دکوراسیون مهر",
]

SETTLEMENTS = ["نقد", "چک", "کارت‌خوان", "نسیه"]

PRODUCTS = [
    ("RN-101", "رنگ پلاستیک سفید ۴ لیتری", 240), ("RN-102", "رنگ پلاستیک کرم ۴ لیتری", 180),
    ("RN-103", "رنگ پلاستیک طوسی ۴ لیتری", 95), ("RN-104", "رنگ اکریلیک مشکی ۱ لیتری", 60),
    ("RN-201", "رنگ روغنی سفید ۱ لیتری", 130), ("RN-202", "رنگ روغنی قرمز ۱ لیتری", 12),
    ("RN-203", "رنگ روغنی آبی ۱ لیتری", 75), ("RN-301", "ضدزنگ خاکستری ۱ لیتری", 88),
    ("RN-302", "ضدزنگ قرمز ۱ لیتری", 8), ("TN-001", "تینر فوری ۱ لیتری", 320),
    ("TN-002", "تینر اکریلیک ۴ لیتری", 54), ("AS-010", "آستری دیوار ۴ لیتری", 160),
    ("AS-011", "آستری چوب ۱ لیتری", 41), ("BR-100", "قلم‌مو شماره ۲", 500),
    ("BR-101", "قلم‌مو شماره ۴", 420), ("BR-102", "قلم‌مو شماره ۶", 15),
    ("RL-200", "غلتک ۲۰ سانتی", 210), ("RL-201", "غلتک ۲۵ سانتی", 130),
    ("RL-202", "دسته غلتک", 0), ("ML-050", "ماله پلاستیکی", 76),
    ("CH-001", "چسب چوب ۱ کیلویی", 98), ("CH-002", "چسب آکواریوم", 33),
    ("ZG-010", "سمباده شمارهٔ ۱۲۰", 900), ("ZG-011", "سمباده شمارهٔ ۲۴۰", 0),
    ("PO-300", "پودر گچ ۱۰ کیلویی", 64),
]

EXPENSES = [
    ("6101", "حقوق و دستمزد"), ("6102", "اجارهٔ انبار"), ("6103", "برق و آب و گاز"),
    ("6104", "حمل و نقل"), ("6105", "تبلیغات"), ("6106", "تعمیر و نگهداری"),
    ("6107", "ملزومات اداری"), ("6108", "بیمه و مالیات"), ("6109", "هزینهٔ ارتباطات"),
    ("6110", "پذیرایی"),
]


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
        + gd + g_d_m[gm - 1]
    )
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def days_in_jalali_month(month: int) -> int:
    return 31 if month <= 6 else 30 if month <= 11 else 29


def build_sales(rng: random.Random, today: tuple[int, int, int]) -> list[SalesInvoice]:
    ty, tm, td = today
    invoices: list[SalesInvoice] = []
    number = 1000

    # شش ماه اخیر با روند صعودیِ نسبی؛ ماه جاری فقط تا امروز
    for back in range(5, -1, -1):
        month = tm - back
        year = ty
        while month < 1:
            month += 12
            year -= 1
        last_day = td if back == 0 else days_in_jalali_month(month)
        count = rng.randint(14, 20) if back else max(td // 2, 6)
        scale = 0.7 + (5 - back) * 0.12

        for _ in range(count):
            day = rng.randint(1, last_day)
            amount = int(rng.randint(8, 95) * 1_000_000 * scale / 5) // 100_000 * 100_000
            paid_in_full = rng.random() < 0.7
            remaining = 0 if paid_in_full else int(amount * rng.choice([0.2, 0.3, 0.5, 1.0]))
            number += 1
            invoices.append(
                SalesInvoice(
                    invoice_number=str(number),
                    customer_name=rng.choice(CUSTOMERS),
                    amount=Decimal(amount),
                    remaining_amount=Decimal(remaining),
                    sale_date=f"{year:04d}/{month:02d}/{day:02d}",
                    status="completed" if remaining == 0 else "pending",
                    description=f"نوع تسویه: {rng.choice(SETTLEMENTS)}",
                )
            )

    # چند فاکتور برای «امروز» تا کارت فروش امروز مقدار داشته باشد
    for _ in range(3):
        number += 1
        amount = rng.randint(10, 60) * 1_000_000
        invoices.append(
            SalesInvoice(
                invoice_number=str(number),
                customer_name=rng.choice(CUSTOMERS),
                amount=Decimal(amount),
                remaining_amount=Decimal(0),
                sale_date=f"{ty:04d}/{tm:02d}/{td:02d}",
                status="completed",
                description="نوع تسویه: نقد",
            )
        )
    return invoices


def build_finance(rng: random.Random) -> list[FinanceTransaction]:
    rows = []
    for i, name in enumerate(rng.sample(CUSTOMERS, 9)):
        rows.append(
            FinanceTransaction(
                type="receivable",
                amount=Decimal(rng.randint(5, 120) * 1_000_000),
                party_name=name,
                description=f"کد: {2000 + i}",
                needs_followup=rng.random() < 0.3,
            )
        )
    suppliers = ["پتروشیمی شازند", "تأمین‌کنندهٔ رزین پارس", "بسته‌بندی سبز", "حمل‌ونقل سریع", "شیمی‌صنعت کاسپین", "مواد اولیهٔ تهران"]
    for i, name in enumerate(suppliers):
        rows.append(
            FinanceTransaction(
                type="payable",
                amount=Decimal(rng.randint(10, 200) * 1_000_000),
                party_name=name,
                description=f"کد: {3000 + i}",
                needs_followup=rng.random() < 0.2,
            )
        )
    return rows


def build_expenses(rng: random.Random, period: str) -> list[AccountingExpense]:
    rows = []
    for code, title in EXPENSES:
        debit = rng.randint(5, 80) * 1_000_000
        credit = rng.choice([0, 0, rng.randint(1, 5) * 1_000_000])
        rows.append(
            AccountingExpense(
                code=code,
                title=title,
                debit_turnover=Decimal(debit),
                credit_turnover=Decimal(credit),
                debit_balance=Decimal(max(debit - credit, 0)),
                credit_balance=Decimal(max(credit - debit, 0)),
                period_label=period,
            )
        )
    return rows


async def seed(db_url: str) -> None:
    engine = create_async_engine(
        db_url,
        connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {},
    )
    rng = random.Random(1405)  # دادهٔ تکرارپذیر

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    now = date.today()
    today = gregorian_to_jalali(now.year, now.month, now.day)
    sales = build_sales(rng, today)

    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        session.add_all(
            User(email=e, full_name=n, hashed_password=hash_password(p), role=r)
            for e, n, p, r in USERS
        )
        session.add_all(sales)
        session.add_all(build_finance(rng))
        session.add_all(build_expenses(rng, f"{today[0]}/{today[1]:02d}"))
        session.add_all(
            InventoryItem(code=c, title=t, quantity=Decimal(q)) for c, t, q in PRODUCTS
        )
        control_counts = await seed_control(session, rng)
        await session.flush()  # شناسهٔ کالاها برای درخواست‌های خرید لازم است
        portal_counts = await seed_portal(session, rng)
        await session.commit()

    await engine.dispose()
    print(f"[OK] دیتابیس نمونه ساخته شد: {db_url}")
    print(f"     تاریخ امروز (شمسی): {today[0]}/{today[1]:02d}/{today[2]:02d}")
    print(f"     کاربر: {len(USERS)} | فاکتور: {len(sales)} | کالا: {len(PRODUCTS)}")
    print(f"     کنترل: {control_counts}")
    print(f"     پنل خریدار/کارگران: {portal_counts}")
    print("     ورود: admin@example.com / admin1234")


def main() -> None:
    parser = argparse.ArgumentParser(description="ساخت دیتابیس نمونه")
    parser.add_argument("--db", default=DEFAULT_DB, help="آدرس دیتابیس (پیش‌فرض: example.db)")
    parser.add_argument("--force", action="store_true", help="اجازهٔ پاک‌کردن دیتابیسی غیر از example.db")
    args = parser.parse_args()

    if args.db != DEFAULT_DB and not args.force:
        parser.error("این اسکریپت جدول‌ها را پاک می‌کند؛ برای دیتابیس دیگر --force بدهید.")

    asyncio.run(seed(args.db))


if __name__ == "__main__":
    main()
