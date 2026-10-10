import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.core.security import hash_password

engine = create_async_engine('sqlite+aiosqlite:///./dev.db', echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def reset_password():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == 'admin@example.com'))
        user = result.scalar_one_or_none()
        if user:
            user.hashed_password = hash_password("StrongPass123")
            await db.commit()
            print(f"Password reset for {user.email}")
            print(f"New hash: {user.hashed_password}")
        else:
            print("User not found!")

asyncio.run(reset_password())