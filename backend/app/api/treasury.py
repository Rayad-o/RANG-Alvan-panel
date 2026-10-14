"""لیست داده‌های خزانه‌داری و دفتر حساب‌ها برای نماهای داشبورد."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.accounting_expense import AccountingExpense
from app.models.treasury import BankAccount, PaymentLog, Receipt, TreasuryCheck
from app.models.user import User

router = APIRouter(tags=["Treasury"])


def _num(value) -> Optional[str]:
    """Numeric به str تا سریال‌ساز JSON شناور اعشاری ندهد (مثل لیست انبار)."""
    return None if value is None else str(value)


def _like(query: Optional[str]) -> Optional[str]:
    return f"%{query.strip()}%" if query and query.strip() else None


@router.get("/banks/")
async def list_banks(
    q: Optional[str] = Query(None, description="جستجو در کد یا عنوان حساب"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(BankAccount)
    like = _like(q)
    if like:
        stmt = stmt.where(or_(BankAccount.code.ilike(like), BankAccount.title.ilike(like)))
    rows = (
        await db.execute(stmt.order_by(BankAccount.balance.desc(), BankAccount.id).limit(limit).offset(offset))
    ).scalars().all()
    return [
        {
            "id": b.id,
            "code": b.code,
            "title": b.title,
            "opening_balance": _num(b.opening_balance),
            "receipts": _num(b.receipts),
            "payments": _num(b.payments),
            "balance": _num(b.balance),
        }
        for b in rows
    ]


@router.get("/checks/")
async def list_checks(
    direction: Optional[str] = Query(None, description="received یا payable"),
    status: Optional[str] = Query(None, description="وضعیت چک (slug یا متن دلخواه)"),
    q: Optional[str] = Query(None, description="جستجو در طرف مقابل، شماره چک یا بانک"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(TreasuryCheck)
    if direction in ("received", "payable"):
        stmt = stmt.where(TreasuryCheck.direction == direction)
    if status:
        stmt = stmt.where(TreasuryCheck.status == status)
    like = _like(q)
    if like:
        stmt = stmt.where(
            or_(
                TreasuryCheck.counterparty.ilike(like),
                TreasuryCheck.check_no.ilike(like),
                TreasuryCheck.announce_no.ilike(like),
                TreasuryCheck.bank.ilike(like),
                TreasuryCheck.owner.ilike(like),
            )
        )
    rows = (
        await db.execute(
            stmt.order_by(TreasuryCheck.due_date.desc().nulls_last(), TreasuryCheck.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return [
        {
            "id": c.id,
            "direction": c.direction,
            "status": c.status,
            "code": c.code,
            "counterparty": c.counterparty,
            "amount": _num(c.amount),
            "due_date": c.due_date,
            "check_no": c.check_no,
            "announce_no": c.announce_no,
            "announce_date": c.announce_date,
            "value_date": c.value_date,
            "deposit_date": c.deposit_date,
            "protest_date": c.protest_date,
            "check_type": c.check_type,
            "bank": c.bank,
            "owner": c.owner,
            "description": c.description,
        }
        for c in rows
    ]


@router.get("/receipts/")
async def list_receipts(
    kind: Optional[str] = Query(None, description="نوع دریافت"),
    q: Optional[str] = Query(None, description="جستجو در طرف مقابل یا شرح"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Receipt)
    if kind:
        stmt = stmt.where(Receipt.kind == kind)
    like = _like(q)
    if like:
        stmt = stmt.where(or_(Receipt.counterparty.ilike(like), Receipt.description.ilike(like)))
    rows = (
        await db.execute(
            stmt.order_by(Receipt.date.desc().nulls_last(), Receipt.id.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return [
        {
            "id": r.id,
            "kind": r.kind,
            "counterparty": r.counterparty,
            "ref_no": r.ref_no,
            "date": r.date,
            "amount": _num(r.amount),
            "description": r.description,
        }
        for r in rows
    ]


@router.get("/payment-log/")
async def list_payment_log(
    kind: Optional[str] = Query(None, description="نوع پرداخت"),
    q: Optional[str] = Query(None, description="جستجو در طرف مقابل یا شرح"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(PaymentLog)
    if kind:
        stmt = stmt.where(PaymentLog.kind == kind)
    like = _like(q)
    if like:
        stmt = stmt.where(or_(PaymentLog.counterparty.ilike(like), PaymentLog.description.ilike(like)))
    rows = (
        await db.execute(
            stmt.order_by(PaymentLog.date.desc().nulls_last(), PaymentLog.id.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return [
        {
            "id": p.id,
            "kind": p.kind,
            "counterparty": p.counterparty,
            "ref_no": p.ref_no,
            "date": p.date,
            "item": p.item,
            "amount": _num(p.amount),
            "description": p.description,
        }
        for p in rows
    ]


@router.get("/expenses/")
async def list_expenses(
    q: Optional[str] = Query(None, description="جستجو در کد یا عنوان سرفصل"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """دفتر حساب‌ها: خروجی آپلود «گزارش هزینه» (مرور تأمین‌کنندگان و سایر ح پ)."""
    stmt = select(AccountingExpense)
    like = _like(q)
    if like:
        stmt = stmt.where(or_(AccountingExpense.code.ilike(like), AccountingExpense.title.ilike(like)))
    rows = (
        await db.execute(stmt.order_by(AccountingExpense.id.desc()).limit(limit).offset(offset))
    ).scalars().all()
    return [
        {
            "id": e.id,
            "code": e.code,
            "title": e.title,
            "debit_turnover": _num(e.debit_turnover),
            "credit_turnover": _num(e.credit_turnover),
            "debit_balance": _num(e.debit_balance),
            "credit_balance": _num(e.credit_balance),
            "period_label": e.period_label,
        }
        for e in rows
    ]
