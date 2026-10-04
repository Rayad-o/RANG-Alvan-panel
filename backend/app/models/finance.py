from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.core.database import Base


class FinanceTransaction(Base):
    __tablename__ = "finance_transactions"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    transaction_date = Column(Date, nullable=True)


    party_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    needs_followup = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

