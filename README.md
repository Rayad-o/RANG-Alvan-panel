# سامانه گزارش‌دهی و داشبورد مدیریتی (Rang)

سامانه‌ای برای مدیریت فروش، مالی، انبار و گزارش‌گیری با رابط کاربری فارسی.

## پیش‌نیازها

- Python 3.11+
- PostgreSQL 14+ (یا SQLite برای توسعه)
- مرورگر وب مدرن

## راه‌اندازی Backend

### ۱. محیط مجازی و وابستگی‌ها

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

### ۲. تنظیم متغیرهای محیطی

فایل `.env.example` را کپی کنید و مقادیر را تغییر دهید:

```bash
copy .env.example .env
```

**برای توسعه سریع با SQLite (نیازی به PostgreSQL نیست):**

```env
DATABASE_URL=sqlite+aiosqlite:///./dev.db
SECRET_KEY=your-secret-key-here-at-least-32-chars
CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:5500,http://localhost:5500
SQL_ECHO=true
```

**برای Production با PostgreSQL:**

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dashboard
SECRET_KEY=your-production-secret-key-at-least-32-chars
CORS_ORIGINS=https://yourdomain.com
SQL_ECHO=false
```

> **نکته:** `SECRET_KEY` باید یک رشته تصادفی بلند باشد. می‌توانید با این دستور تولید کنید:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(48))"
> ```

### ۳. اجرای سرور

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

سرور در `http://127.0.0.1:8000` بالا می‌آید.

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health Check: `http://127.0.0.1:8000/health`

### ۴. ایجاد کاربر اول (Admin)

از طریق Swagger UI (`/docs`) یا `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "full_name": "مدیر سیستم",
    "password": "strong-password",
    "role": "admin"
  }'
```

## دیتابیس نمونه (برای تست)

برای دیدن داشبورد با داده‌های آزمایشی (فاکتور، مطالبات، انبار، هزینه، تأمین‌کننده، پرداخت، فاکتور خرید، وظایف و ۳ کاربر) یک دیتابیس جدا به نام `example.db` بسازید. دیتابیس اصلی (`dev.db`) تغییر نمی‌کند:

```bash
cd backend
python seed_example.py
```

سپس سرور را روی آن اجرا کنید:

```powershell
# PowerShell
$env:DATABASE_URL="sqlite+aiosqlite:///./example.db"
uvicorn app.main:app --reload
```

```bash
# bash
DATABASE_URL=sqlite+aiosqlite:///./example.db uvicorn app.main:app --reload
```

| ایمیل | رمز | نقش |
|-------|-----|-----|
| `admin@example.com` | `admin1234` | مدیر سیستم |
| `manager@example.com` | `manager1234` | مدیر |
| `staff@example.com` | `staff1234` | کارمند |

> این اسکریپت جدول‌های مقصد را پاک و دوباره می‌سازد، پس فقط روی `example.db` بدون تأیید کار می‌کند. تاریخ فاکتورها نسبت به امروز ساخته می‌شود، بنابراین هر بار اجرا داده‌ها تازه است.

## راه‌اندازی Frontend

Frontend فایل‌های استاتیک HTML/CSS/JS است. برای توسعه می‌توانید با هر سرور استاتیک اجرا کنید:

### گزینه ۱: Python (ساده‌ترین)

```bash
cd frontend
python -m http.server 5500
```
سپس `http://127.0.0.1:5500` را باز کنید.

### گزینه ۲: VS Code Live Server

افزونه **Live Server** را نصب کنید، روی `index.html` راست‌کلیک → **Open with Live Server**.

### گزینه ۳: Nginx / Apache (Production)

فایل‌های پوشه `frontend/` را در دایرکتوری وب‌سرور کپی کنید.

> **تنظیم API_URL:** در `frontend/js/config.js` می‌توانید `API_URL` را تغییر دهید. اگر خالی باشد، فرض بر این است که Frontend و Backend هم‌منشأ (same-origin) هستند.

## ساختار پروژه

```
Rang/
├── backend/
│   ├── app/
│   │   ├── api/              # Endpoint های REST
│   │   │   ├── auth.py       # ثبت‌نام، ورود، JWT
│   │   │   ├── sales.py      # فاکتور فروش
│   │   │   ├── finance.py    # تراکنش‌های مالی
│   │   │   ├── inventory.py  # موجودی انبار
│   │   │   ├── upload.py     # آپلود اکسل فروش
│   │   │   ├── upload_expense.py
│   │   │   ├── upload_finance.py
│   │   │   ├── dashboard.py  # آمار داشبورد (فروش/مالی و کنترل)
│   │   │   ├── payments.py   # درخواست پرداخت، ریسک، تأیید
│   │   │   ├── purchase_invoices.py  # تطبیق سه‌طرفه
│   │   │   ├── suppliers.py, tasks.py, users.py, settings.py
│   │   ├── services/         # موتور ریسک، تنظیمات، دفتر فعالیت
│   │   ├── core/             # تنظیمات، امنیت، دیتابیس، اکسل، زمان
│   │   ├── models/           # مدل‌های SQLAlchemy
│   │   ├── schemas/          # اسکیمای Pydantic
│   │   └── main.py           # نقطه ورود FastAPI
│   ├── seed_example.py       # ساخت دیتابیس نمونه
│   ├── seed_control.py       # دادهٔ نمونهٔ ماژول کنترل
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html            # صفحه ورود
│   ├── dashboard.html        # داشبورد
│   ├── css/style.css, control.css
│   └── js/
│       ├── config.js         # تنظیمات API_URL
│       ├── auth.js           # مدیریت ورود
│       ├── scene.js          # صحنه‌های سه‌بعدی (Three.js)
│       ├── core.js           # API، مودال، لیست‌های جدول‌دار
│       ├── overview.js       # داشبورد (فروش و مالی / کنترل و ریسک)
│       ├── business.js       # فروش، مالی، انبار، آپلود
│       ├── control.js        # پرداخت، فاکتور خرید، تأمین‌کننده، وظایف
│       ├── admin.js          # گزارش‌ها، کاربران، تنظیمات
│       └── app.js            # مسیریابی و راه‌اندازی
└── README.md
```

## API Endpoints اصلی

| متد | مسیر | توضیح |
|-----|------|-------|
| POST | `/auth/register` | ثبت‌نام کاربر جدید |
| POST | `/auth/login` | ورود و دریافت توکن JWT |
| GET | `/auth/me` | اطلاعات کاربر جاری |
| POST | `/sales/` | ایجاد فاکتور فروش |
| GET | `/sales/` | لیست فاکتورهای فروش |
| POST | `/finance/` | ایجاد تراکنش مالی |
| GET | `/finance/` | لیست تراکنش‌های مالی |
| POST | `/upload/sales-excel` | آپلود فاکتورهای فروش از اکسل |
| POST | `/upload/expense-report` | آپلود گزارش هزینه از اکسل |
| POST | `/upload/receivables-excel` | آپلود حساب‌های دریافتنی |
| POST | `/upload/payables-excel` | آپلود مانده بستانکاری |
| POST | `/inventory/upload` | آپلود موجودی انبار |
| GET | `/inventory/` | لیست کالاهای انبار |
| GET | `/dashboard/summary` | آمار فروش و مالی داشبورد |
| GET | `/dashboard/control` | آمار کنترل و ریسک (هشدارها، سلامت، فعالیت‌ها) |
| GET/POST | `/payments/` | لیست (فیلتر) / ثبت درخواست پرداخت |
| POST | `/payments/{id}/approve`، `/payments/{id}/stop` | تأیید / توقف (مدیر به بالا) |
| GET/POST | `/purchase-invoices/` | فاکتور خرید و تطبیق |
| POST | `/purchase-invoices/{id}/resolve` | رفع مغایرت |
| GET/POST/PATCH | `/suppliers/`، `/suppliers/{id}` | تأمین‌کنندگان |
| POST | `/suppliers/{id}/verify-bank` | تأیید حساب بانکی |
| GET/POST | `/tasks/`، `/tasks/{id}/complete` | وظایف |
| GET/PATCH | `/users/`، `/users/{id}` | کاربران (مدیر سیستم) |
| GET/PUT | `/settings/` | قواعد و سقف‌های کنترل |
| POST | `/auth/change-password` | تغییر رمز کاربر جاری |
| GET | `/health` | بررسی سلامت سرور |

**احراز هویت:** تمام endpointها (به جز `/auth/*` و `/health`) نیاز به هدر `Authorization: Bearer <token>` دارند.

## ماژول کنترل و ریسک

این بخش ایدهٔ نسخهٔ نمایشی Rayad Business Control را به‌صورت واقعی روی همین بک‌اند پیاده می‌کند:

| بخش | کار |
|-----|-----|
| **کنترل پرداخت** | هر درخواست پرداخت امتیاز ریسک ۰ تا ۱۰۰ با دلیل می‌گیرد؛ تأیید یا توقف با ثبت یادداشت |
| **فاکتور خرید** | تطبیق مقدار رسیدشده با فاکتورشده؛ نتیجه: تأییدشده / بررسی / مغایرت |
| **تأمین‌کنندگان** | پروندهٔ شرکت، علامت پرریسک، تغییر حساب بانکی با تأیید مدیر |
| **کنترل عملکرد** | وظایف، سررسید، عقب‌افتاده‌ها و اولویت |
| **گزارش‌ها** | خلاصهٔ زنده، چاپ/PDF و خروجی CSV |
| **کاربران و تنظیمات** | نقش‌ها، قواعد کنترل، سقف‌های تأیید (فقط مدیر سیستم) |

**قواعد امتیاز ریسک** (قابل‌توضیح؛ هر کدام در تنظیمات قابل خاموش‌کردن است): مبلغ بیش از ۱.۵ یا ۲ برابر میانگین ۹۰ روز اخیر همان تأمین‌کننده، تأمین‌کنندهٔ بدون سابقه یا پرریسک، تغییر تأییدنشدهٔ حساب بانکی، پرداخت تکراری در ۷ روز، و مغایرت/نبود فاکتور برای سفارش. امتیاز فقط ناهنجاری را نشان می‌دهد و تصمیم با انسان است.

**دسترسی‌ها:**

| نقش | توانایی |
|-----|---------|
| کارمند (`staff`) | ثبت پرداخت/فاکتور/وظیفه/تأمین‌کننده و مشاهده |
| مدیر (`manager`) | تأیید یا توقف پرداخت تا سقف خودش، رفع مغایرت فاکتور، تأیید حساب بانکی |
| مدیر سیستم (`admin`) | همهٔ موارد + کاربران + تنظیمات + تأیید پرداخت‌های بزرگ یا پرریسک |

سقف‌های پیش‌فرض: تا ۵۰۰ میلیون تومان مدیر کافی است؛ بالاتر یا امتیاز ریسک ≥ ۷۰ فقط مدیر سیستم. از «تنظیمات کنترل» قابل تغییر است. منطقهٔ زمانی «امروز» با `TIMEZONE` در `.env` تنظیم می‌شود (پیش‌فرض `Asia/Tehran`).

## فرمت فایل‌های اکسل آپلودی

### فاکتور فروش (`/upload/sales-excel`)
ستون‌های مورد نیاز:
- **تاریخ** (شمسی، مثل `1405/07/02`)
- **نام مشتری**
- **خالص** (مبلغ)
- **باقی مانده فاکتور** (اختیاری)
- **نوع تسویه** (اختیاری)
- **شماره فاکتور** (اختیاری)

### گزارش هزینه (`/upload/expense-report`)
- **کد**
- **عنوان**
- **گردش بدهکار** (اختیاری)
- **گردش بستانکار** (اختیاری)
- **مانده بدهکار** (اختیاری)
- **مانده بستانکار** (اختیاری)

### حساب‌های دریافتنی (`/upload/receivables-excel`)
- **کد** (اختیاری)
- **عنوان** (نام طرف)
- **مانده** (مبلغ)

### مانده بستانکاری (`/upload/payables-excel`)
- **کد** (اختیاری)
- **عنوان** (نام طرف)
- **مانده بستانکار** (مبلغ)

### موجودی انبار (`/inventory/upload`)
- **کد کالا**
- **عنوان کالا**
- **موجودی** (تعداد)

## عیب‌یابی

### خطای اتصال به دیتابیس
- مطمئن شوید PostgreSQL در حال اجراست و `DATABASE_URL` درست است.
- برای SQLite: فایل `dev.db` در پوشه `backend/` ساخته می‌شود.

### خطای CORS در مرورگر
- `CORS_ORIGINS` در `.env` شامل مبدأ Frontend باشد (مثل `http://127.0.0.1:5500`).
- Backend باید با `--host 0.0.0.0` اجرا شود.

### توکن منقضی شده
- توکن‌ها پس از ۲۴ ساعت (پیش‌فرض) منقضی می‌شوند. دوباره لاگین کنید.
- `ACCESS_TOKEN_EXPIRE_MINUTES` در `.env` قابل تغییر است.

### ماژول `calamine` نصب نیست
برای خواندن فایل `.xls` قدیمی و `.xlsx`:
```bash
pip install python-calamine
```
بدون آن، فقط `openpyxl` برای `.xlsx` و `xlrd` برای `.xls` استفاده می‌شود.

## لایسنس

MIT

## در اپدیت جدید - v0.0.24
- سرعت دیتابیس بیشتر شه (بهینه شده) 🚀
- باگ ها فیکس شده 😎
