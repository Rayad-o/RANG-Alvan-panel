import re
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.finance import FinanceTransaction
from app.models.inventory import InventoryItem
from app.models.sales import SalesInvoice
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

_JALALI_DATE = re.compile(r"^\d{4}/\d{2}/\d{2}$")


def _num(value) -> float:
    return float(value or Decimal("0"))


@router.get("/summary")
async def summary(
    today: str | None = Query(None, description="تاریخ شمسی امروز به شکل YYYY/MM/DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """همهٔ آمار داشبورد با چند کوئری تجمیعی (به‌جای دانلود کل جدول‌ها در مرورگر)."""
    if today is not None and not _JALALI_DATE.match(today):
        raise HTTPException(status_code=400, detail="قالب تاریخ باید YYYY/MM/DD باشد")

    sales_total, sales_count, remaining_total, unpaid_count = (
        await db.execute(
            select(
                func.coalesce(func.sum(SalesInvoice.amount), 0),
                func.count(SalesInvoice.id),
                func.coalesce(func.sum(SalesInvoice.remaining_amount), 0),
                func.coalesce(
                    func.sum(case((SalesInvoice.remaining_amount > 0, 1), else_=0)), 0
                ),
            )
        )
    ).one()

    today_sales = 0.0
    if today:
        today_sales = _num(
            (
                await db.execute(
                    select(func.coalesce(func.sum(SalesInvoice.amount), 0)).where(
                        SalesInvoice.sale_date == today
                    )
                )
            ).scalar_one()
        )

    ledger = {
        row.type: (_num(row.total), row.count)
        for row in (
            await db.execute(
                select(
                    FinanceTransaction.type,
                    func.coalesce(func.sum(FinanceTransaction.amount), 0).label("total"),
                    func.count(FinanceTransaction.id).label("count"),
                ).group_by(FinanceTransaction.type)
            )
        ).all()
    }

    followups = (
        await db.execute(
            select(func.count(FinanceTransaction.id)).where(FinanceTransaction.needs_followup.is_(True))
        )
    ).scalar_one()

    inventory_items = (await db.execute(select(func.count(InventoryItem.id)))).scalar_one()

    month = func.substr(SalesInvoice.sale_date, 1, 7)
    monthly_rows = (
        await db.execute(
            select(month.label("month"), func.sum(SalesInvoice.amount).label("total"))
            .group_by(month)
            .order_by(month.desc())
            .limit(6)
        )
    ).all()
    monthly = [{"month": r.month, "total": _num(r.total)} for r in reversed(monthly_rows)]

    top_rows = (
        await db.execute(
            select(SalesInvoice.customer_name, func.sum(SalesInvoice.amount).label("total"))
            .where(SalesInvoice.customer_name.is_not(None))
            .group_by(SalesInvoice.customer_name)
            .order_by(func.sum(SalesInvoice.amount).desc())
            .limit(5)
        )
    ).all()

    recent = (
        await db.execute(
            select(SalesInvoice).order_by(SalesInvoice.sale_date.desc(), SalesInvoice.id.desc()).limit(8)
        )
    ).scalars().all()

    return {
        "today_sales": today_sales,
        "sales_total": _num(sales_total),
        "sales_count": sales_count,
        "unpaid_invoices": int(unpaid_count or 0),
        "unpaid_amount": _num(remaining_total),
        "receivables": ledger.get("receivable", (0.0, 0))[0],
        "payables": ledger.get("payable", (0.0, 0))[0],
        "followups": followups,
        "inventory_items": inventory_items,
        "monthly_sales": monthly,
        "top_customers": [{"name": r.customer_name, "total": _num(r.total)} for r in top_rows],
        "recent_sales": [
            {
                "id": s.id,
                "invoice_number": s.invoice_number,
                "customer_name": s.customer_name,
                "amount": _num(s.amount),
                "remaining_amount": _num(s.remaining_amount),
                "sale_date": s.sale_date,
            }
            for s in recent
        ],
    }


# ---------------------------------------------------------------------------
# داشبورد کنترل و ریسک
# ---------------------------------------------------------------------------
import json  # noqa: E402
from datetime import timedelta  # noqa: E402

from app.core.timeutil import local_date_of, local_day_start_utc, local_today, utcnow  # noqa: E402
from app.models.control import ActivityLog, PaymentRequest, PurchaseInvoice, Supplier, Task  # noqa: E402
from app.services.settings import get_settings  # noqa: E402

WEEKDAYS_FA = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]  # بر اساس date.weekday()


@router.get("/control")
async def control_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = await get_settings(db)
    high = cfg["high_risk_threshold"]
    now = utcnow()
    today = local_today()
    t0 = local_day_start_utc(today)
    y0 = local_day_start_utc(today - timedelta(days=1))
    week0 = local_day_start_utc(today - timedelta(days=6))

    async def total(*conds) -> float:
        return _num((await db.execute(select(func.coalesce(func.sum(PaymentRequest.amount), 0)).where(*conds))).scalar_one())

    today_total = await total(PaymentRequest.created_at >= t0, PaymentRequest.status != "stopped")
    yesterday_total = await total(
        PaymentRequest.created_at >= y0, PaymentRequest.created_at < t0, PaymentRequest.status != "stopped"
    )
    change_pct = round((today_total - yesterday_total) / yesterday_total * 100) if yesterday_total else None

    stopped_count, stopped_amount = (
        await db.execute(
            select(func.count(PaymentRequest.id), func.coalesce(func.sum(PaymentRequest.amount), 0)).where(
                PaymentRequest.status == "stopped"
            )
        )
    ).one()
    pending_count, pending_amount = (
        await db.execute(
            select(func.count(PaymentRequest.id), func.coalesce(func.sum(PaymentRequest.amount), 0)).where(
                PaymentRequest.status == "pending"
            )
        )
    ).one()

    # جریان پرداخت ۷ روز (تجمیع در پایتون با منطقهٔ زمانی محلی)
    week_rows = (
        await db.execute(
            select(PaymentRequest.created_at, PaymentRequest.amount).where(
                PaymentRequest.created_at >= week0, PaymentRequest.status != "stopped"
            )
        )
    ).all()
    per_day: dict = {today - timedelta(days=i): 0.0 for i in range(6, -1, -1)}
    for created_at, amount in week_rows:
        day = local_date_of(created_at)
        if day in per_day:
            per_day[day] += float(amount)
    payments_7d = [
        {"date": d.isoformat(), "label": WEEKDAYS_FA[d.weekday()], "total": v} for d, v in per_day.items()
    ]

    # وظایف
    open_tasks = (await db.execute(select(Task).where(Task.status == "open"))).scalars().all()
    overdue = [t for t in open_tasks if t.due_at < now]
    critical_overdue = [t for t in overdue if t.priority == "critical"]
    done_count = (await db.execute(select(func.count(Task.id)).where(Task.status == "done"))).scalar_one()
    on_time_pct = round(done_count / (done_count + len(overdue)) * 100) if (done_count + len(overdue)) else 100

    # کانون‌های تمرکز
    high_pending = (
        await db.execute(
            select(PaymentRequest)
            .where(PaymentRequest.status == "pending", PaymentRequest.risk_score >= high)
            .order_by(PaymentRequest.risk_score.desc())
        )
    ).scalars().all()
    mismatches = (
        await db.execute(select(PurchaseInvoice).where(PurchaseInvoice.status == "mismatch"))
    ).scalars().all()
    bank_pending = (
        await db.execute(
            select(Supplier).where(Supplier.bank_verified.is_(False), Supplier.bank_changed_at.is_not(None))
        )
    ).scalars().all()

    # هشدارها
    alerts: list[dict] = []
    for p in high_pending:
        reasons = json.loads(p.risk_reasons or "[]")
        alerts.append({
            "level": "red", "icon": "🔴", "badge": "ریسک بالا", "link": "payments",
            "title": f"پرداخت پرریسک — {p.party_name}",
            "detail": f"{float(p.amount):,.0f} • امتیاز {p.risk_score}" + (f" • {reasons[0]}" if reasons else ""),
        })
    if cfg["controls"]["bank_change_alert"]:
        for s in bank_pending:
            alerts.append({
                "level": "red", "icon": "🏦", "badge": "تأیید لازم", "link": "suppliers",
                "title": "تغییر اطلاعات بانکی تأمین‌کننده",
                "detail": f"{s.name} • تغییر توسط {s.bank_changed_by or 'نامشخص'}",
            })
    for inv in mismatches:
        diff = abs(float(inv.received_qty) - float(inv.invoiced_qty))
        alerts.append({
            "level": "orange", "icon": "📦", "badge": "بررسی", "link": "purchase",
            "title": "مغایرت فاکتور با رسید انبار",
            "detail": f"فاکتور {inv.number} • {inv.supplier_name} • اختلاف {diff:g} {inv.unit}",
        })
    if cfg["controls"]["task_escalation"]:
        for t in critical_overdue:
            alerts.append({
                "level": "orange", "icon": "⏱", "badge": "عقب‌افتاده", "link": "tasks",
                "title": f"وظیفهٔ بحرانی عقب‌افتاده — {t.unit}",
                "detail": f"{t.title} • مسئول: {t.owner}",
            })

    # امتیاز سلامت کنترل
    penalty = len(high_pending) * 6 + len(mismatches) * 3 + len(bank_pending) * 5
    penalty += sum(4 if t.priority == "critical" else 2 for t in overdue)
    health = max(0, min(100, 100 - penalty))

    top_risks = [
        {
            "id": p.id, "ref": p.ref, "party_name": p.party_name, "risk_score": p.risk_score,
            "reasons": json.loads(p.risk_reasons or "[]"),
        }
        for p in (
            await db.execute(
                select(PaymentRequest)
                .where(PaymentRequest.status == "pending")
                .order_by(PaymentRequest.risk_score.desc(), PaymentRequest.id.desc())
                .limit(2)
            )
        ).scalars().all()
    ]

    activity = (
        await db.execute(select(ActivityLog).order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(8))
    ).scalars().all()

    return {
        "payments_today": today_total,
        "payments_change_pct": change_pct,
        "stopped_count": stopped_count,
        "stopped_amount": _num(stopped_amount),
        "pending_count": pending_count,
        "pending_amount": _num(pending_amount),
        "overdue_tasks": len(overdue),
        "critical_overdue": len(critical_overdue),
        "health_score": health,
        "alerts": alerts[:6],
        "alerts_total": len(alerts),
        "top_risks": top_risks,
        "payments_7d": payments_7d,
        "task_performance": {"done": done_count, "overdue": len(overdue), "open": len(open_tasks), "on_time_pct": on_time_pct},
        "focus": {
            "high_risk_payments": len(high_pending),
            "invoice_mismatches": len(mismatches),
            "sensitive_changes": len(bank_pending),
            "late_staff": len({t.owner for t in overdue}),
        },
        "recent_activity": [
            {
                "at": (a.created_at.isoformat() + "Z"), "actor": a.actor, "action": a.action, "detail": a.detail,
            }
            for a in activity
        ],
    }
