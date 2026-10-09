from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text

from app.core.database import Base
from app.core.timeutil import utcnow


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True)
    bank_account = Column(String(60), nullable=True)
    bank_changed_at = Column(DateTime, nullable=True)
    bank_changed_by = Column(String(100), nullable=True)
    bank_verified = Column(Boolean, nullable=False, default=True)
    is_high_risk = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    id = Column(Integer, primary_key=True, index=True)
    ref = Column(String(20), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True, index=True)
    party_name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    po_ref = Column(String(50), nullable=True)
    amount = Column(Numeric(18, 2), nullable=False)
    risk_score = Column(Integer, nullable=False, default=0)
    risk_reasons = Column(Text, nullable=False, default="[]")  # JSON
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending/approved/stopped
    created_by = Column(String(100), nullable=True)
    decided_by = Column(String(100), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    decision_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)


class PurchaseInvoice(Base):
    __tablename__ = "purchase_invoices"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    supplier_name = Column(String(255), nullable=False)
    po_number = Column(String(50), nullable=True, index=True)
    ordered_qty = Column(Numeric(18, 3), nullable=True)
    received_qty = Column(Numeric(18, 3), nullable=False, default=0)
    invoiced_qty = Column(Numeric(18, 3), nullable=False, default=0)
    unit = Column(String(20), nullable=False, default="kg")
    amount = Column(Numeric(18, 2), nullable=False)
    status = Column(String(20), nullable=False, default="matched")  # matched/review/mismatch/resolved
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    unit = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    owner = Column(String(100), nullable=False)
    priority = Column(String(20), nullable=False, default="medium")  # critical/high/medium/low
    due_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="open", index=True)  # open/done
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(50), primary_key=True)
    value = Column(Text, nullable=False)  # JSON


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    actor = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    entity = Column(String(50), nullable=True)
    detail = Column(Text, nullable=True)
