from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    except JWTError:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="کاربر یافت نشد")

    return user


def require_roles(*roles):
    async def checker(current_user: User = Depends(get_current_user)):
        user_role = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
        if user_role not in roles:
            raise HTTPException(status_code=403, detail="دسترسی مجاز نیست")
        return current_user
    return checker


