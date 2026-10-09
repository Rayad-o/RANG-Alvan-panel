from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt

from app.core.config import settings

# نکته: passlib از سال ۲۰۲۰ به‌روزرسانی نشده و با bcrypt 4.1+ ناسازگار است
# ( AttributeError روی bcrypt.__about__ که در هر دو فراخوانی hash و verify
#   لاگ خطای ترسناک می‌نویسد). چون فقط از یک الگوریتم استفاده می‌کنیم،
#   استفاده مستقیم از خود bcrypt هم ساده‌تر است و هم سالم‌تر.
# هش‌های ساخته‌شده با passlib هم قالب استاندارد $2b$ دارند و بدون تغییر قابل verify هستند.

# bcrypt فقط ۷۲ بایت اول رمز را در نظر می‌گیرد؛ برای رمزهای فارسی/بلند این مهم است.
_MAX_PASSWORD_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_PASSWORD_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(_prepare(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        # هش نامعتبر/با فرمت ناشناخته
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)