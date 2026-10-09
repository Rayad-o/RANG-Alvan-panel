from sqlalchemy.ext.asyncio import AsyncSession

from app.models.control import ActivityLog


def log_activity(db: AsyncSession, actor: str, action: str, entity: str | None = None, detail: str | None = None) -> None:
    """ثبت رویداد در دفتر فعالیت‌ها (commit را فراخواننده انجام می‌دهد)."""
    db.add(ActivityLog(actor=actor, action=action, entity=entity, detail=detail))
