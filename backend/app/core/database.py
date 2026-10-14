from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# برای SQLite در حالت async نیاز به aiosqlite است
# PostgreSQL پیش‌فرض production است
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    # برای SQLite نیاز است تا deadlock پیش نشود
    connect_args={"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {},
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ستون‌هایی که بعد از نسخهٔ اول به جدول‌های موجود اضافه شده‌اند.
# create_all فقط جدول‌های جدید می‌سازد؛ این فهرست دیتابیس‌های قدیمی را بدون از دست رفتن داده ارتقا می‌دهد.
COLUMN_MIGRATIONS = [
    ("users", "department", "VARCHAR(100)"),
    ("inventory_items", "stock_value", "NUMERIC(18, 2)"),
    ("inventory_items", "avg_price", "NUMERIC(18, 4)"),
]


def ensure_columns(sync_conn) -> None:
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())
    for table, column, ddl in COLUMN_MIGRATIONS:
        if table not in existing_tables:
            continue
        if column not in {c["name"] for c in inspector.get_columns(table)}:
            sync_conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
