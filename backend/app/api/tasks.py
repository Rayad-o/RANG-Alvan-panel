from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.timeutil import utcnow
from app.models.control import Task
from app.models.user import User
from app.schemas.control import TaskCreate, TaskOut
from app.services.activity import log_activity

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _out(task: Task, now) -> TaskOut:
    out = TaskOut.model_validate(task)
    if task.status == "open" and task.due_at < now:
        out.status = "overdue"
    return out


@router.get("/", response_model=list[TaskOut])
async def list_tasks(
    status: str | None = Query(None, description="open / overdue / done"),
    q: str | None = Query(None, description="جستجو در وظیفه، مسئول یا واحد"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = utcnow()
    stmt = select(Task)
    if status == "done":
        stmt = stmt.where(Task.status == "done")
    elif status == "overdue":
        stmt = stmt.where(Task.status == "open", Task.due_at < now)
    elif status == "open":
        stmt = stmt.where(Task.status == "open", Task.due_at >= now)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Task.title.ilike(like), Task.owner.ilike(like), Task.unit.ilike(like)))

    # نیمه‌کارها اول (به ترتیب سررسید)، تکمیل‌شده‌ها آخر
    rows = (
        await db.execute(
            stmt.order_by((Task.status == "done"), Task.due_at.asc(), Task.id.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    return [_out(t, now) for t in rows]


@router.post("/", response_model=TaskOut, status_code=201)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = Task(**data.model_dump())
    db.add(task)
    log_activity(db, current_user.full_name, "task_created", "task", f"{task.title} • {task.owner}")
    await db.commit()
    await db.refresh(task)
    return _out(task, utcnow())


@router.post("/{task_id}/complete", response_model=TaskOut)
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="وظیفه یافت نشد")
    if task.status == "done":
        return _out(task, utcnow())
    task.status = "done"
    task.completed_at = utcnow()
    log_activity(db, current_user.full_name, "task_completed", "task", task.title)
    await db.commit()
    await db.refresh(task)
    return _out(task, utcnow())
