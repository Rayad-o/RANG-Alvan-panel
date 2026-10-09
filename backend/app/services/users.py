from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.portal import Department
from app.models.user import DEPARTMENT_ROLES


async def normalize_department(db: AsyncSession, role: str, department: str | None) -> str | None:
    """رییس و کارکن بخش حتماً باید عضو یکی از بخش‌های ثبت‌شده باشند؛ بقیهٔ نقش‌ها بخش ندارند."""
    if role not in DEPARTMENT_ROLES:
        return None
    name = (department or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="برای رییس بخش و کارکن بخش، انتخاب بخش الزامی است")
    exists = (await db.execute(select(Department.id).where(Department.name == name))).first()
    if not exists:
        raise HTTPException(status_code=400, detail="بخش انتخاب‌شده معتبر نیست؛ ابتدا بخش را بسازید")
    return name
