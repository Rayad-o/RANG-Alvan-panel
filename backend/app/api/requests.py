"""گردش درخواست خرید بین حسابدار، رییس بخش و کارکن بخش.

submitted ──(حسابدار: ارجاع به بخش)──▶ forwarded ──(رییس بخش: واگذاری)──▶ assigned
        ──(کارکن: شروع)──▶ in_progress ──(کارکن: پایان)──▶ done
حسابدار در مرحلهٔ submitted/forwarded می‌تواند درخواست را رد (rejected) کند؛ مدیر سیستم همهٔ اقدام‌ها را دارد.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.portal import Department, PurchaseRequest
from app.models.user import User, UserRole
from app.schemas.portal import AssignIn, ForwardIn, NoteIn, RejectIn, RequestOut
from app.services.activity import log_activity
from app.services.buyer import debt_totals
from app.services.requests import add_event, build_out
from app.services.settings import get_settings

router = APIRouter(prefix="/requests", tags=["Purchase requests"])

_work = require_roles("accountant", "dept_head", "dept_staff", "admin", "manager")

ALL_STATUSES = ("submitted", "forwarded", "assigned", "in_progress", "done", "rejected", "cancelled")
HEAD_VISIBLE = ("forwarded", "assigned", "in_progress", "done")


def _role(user: User) -> str:
    return user.role.value


def _scope(stmt, user: User):
    """محدودکردن درخواست‌های قابل‌مشاهده بر اساس نقش."""
    role = _role(user)
    if role in ("accountant", "admin", "manager"):
        return stmt
    if role == "dept_head":
        return stmt.where(PurchaseRequest.department == user.department, PurchaseRequest.status.in_(HEAD_VISIBLE))
    if role == "dept_staff":
        return stmt.where(PurchaseRequest.assigned_to_id == user.id)
    return stmt.where(PurchaseRequest.id == -1)


def _can_view(req: PurchaseRequest, user: User) -> bool:
    role = _role(user)
    if role in ("accountant", "admin", "manager"):
        return True
    if role == "dept_head":
        return req.department == user.department and req.status in HEAD_VISIBLE
    if role == "dept_staff":
        return req.assigned_to_id == user.id
    return False


async def _get(db: AsyncSession, request_id: int) -> PurchaseRequest:
    req = await db.get(PurchaseRequest, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")
    return req


async def _respond(db: AsyncSession, req: PurchaseRequest, user: User) -> RequestOut:
    with_debt = _role(user) in ("accountant", "admin", "manager")
    return (await build_out(db, [req], with_events=True, with_debt=with_debt))[0]


@router.get("/", response_model=list[RequestOut])
async def list_requests(
    q: str | None = Query(None, description="جستجو در شماره، نام خریدار یا یادداشت"),
    status: str | None = Query(None),
    department: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_work),
):
    stmt = select(PurchaseRequest).join(User, User.id == PurchaseRequest.buyer_id)
    stmt = _scope(stmt, current_user)
    if status:
        stmt = stmt.where(PurchaseRequest.status == status)
    if department:
        stmt = stmt.where(PurchaseRequest.department == department)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(PurchaseRequest.ref.ilike(like), User.full_name.ilike(like), PurchaseRequest.note.ilike(like)))
    rows = (
        await db.execute(stmt.order_by(PurchaseRequest.created_at.desc(), PurchaseRequest.id.desc()).limit(limit).offset(offset))
    ).scalars().all()
    return await build_out(db, rows, with_debt=_role(current_user) in ("accountant", "admin", "manager"))


@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db), current_user: User = Depends(_work)):
    """شمارندهٔ وضعیت‌ها برای کارت‌ها و نشانگر منو (محدود به آنچه کاربر می‌بیند)."""
    stmt = select(PurchaseRequest.status, func.count(PurchaseRequest.id))
    stmt = _scope(stmt, current_user).group_by(PurchaseRequest.status)
    counts = {s: 0 for s in ALL_STATUSES}
    counts.update(dict((await db.execute(stmt)).all()))

    role = _role(current_user)
    pending = {
        "accountant": counts["submitted"],
        "admin": counts["submitted"],
        "manager": 0,
        "dept_head": counts["forwarded"],
        "dept_staff": counts["assigned"],
    }.get(role, 0)

    result = {"counts": counts, "pending_for_me": pending}
    if role in ("accountant", "admin", "manager"):
        cfg = await get_settings(db)
        totals = await debt_totals(db)
        limit = cfg["buyer_debt_limit"]
        result["open_debt_total"] = sum(totals.values(), 0)
        result["buyers_over_limit"] = sum(1 for t in totals.values() if t > limit)
        result["debt_limit"] = limit
    return result


@router.get("/staff")
async def department_staff(
    department: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("dept_head", "admin")),
):
    """کارکنان یک بخش و تعداد کارهای در جریان هرکدام (برای واگذاری)."""
    role = _role(current_user)
    dept = current_user.department if role == "dept_head" else department
    if not dept:
        raise HTTPException(status_code=400, detail="بخش مشخص نیست")

    staff = (
        await db.execute(
            select(User).where(User.role == UserRole.dept_staff, User.department == dept, User.is_active.is_(True)).order_by(User.full_name)
        )
    ).scalars().all()
    loads = dict(
        (await db.execute(
            select(PurchaseRequest.assigned_to_id, func.count(PurchaseRequest.id))
            .where(PurchaseRequest.status.in_(("assigned", "in_progress")), PurchaseRequest.assigned_to_id.is_not(None))
            .group_by(PurchaseRequest.assigned_to_id)
        )).all()
    )
    return [{"id": u.id, "full_name": u.full_name, "email": u.email, "active_requests": loads.get(u.id, 0)} for u in staff]


@router.get("/{request_id}", response_model=RequestOut)
async def get_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_work),
):
    req = await _get(db, request_id)
    if not _can_view(req, current_user):
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")
    return await _respond(db, req, current_user)


# ---------------------------------------------------------------------------
# اقدام‌ها (هرکدام دسترسی و وضعیت مجاز خودش را دارد)
# ---------------------------------------------------------------------------
@router.post("/{request_id}/forward", response_model=RequestOut)
async def forward_request(
    request_id: int,
    data: ForwardIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("accountant", "admin")),
):
    req = await _get(db, request_id)
    if req.status not in ("submitted", "forwarded"):
        raise HTTPException(status_code=400, detail="این درخواست در وضعیتی نیست که بتوان آن را ارجاع داد")
    dept = (await db.execute(select(Department).where(Department.name == data.department))).scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=400, detail="بخش انتخاب‌شده معتبر نیست")

    req.status = "forwarded"
    req.department = dept.name
    req.assigned_to_id = None  # ارجاع دوباره، واگذاری قبلی را باطل می‌کند
    add_event(db, req, current_user.full_name, "forwarded", f"به بخش «{dept.name}»" + (f" — {data.note}" if data.note else ""))
    log_activity(db, current_user.full_name, "request_forwarded", "request", f"{req.ref} → {dept.name}")
    await db.commit()
    return await _respond(db, req, current_user)


@router.post("/{request_id}/reject", response_model=RequestOut)
async def reject_request(
    request_id: int,
    data: RejectIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("accountant", "admin")),
):
    req = await _get(db, request_id)
    if req.status not in ("submitted", "forwarded"):
        raise HTTPException(status_code=400, detail="این درخواست قابل رد شدن نیست")
    req.status = "rejected"
    req.decision_note = data.note
    req.assigned_to_id = None
    add_event(db, req, current_user.full_name, "rejected", data.note)
    log_activity(db, current_user.full_name, "request_rejected", "request", req.ref)
    await db.commit()
    return await _respond(db, req, current_user)


@router.post("/{request_id}/assign", response_model=RequestOut)
async def assign_request(
    request_id: int,
    data: AssignIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("dept_head", "admin")),
):
    req = await _get(db, request_id)
    if req.status not in ("forwarded", "assigned"):
        raise HTTPException(status_code=400, detail="این درخواست در وضعیت قابل واگذاری نیست")
    if _role(current_user) == "dept_head" and req.department != current_user.department:
        raise HTTPException(status_code=403, detail="این درخواست مربوط به بخش شما نیست")

    assignee = await db.get(User, data.assignee_id)
    if (
        assignee is None or assignee.role != UserRole.dept_staff or not assignee.is_active
        or assignee.department != req.department
    ):
        raise HTTPException(status_code=400, detail="کارکن انتخاب‌شده عضو این بخش نیست")

    req.status = "assigned"
    req.assigned_to_id = assignee.id
    add_event(db, req, current_user.full_name, "assigned", f"به {assignee.full_name}" + (f" — {data.note}" if data.note else ""))
    log_activity(db, current_user.full_name, "request_assigned", "request", f"{req.ref} → {assignee.full_name}")
    await db.commit()
    return await _respond(db, req, current_user)


def _check_worker_access(req: PurchaseRequest, user: User) -> None:
    role = _role(user)
    if role == "dept_staff" and req.assigned_to_id != user.id:
        raise HTTPException(status_code=403, detail="این کار به شما واگذار نشده است")
    if role == "dept_head" and req.department != user.department:
        raise HTTPException(status_code=403, detail="این درخواست مربوط به بخش شما نیست")


@router.post("/{request_id}/start", response_model=RequestOut)
async def start_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("dept_staff", "dept_head", "admin")),
):
    req = await _get(db, request_id)
    _check_worker_access(req, current_user)
    if req.status != "assigned":
        raise HTTPException(status_code=400, detail="فقط کار واگذارشده را می‌توان شروع کرد")
    req.status = "in_progress"
    add_event(db, req, current_user.full_name, "started")
    await db.commit()
    return await _respond(db, req, current_user)


@router.post("/{request_id}/complete", response_model=RequestOut)
async def complete_request(
    request_id: int,
    data: NoteIn | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("dept_staff", "dept_head", "admin")),
):
    req = await _get(db, request_id)
    _check_worker_access(req, current_user)
    allowed = ("in_progress",) if _role(current_user) == "dept_staff" else ("assigned", "in_progress")
    if req.status not in allowed:
        raise HTTPException(status_code=400, detail="این کار در وضعیتی نیست که بتوان آن را تکمیل کرد")
    req.status = "done"
    add_event(db, req, current_user.full_name, "completed", data.note if data else None)
    log_activity(db, current_user.full_name, "request_completed", "request", req.ref)
    await db.commit()
    return await _respond(db, req, current_user)
