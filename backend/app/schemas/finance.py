from pydantic import BaseModel
from typing import Optional
from datetime import date
from decimal import Decimal

class FinanceTransactionCreate(BaseModel):
    type: str
    amount: Decimal
    transaction_date: date
    party_name: Optional[str] = None
    description: Optional[str] = None
    needs_followup: bool = False

class FinanceTransactionOut(BaseModel):
    id: int
    type: str
    amount: Decimal
    transaction_date: Optional[date] = None
    party_name: Optional[str]
    description: Optional[str]
    needs_followup: bool

    class Config:
        from_attributes = True




