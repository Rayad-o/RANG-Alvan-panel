from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User
from app.schemas.control import SettingsModel
from app.services.activity import log_activity
from app.services.settings import get_settings, save_settings

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/")
async def read_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_settings(db)


@router.put("/")
async def update_settings(
    data: SettingsModel,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    await save_settings(db, data.model_dump())
    log_activity(db, current_user.full_name, "settings_updated", "settings", None)
    await db.commit()
    return await get_settings(db)
