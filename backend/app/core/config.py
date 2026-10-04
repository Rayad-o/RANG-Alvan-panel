from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # تنظیمات دیتابیس
    DATABASE_URL: str = "postgresql+asyncpg://admin:admin123@localhost:5432/dashboard"

    # تنظیمات امنیت
    SECRET_KEY: str = "super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 ساعت

    class Config:
        env_file = ".env"


settings = Settings()
