# استقرار روی سرور

سرور هدف: اوبونتو ۲۴.۰۴ (یا دبیان ۱۲) با پایتون ۳.۱۱ یا بالاتر. همهٔ دستورها را خودتان از PowerShell ویندوز اجرا کنید.

## ۱) ساخت بستهٔ پروژه (روی ویندوز، از ریشهٔ پروژه)

بدون `.venv`، دیتابیس‌ها و `.env` محلی:

```powershell
cd C:\Users\malig\Documents\Rang
tar -czf rang.tar.gz --exclude=.venv --exclude=__pycache__ --exclude=*.db --exclude=.env --exclude=.git backend frontend
```

## ۲) ارسال به سرور

```powershell
scp rang.tar.gz deploy\setup_server.sh root@185.239.0.76:/root/
```

(رمز را همین‌جا خودتان وارد کنید.)

## ۳) نصب

```powershell
ssh root@185.239.0.76 "bash /root/setup_server.sh /root/rang.tar.gz"
```

> **توجه:** روی این سرور از قبل برنامهٔ دیگری روی پورت ۸۰ اجرا می‌شود. اسکریپت آن را تغییر نمی‌دهد و Rang را روی پورت **۸۰۸۰** (و uvicorn را روی ۸۷۶۵ داخلی) بالا می‌آورد. برای پورت دیگر: `APP_PORT=... PUBLIC_PORT=... bash /root/setup_server.sh ...`

در پایان آدرس برنامه (`http://185.239.0.76:8080`) و دستور ساخت اولین مدیر چاپ می‌شود.

## ۴) ساخت اولین مدیر سیستم

روی سرور (`ssh root@185.239.0.76`) اجرا کنید و رمز قوی خودتان را بگذارید. اولین ثبت‌نام خودکار `admin` می‌شود و بعد از آن ثبت‌نام باز بسته است:

```bash
curl -X POST http://127.0.0.1:8765/auth/register -H 'Content-Type: application/json' -d '{"email":"admin@yourcompany.com","full_name":"مدیر سیستم","password":"<رمز-قوی>"}'
```

## به‌روزرسانی بعدی

بستهٔ جدید را بسازید و بفرستید و دوباره `setup_server.sh` را اجرا کنید. دیتابیس (`/opt/rang/data`) و `.env` سرور دست‌نخورده می‌مانند.

## نکته‌های امنیتی

- **رمز root که در چت فرستادید را همین حالا عوض کنید** (`passwd` روی سرور)، و بهتر است ورود با کلید SSH را فعال و ورود با رمز را غیرفعال کنید.
- روی IP بدون دامنه فقط HTTP ممکن است: توکن و رمز بدون رمزنگاری رد می‌شوند. برای استفادهٔ واقعی یک دامنه به سرور وصل کنید و HTTPS بگیرید (`apt install certbot python3-certbot-nginx` و `certbot --nginx`)؛ بعد `CORS_ORIGINS` را در `/opt/rang/backend/.env` به `https://دامنه` تغییر دهید و `systemctl restart rang` بزنید.
- اگر فایروال فعال است، پورت ۸۰۸۰ را باز کنید: `ufw allow 8080/tcp`.
- دیتابیس SQLite برای شروع و تیم کوچک مناسب است. برای کاربر زیاد، PostgreSQL را در `DATABASE_URL` تنظیم کنید.
- دادهٔ نمونه (`example.db`) روی سرور نصب نمی‌شود. اگر خواستید فقط برای تست: `cd /opt/rang/backend && sudo -u rang .venv/bin/python seed_example.py` و سپس `DATABASE_URL` را موقتاً به `example.db` بدهید.
