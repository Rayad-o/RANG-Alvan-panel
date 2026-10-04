from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class SalesInvoice(Base):
    __tablename__ = "sales_invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(100), nullable=True)
    customer_name = Column(String(255), nullable=True)
    amount = Column(Numeric(18, 2), nullable=False)
    remaining_amount = Column(Numeric(18, 2), nullable=True)  # باقی‌مانده فاکتور
    sale_date = Column(String(20), nullable=False)  # تاریخ شمسی مثل 1405/07/02
    status = Column(String(50), default="completed")
    description = Column(Text, nullable=True)  # نوع تسویه و ...
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    