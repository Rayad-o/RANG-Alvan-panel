from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

# auto_error=False تا بتوانیم خودمان 401 با پیام فارسی برگردانیم
# (رفتار پیش‌فرض FastAPI برای هدر ناقص، 403 برمی‌گرداند که گمراه‌کننده است)
security = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "توکن نامعتبر است") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise _unauthorized("هدر Authorization ارسال نشده است")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise _unauthorized()

    email = payload.get("sub")
    if not email:
        raise _unauthorized()

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise _unauthorized("کاربر یافت نشد")

    # کاربر غیرفعال باید نتواند از توکنِ معتبرش استفاده کند
    # (در غیر این صورت غیرفعال‌سازی حساب بی‌اثر می‌ماند)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="حساب کاربری غیرفعال است",
        )

    return user


async def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """کاربر جاری اگر توکن ارسال شده باشد، وگرنه None."""
    if credentials is None:
        return None
    return await get_current_user(credentials, db)


def require_roles(*roles: str) -> Callable:
    """وابستگی FastAPI برای محدود کردن دسترسی به نقش‌های مشخص."""

    allowed = {r.value if hasattr(r, "value") else r for r in roles}

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = (
            current_user.role.value
            if hasattr(current_user.role, "value")
            else current_user.role
        )
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="دسترسی مجاز نیست",
            )
        return current_user

    return checker

# دسترسی به داشبورد مدیریتی (فروش، مالی، کنترل و ریسک): فقط نقش‌های داخلی.
# خریدار و کارگران بخش فقط به API پنل خودشان دسترسی دارند.
internal_only = require_roles("admin", "manager", "staff")
