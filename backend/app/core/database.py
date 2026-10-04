from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# ساخت Engine (موتور اتصال به دیتابیس)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # در حالت توسعه لاگ SQL را نشان می‌دهد
)

# ساخت Session
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# پایه برای مدل‌ها
Base = declarative_base()

# وابستگی برای استفاده در APIها
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
            