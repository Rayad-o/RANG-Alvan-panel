from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.timeutil import utcnow
from app.models.control import Supplier
from app.models.user import User
from app.schemas.control import SupplierCreate, SupplierOut, SupplierUpdate
from app.services.activity import log_activity

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

_manager = require_roles("manager", "admin")


async def _next_code(db: AsyncSession) -> str:
    last = (await db.execute(select(func.max(Supplier.id)))).scalar_one() or 0
    return f"SUP-{1000 + last + 1}"


@router.get("/", response_model=list[SupplierOut])
async def list_suppliers(
    q: str | None = Query(None, description="جستجو در نام یا کد"),
    risk: str | None = Query(None, description="high یا normal"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Supplier)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Supplier.name.ilike(like), Supplier.code.ilike(like)))
    if risk == "high":
        stmt = stmt.where(Supplier.is_high_risk.is_(True))
    elif risk == "normal":
        stmt = stmt.where(Supplier.is_high_risk.is_(False))
    result = await db.execute(stmt.order_by(Supplier.name).limit(limit).offset(offset))
    return result.scalars().all()


@router.post("/", response_model=SupplierOut, status_code=201)
async def create_supplier(
    data: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    code = (data.code or "").strip() or await _next_code(db)
    if (await db.execute(select(Supplier.id).where(Supplier.code == code))).first():
        raise HTTPException(status_code=400, detail="این کد تأمین‌کننده قبلاً ثبت شده است")

    supplier = Supplier(
        code=code,
        name=data.name.strip(),
        category=data.category,
        bank_account=data.bank_account,
    )
    db.add(supplier)
    log_activity(db, current_user.full_name, "supplier_created", "supplier", supplier.name)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.patch("/{supplier_id}", response_model=SupplierOut)
async def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    supplier = await db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="تأمین‌کننده یافت نشد")

    changes = data.model_dump(exclude_unset=True)

    # علامت‌گذاری ریسک، حساس است و فقط مدیر/ادمین می‌تواند آن را عوض کند
    if "is_high_risk" in changes and current_user.role.value == "staff":
        raise HTTPException(status_code=403, detail="دسترسی مجاز نیست")

    if "bank_account" in changes and changes["bank_account"] != supplier.bank_account:
        supplier.bank_account = changes.pop("bank_account")
        supplier.bank_changed_at = utcnow()
        supplier.bank_changed_by = current_user.full_name
        supplier.bank_verified = False  # تا تأیید مدیر، پرریسک محسوب می‌شود
        log_activity(db, current_user.full_name, "bank_changed", "supplier", supplier.name)
    else:
        changes.pop("bank_account", None)

    for key, value in changes.items():
        setattr(supplier, key, value)

    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.post("/{supplier_id}/verify-bank", response_model=SupplierOut)
async def verify_bank(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_manager),
):
    supplier = await db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="تأمین‌کننده یافت نشد")
    supplier.bank_verified = True
    log_activity(db, current_user.full_name, "bank_verified", "supplier", supplier.name)
    await db.commit()
    await db.refresh(supplier)
    return supplier
