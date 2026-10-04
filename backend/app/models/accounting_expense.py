from sqlalchemy import Column, Integer, String, Numeric, DateTime, func
from app.core.database import Base


class AccountingExpense(Base):
    __tablename__ = "accounting_expenses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    debit_turnover = Column(Numeric(18, 2), default=0)
    credit_turnover = Column(Numeric(18, 2), default=0)
    debit_balance = Column(Numeric(18, 2), default=0)
    credit_balance = Column(Numeric(18, 2), default=0)
    period_label = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
