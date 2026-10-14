from sqlalchemy import Column, Integer, String, Numeric, DateTime, func
from app.core.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False, default=0)
    # از «مرور مبلغی انبار محصول»: موجودی به تفکیک مبلغ و فی متوسط
    stock_value = Column(Numeric(18, 2), nullable=True)  # موجودی-مبلغ
    avg_price = Column(Numeric(18, 4), nullable=True)  # موجودی-فی متوسط
    created_at = Column(DateTime(timezone=True), server_default=func.now())
