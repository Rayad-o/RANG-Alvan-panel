from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.portal import Department
from app.models.user import User
from app.schemas.portal import DepartmentCreate, DepartmentOut
from app.services.activity import log_activity

router = APIRouter(prefix="/departments", tags=["Departments"])

# فهرست بخش‌ها برای همهٔ نقش‌های داخلی و کارگران؛ فقط خریدار دسترسی ندارد
_read = require_roles("admin", "manager", "staff", "accountant", "dept_head", "dept_staff")


@router.get("/", response_model=list[DepartmentOut])
async def list_departments(db: AsyncSession = Depends(get_db), current_user: User = Depends(_read)):
    return (await db.execute(select(Department).order_by(Department.name))).scalars().all()


@router.post("/", response_model=DepartmentOut, status_code=201)
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    name = data.name.strip()
    if (await db.execute(select(Department.id).where(Department.name == name))).first():
        raise HTTPException(status_code=400, detail="این بخش قبلاً ثبت شده است")
    dept = Department(name=name)
    db.add(dept)
    log_activity(db, current_user.full_name, "department_created", "department", name)
    await db.commit()
    await db.refresh(dept)
    return dept
