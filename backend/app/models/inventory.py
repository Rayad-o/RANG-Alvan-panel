from sqlalchemy import Column, Integer, String, Numeric, DateTime, func
from app.core.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    quantity = Column(Numeric(18, 4), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
