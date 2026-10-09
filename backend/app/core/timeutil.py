"""ابزارهای زمان. همهٔ زمان‌ها در دیتابیس «UTC بدون tzinfo» ذخیره می‌شوند."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import PlainSerializer

from app.core.config import settings

try:
    TZ = ZoneInfo(settings.TIMEZONE)
except ZoneInfoNotFoundError:  # tzdata نصب نیست
    TZ = timezone.utc


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def local_today() -> date:
    return datetime.now(TZ).date()


def local_day_start_utc(day: date) -> datetime:
    """شروع روز محلی (۰۰:۰۰) به UTC بدون tzinfo."""
    return datetime.combine(day, time.min, tzinfo=TZ).astimezone(timezone.utc).replace(tzinfo=None)


def local_date_of(value: datetime) -> date:
    return value.replace(tzinfo=timezone.utc).astimezone(TZ).date()


def _iso_utc(value: datetime) -> str:
    return (value.isoformat() + "Z") if value.tzinfo is None else value.isoformat()


# در خروجی JSON پسوند Z اضافه می‌شود تا مرورگر زمان را UTC بخواند نه محلی
UtcDatetime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str, when_used="json")]

__all__ = [
    "TZ", "utcnow", "to_utc_naive", "local_today", "local_day_start_utc",
    "local_date_of", "UtcDatetime", "timedelta",
]
