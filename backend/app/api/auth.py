from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select
from app.core.deps import get_current_user, optional_user



from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.models.user import User, UserRole
from app.schemas.control import ChangePassword
from app.schemas.user import UserCreate, UserLogin, UserOut, Token
from app.services.users import normalize_department


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(optional_user),
):
    # ثبت‌نام باز فقط برای ساخت اولین کاربر (مدیر سیستم) مجاز است؛
    # بعد از آن فقط admin می‌تواند کاربر بسازد. در غیر این صورت هر کسی
    # می‌توانست خودش را admin ثبت کند.
    user_count = (await db.execute(select(func.count(User.id)))).scalar_one()
    if user_count == 0:
        role = UserRole.admin
    else:
        if current_user is None or current_user.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="فقط مدیر سیستم می‌تواند کاربر جدید بسازد",
            )
        role = user_data.role

    email = user_data.email.strip()
    if not email:
        raise HTTPException(status_code=400, detail="ایمیل را وارد کنید")
    department = await normalize_department(db, role.value, user_data.department)

    # بررسی تکراری بودن ایمیل
    result = await db.execute(
        select(User).where(User.email == email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="این ایمیل قبلاً ثبت شده است",
        )

    new_user = User(
        email=email,
        full_name=user_data.full_name.strip(),
        hashed_password=hash_password(user_data.password),
        role=role,
        department=department,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(
        user_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ایمیل یا رمز عبور اشتباه است",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="حساب کاربری غیرفعال است",
        )

    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role.value,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
async def change_password(
    data: ChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="رمز فعلی اشتباه است")
    current_user.hashed_password = hash_password(data.new_password)
    await db.commit()
    return {"message": "رمز عبور تغییر کرد"}
