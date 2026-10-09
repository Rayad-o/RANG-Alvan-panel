import secrets
import warnings

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- دیتابیس ---
    DATABASE_URL: str = "postgresql+asyncpg://admin:admin123@localhost:5432/dashboard"

    # --- امنیت ---
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 ساعت

    # --- CORS ---
    # "*" با allow_credentials=True توسط مرورگرها رد می‌شود؛
    # برای همین به‌صورت پیش‌فرض فقط مبدأهای همین سرور مجاز است.
    CORS_ORIGINS: str = "http://127.0.0.1:8000,http://localhost:8000"

    # --- منطقهٔ زمانی برای محاسبهٔ «امروز» در گزارش‌ها ---
    TIMEZONE: str = "Asia/Tehran"

    # --- لاگ SQL ---
    SQL_ECHO: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()

if not settings.SECRET_KEY:
    # کلید ثابت و hard-code شدنی نباید در کد باشد. برای محیط توسعه یک کلید
    # موقت ساخته می‌شود (با هر بار ری‌استارت توکن‌ها بی‌اعتبار می‌شوند).
    settings.SECRET_KEY = secrets.token_urlsafe(48)
    warnings.warn(
        "SECRET_KEY تنظیم نشده است؛ یک کلید موقت ساخته شد. "
        "برای محیط عملیاتی حتماً SECRET_KEY را در فایل .env مقدار بدهید.",
        RuntimeWarning,
        stacklevel=2,
    )