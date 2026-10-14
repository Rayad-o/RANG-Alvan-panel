from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, sales, finance, upload, dashboard
from app.api import payments, purchase_invoices, suppliers, tasks, users
from app.api import accounting, buyer, departments, requests as requests_api
from app.api import settings as settings_api
from app.api.upload_finance import router as upload_finance_router
from app.api.upload_expense import router as expense_upload_router
from app.api.upload_treasury import router as upload_treasury_router
from app.api.treasury import router as treasury_router
from app.api.inventory import router as inventory_router
from app.core.config import settings
from app.core.database import engine, Base, ensure_columns
from app.core.deps import internal_only
from app import models  # noqa: F401  (ثبت همهٔ مدل‌ها روی Base قبل از create_all)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(ensure_columns)
    print("[OK] Database tables checked/created")
    yield

app = FastAPI(
    title="Management Dashboard API",
    description="سامانه گزارش‌دهی و داشبورد مدیریتی",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)

# داشبورد مدیریتی (فروش، مالی، انبار، کنترل و ریسک): فقط نقش‌های داخلی.
# خریدار و کارگران بخش فقط به API پنل خودشان دسترسی دارند.
_internal = [Depends(internal_only)]
for _router in (
    dashboard.router, suppliers.router, payments.router, purchase_invoices.router, tasks.router,
    settings_api.router, sales.router, finance.router, upload.router, expense_upload_router,
    upload_finance_router, upload_treasury_router, treasury_router, inventory_router,
):
    app.include_router(_router, dependencies=_internal)

# مدیریت کاربران و پنل‌های خریدار/کارگران (هرکدام نقش‌های مجاز خودش را دارد)
for _router in (users.router, departments.router, buyer.router, accounting.router, requests_api.router):
    app.include_router(_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "سیستم با موفقیت در حال اجرا است",
    }


class NoCacheStaticFiles(StaticFiles):
    """فایل‌های فرانت‌اند همیشه با سرور اعتبارسنجی می‌شوند تا بعد از هر تغییر نسخهٔ قدیمی نمایش داده نشود."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


# سرو فرانت‌اند روی همان پورت (هم‌منشأ). باید بعد از همهٔ routeها mount شود.
if FRONTEND_DIR.is_dir():
    app.mount("/", NoCacheStaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
