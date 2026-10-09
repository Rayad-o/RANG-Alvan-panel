"""مدل‌های پنل خریدار و کارگران: بخش‌ها، بدهی خریدار، درخواست خرید."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text

from app.core.database import Base
from app.core.timeutil import utcnow


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class BuyerDebt(Base):
    """یک ردیف بدهی که حسابدار برای خریدار ثبت می‌کند (مبالغ به تومان)."""

    __tablename__ = "buyer_debts"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    paid_amount = Column(Numeric(18, 2), nullable=False, default=0)
    description = Column(String(500), nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="open", index=True)  # open / paid / voided
    created_by = Column(String(100), nullable=True)
    void_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)


class DebtPayment(Base):
    __tablename__ = "debt_payments"

    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("buyer_debts.id"), nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    note = Column(String(500), nullable=True)
    recorded_by = Column(String(100), nullable=True)
    paid_at = Column(DateTime, default=utcnow, nullable=False)


class PurchaseRequest(Base):
    """درخواست خرید خریدار از کارخانهٔ رنگ."""

    __tablename__ = "purchase_requests"

    id = Column(Integer, primary_key=True, index=True)
    ref = Column(String(20), nullable=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    note = Column(String(1000), nullable=True)
    # submitted / forwarded / assigned / in_progress / done / rejected / cancelled
    status = Column(String(20), nullable=False, default="submitted", index=True)
    department = Column(String(100), nullable=True, index=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    decision_note = Column(Text, nullable=True)  # دلیل رد
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class PurchaseRequestItem(Base):
    __tablename__ = "purchase_request_items"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("purchase_requests.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=True)
    product_code = Column(String(100), nullable=False)
    product_title = Column(String(255), nullable=False)
    quantity = Column(Numeric(18, 3), nullable=False)


class RequestEvent(Base):
    """تاریخچهٔ هر درخواست (برای نمایش مراحل به خریدار و کارگران)."""

    __tablename__ = "request_events"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("purchase_requests.id"), nullable=False, index=True)
    at = Column(DateTime, default=utcnow, nullable=False)
    actor = Column(String(100), nullable=False)
    action = Column(String(30), nullable=False)
    note = Column(Text, nullable=True)
