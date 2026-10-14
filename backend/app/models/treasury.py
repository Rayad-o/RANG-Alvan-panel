from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, func
from app.core.database import Base


class BankAccount(Base):
    """مرور بانک‌ها: دریافت و پرداخت هر حساب بانکی در دوره."""

    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    opening_balance = Column(Numeric(18, 2), nullable=False, default=0)  # اول دوره
    receipts = Column(Numeric(18, 2), nullable=False, default=0)  # دریافت‌ها
    payments = Column(Numeric(18, 2), nullable=False, default=0)  # پرداخت‌ها
    balance = Column(Numeric(18, 2), nullable=False, default=0)  # مانده
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TreasuryCheck(Base):
    """چک‌های دریافتی و پرداختنی (هر چهار گزارش چک)."""

    __tablename__ = "treasury_checks"

    id = Column(Integer, primary_key=True, index=True)
    # received = دریافتی، payable = پرداختنی
    direction = Column(String(20), nullable=False, default="received", index=True)
    # وضعیت به شکل slug: deposited / spent / cleared / pending؛ متن دلخواه هم مجاز است
    status = Column(String(50), nullable=False, default="pending", index=True)
    code = Column(String(20), nullable=True)  # تفصیلی
    counterparty = Column(String(255), nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    due_date = Column(String(10), nullable=True)  # تاریخ سررسید (شمسی)
    check_no = Column(String(30), nullable=True)  # شماره چک
    announce_no = Column(String(30), nullable=True)  # شماره اعلامیه
    announce_date = Column(String(10), nullable=True)  # تاریخ اعلامیه
    value_date = Column(String(10), nullable=True)  # تاریخ وصول
    deposit_date = Column(String(10), nullable=True)  # تاریخ رسید (چک‌های دریافتی)
    protest_date = Column(String(10), nullable=True)  # تاریخ وصول/واخواست
    check_type = Column(String(100), nullable=True)  # نوع
    bank = Column(String(255), nullable=True)  # حساب بانکی / بانک
    owner = Column(String(255), nullable=True)  # صاحب چک
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Receipt(Base):
    """دریافت‌ها به تفکیک نوع و تاریخ."""

    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(100), nullable=True)  # نوع دریافت
    counterparty = Column(String(255), nullable=False, index=True)
    ref_no = Column(String(30), nullable=True)  # شماره سند
    date = Column(String(10), nullable=True)  # تاریخ شمسی
    amount = Column(Numeric(18, 2), nullable=False, default=0)  # مبلغ دریافت
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PaymentLog(Base):
    """دفتر پرداخت روزانه به تفکیک نوع و روز."""

    __tablename__ = "payment_logs"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(100), nullable=True)  # نوع پرداخت
    counterparty = Column(String(255), nullable=False, index=True)
    ref_no = Column(String(30), nullable=True)  # شماره سند
    date = Column(String(10), nullable=True)  # تاریخ شمسی
    item = Column(String(100), nullable=True)  # اقلام (حواله، چک، ...)
    amount = Column(Numeric(18, 2), nullable=False, default=0)  # مبلغ پرداخت
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
