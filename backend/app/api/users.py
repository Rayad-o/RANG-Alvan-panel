from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.control import UserUpdate
from app.schemas.user import UserOut
from app.services.activity import log_activity
from app.services.users import normalize_department

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    return (await db.execute(select(User).order_by(User.id))).scalars().all()


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")

    changes = data.model_dump(exclude_unset=True)

    # جلوگیری از قفل شدن سیستم: ادمین نباید خودش را تنزل دهد یا غیرفعال کند
    if user.id == current_user.id and (
        changes.get("is_active") is False or ("role" in changes and changes["role"] != "admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="نمی‌توانید نقش یا وضعیت حساب خودتان را کاهش دهید",
        )

    if "password" in changes:
        user.hashed_password = hash_password(changes.pop("password"))
    if "role" in changes:
        user.role = UserRole(changes.pop("role"))
    # بخش با نقش نهایی سنجیده می‌شود (مثلاً تغییر نقش به رییس بخش بدون بخش مجاز نیست)
    if "department" in changes or "role" in data.model_fields_set:
        user.department = await normalize_department(
            db, user.role.value, changes.pop("department", user.department)
        )
    for key, value in changes.items():
        setattr(user, key, value)

    log_activity(db, current_user.full_name, "user_updated", "user", user.email)
    await db.commit()
    await db.refresh(user)
    return user
