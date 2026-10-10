import bcrypt
from app.core.security import hash_password, verify_password

# Test bcrypt with known hash
hashed = b"$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
password = b"StrongPass123"
try:
    result = bcrypt.checkpw(password, hashed)
    print("bcrypt check with known hash:", result)
except Exception as e:
    print("Error:", e)

# Test our functions
new_hash = hash_password("StrongPass123")
print("New hash:", new_hash)
print("Verify new:", verify_password("StrongPass123", new_hash))

# Check what's in DB
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

engine = create_async_engine('sqlite+aiosqlite:///./dev.db', echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def check_user():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == 'admin@example.com'))
        user = result.scalar_one_or_none()
        if user:
            print(f"User: id={user.id}, email={user.email}, role={user.role}, active={user.is_active}")
            print(f"Stored hash: {user.hashed_password}")
            print("Verify stored:", verify_password("StrongPass123", user.hashed_password))
        else:
            print("User not found!")

asyncio.run(check_user())