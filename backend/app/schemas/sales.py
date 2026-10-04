from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class SalesInvoiceCreate(BaseModel):
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    amount: Decimal
    remaining_amount: Optional[Decimal] = None
    sale_date: str
    status: str = "completed"
    description: Optional[str] = None


class SalesInvoiceOut(BaseModel):
    id: int
    invoice_number: Optional[str]
    customer_name: Optional[str]
    amount: Decimal
    remaining_amount: Optional[Decimal]
    sale_date: str
    status: str
    description: Optional[str]

    class Config:
        from_attributes = True

