import json
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.timeutil import UtcDatetime, to_utc_naive

Priority = Literal["critical", "high", "medium", "low"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- تأمین‌کنندگان ----------
class SupplierCreate(BaseModel):
    code: Optional[str] = Field(None, max_length=30)
    name: str = Field(min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    bank_account: Optional[str] = Field(None, max_length=60)


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    bank_account: Optional[str] = Field(None, max_length=60)
    is_high_risk: Optional[bool] = None


class SupplierOut(ORM):
    id: int
    code: str
    name: str
    category: Optional[str]
    bank_account: Optional[str]
    bank_changed_at: Optional[UtcDatetime]
    bank_changed_by: Optional[str]
    bank_verified: bool
    is_high_risk: bool
    created_at: UtcDatetime


# ---------- پرداخت‌ها ----------
class PaymentCreate(BaseModel):
    supplier_id: int
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    description: Optional[str] = Field(None, max_length=500)
    po_ref: Optional[str] = Field(None, max_length=50)


class DecisionNote(BaseModel):
    note: Optional[str] = Field(None, max_length=1000)


class PaymentOut(ORM):
    id: int
    ref: Optional[str]
    supplier_id: Optional[int]
    party_name: str
    description: Optional[str]
    po_ref: Optional[str]
    amount: Decimal
    risk_score: int
    risk_reasons: list[str] = []
    status: str
    created_by: Optional[str]
    decided_by: Optional[str]
    decided_at: Optional[UtcDatetime]
    decision_note: Optional[str]
    created_at: UtcDatetime
    required_role: str = "manager"

    @field_validator("risk_reasons", mode="before")
    @classmethod
    def _parse_reasons(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                return []
        return value or []


# ---------- فاکتور خرید ----------
class PurchaseInvoiceCreate(BaseModel):
    number: str = Field(min_length=1, max_length=50)
    supplier_id: int
    po_number: Optional[str] = Field(None, max_length=50)
    ordered_qty: Optional[Decimal] = Field(None, ge=0)
    received_qty: Decimal = Field(ge=0)
    invoiced_qty: Decimal = Field(ge=0)
    unit: str = Field("kg", max_length=20)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class PurchaseInvoiceOut(ORM):
    id: int
    number: str
    supplier_id: Optional[int]
    supplier_name: str
    po_number: Optional[str]
    ordered_qty: Optional[Decimal]
    received_qty: Decimal
    invoiced_qty: Decimal
    unit: str
    amount: Decimal
    status: str
    note: Optional[str]
    created_at: UtcDatetime


# ---------- وظایف ----------
class TaskCreate(BaseModel):
    unit: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    owner: str = Field(min_length=1, max_length=100)
    priority: Priority = "medium"
    due_at: UtcDatetime

    @field_validator("due_at")
    @classmethod
    def _utc(cls, value):
        return to_utc_naive(value)


class TaskOut(ORM):
    id: int
    unit: str
    title: str
    owner: str
    priority: str
    due_at: UtcDatetime
    status: str  # open / overdue / done  (overdue محاسبه می‌شود)
    completed_at: Optional[UtcDatetime]


# ---------- کاربران ----------
class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[Literal["admin", "manager", "staff", "buyer", "accountant", "dept_head", "dept_staff"]] = None
    department: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128)


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


# ---------- تنظیمات ----------
class Tier(BaseModel):
    upto: Optional[int] = Field(None, gt=0)
    role: Literal["manager", "admin"]


class ControlsModel(BaseModel):
    risk_score: bool = True
    bank_change_alert: bool = True
    duplicate_detection: bool = True
    three_way_match: bool = True
    task_escalation: bool = True


class SettingsModel(BaseModel):
    controls: ControlsModel
    approval_tiers: list[Tier] = Field(min_length=1, max_length=8)
    match_tolerance_pct: float = Field(ge=0, le=50)
    high_risk_threshold: int = Field(ge=1, le=100)
    buyer_debt_limit: int = Field(20_000_000, ge=0)

    @field_validator("approval_tiers")
    @classmethod
    def _tiers(cls, tiers):
        limits = [t.upto for t in tiers]
        if limits[-1] is not None:
            raise ValueError("آخرین سقف باید «بدون سقف» باشد")
        finite = [x for x in limits[:-1]]
        if any(x is None for x in finite) or finite != sorted(finite) or len(set(finite)) != len(finite):
            raise ValueError("سقف‌ها باید صعودی و غیرتکراری باشند")
        return tiers
