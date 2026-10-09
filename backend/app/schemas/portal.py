from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.timeutil import UtcDatetime


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- بخش‌ها ----------
class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class DepartmentOut(ORM):
    id: int
    name: str


# ---------- بدهی ----------
class DebtCreate(BaseModel):
    buyer_id: int
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    description: Optional[str] = Field(None, max_length=500)
    due_date: Optional[date] = None


class DebtPay(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    note: Optional[str] = Field(None, max_length=500)


class VoidNote(BaseModel):
    note: str = Field(min_length=3, max_length=500)


class DebtOut(BaseModel):
    id: int
    buyer_id: int
    buyer_name: Optional[str] = None
    amount: Decimal
    paid_amount: Decimal
    remaining: Decimal
    description: Optional[str]
    due_date: Optional[date]
    status: str
    created_by: Optional[str]
    created_at: UtcDatetime


class BuyerRow(BaseModel):
    id: int
    full_name: str
    email: str
    is_active: bool
    total_debt: Decimal
    blocked: bool
    open_requests: int


# ---------- درخواست خرید ----------
class RequestItemIn(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0, max_digits=15, decimal_places=3)


class RequestCreate(BaseModel):
    items: list[RequestItemIn] = Field(min_length=1, max_length=30)
    note: Optional[str] = Field(None, max_length=1000)


class RequestItemOut(ORM):
    id: int
    product_id: Optional[int]
    product_code: str
    product_title: str
    quantity: Decimal


class EventOut(ORM):
    at: UtcDatetime
    actor: str
    action: str
    note: Optional[str]


class RequestOut(BaseModel):
    id: int
    ref: Optional[str]
    buyer_id: int
    buyer_name: Optional[str] = None
    buyer_debt: Optional[Decimal] = None
    note: Optional[str]
    status: str
    department: Optional[str]
    assigned_to_id: Optional[int]
    assigned_to_name: Optional[str] = None
    decision_note: Optional[str]
    created_at: UtcDatetime
    updated_at: UtcDatetime
    items: list[RequestItemOut] = []
    events: list[EventOut] = []


class ForwardIn(BaseModel):
    department: str = Field(min_length=1, max_length=100)
    note: Optional[str] = Field(None, max_length=1000)


class AssignIn(BaseModel):
    assignee_id: int
    note: Optional[str] = Field(None, max_length=1000)


class NoteIn(BaseModel):
    note: Optional[str] = Field(None, max_length=1000)


class RejectIn(BaseModel):
    note: str = Field(min_length=3, max_length=1000)
