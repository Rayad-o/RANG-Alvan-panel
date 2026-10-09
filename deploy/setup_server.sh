#!/usr/bin/env bash
# نصب Rang روی سرور اوبونتو/دبیان (با کاربر root اجرا شود).
#
# استفاده:
#   bash setup_server.sh /root/rang.tar.gz
#
# کارها: نصب پیش‌نیازها، ساخت کاربر سرویس، venv، فایل .env با SECRET_KEY تصادفی،
# سرویس systemd و پراکسی nginx روی پورت ۸۰۸۰ (قابل تغییر؛ سایت‌های دیگر را تغییر نمی‌دهد). دیتابیس: SQLite در /opt/rang/data
set -euo pipefail

ARCHIVE="${1:-/root/rang.tar.gz}"
# پورت‌ها قابل تغییر هستند تا با برنامه‌های دیگر روی همین سرور (مثلاً پورت ۸۰ و ۸۰۰۰) تداخل نکنند
APP_PORT="${APP_PORT:-8765}"        # پورت داخلی uvicorn (فقط localhost)
PUBLIC_PORT="${PUBLIC_PORT:-8080}"  # پورت عمومی nginx برای Rang
APP_DIR=/opt/rang
DATA_DIR=$APP_DIR/data
SERVICE_USER=rang

[ "$(id -u)" -eq 0 ] || { echo "این اسکریپت باید با root اجرا شود"; exit 1; }
[ -f "$ARCHIVE" ] || { echo "فایل $ARCHIVE پیدا نشد"; exit 1; }

# جلوگیری از تداخل: اگر پورت‌ها اشغال‌اند (به‌جز سرویس خود rang در به‌روزرسانی) متوقف شو
if ! systemctl is-active --quiet rang; then
    for port in "$APP_PORT" "$PUBLIC_PORT"; do
        if ss -ltn "( sport = :$port )" | grep -q LISTEN; then
            echo "پورت $port روی این سرور اشغال است. با APP_PORT/PUBLIC_PORT=... پورت دیگری بدهید."
            exit 1
        fi
    done
fi

echo "==> نصب پیش‌نیازها"
export DEBIAN_FRONTEND=noninteractive
NGINX_WAS_INSTALLED=0
command -v nginx >/dev/null 2>&1 && NGINX_WAS_INSTALLED=1
apt-get update -y
apt-get install -y python3 python3-venv python3-pip nginx curl

PY=python3
if ! $PY -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "پایتون $($PY -V) قدیمی است؛ نسخهٔ ۳.۱۱ یا بالاتر لازم است (اوبونتو ۲۴.۰۴ / دبیان ۱۲)."
    exit 1
fi

echo "==> ساخت کاربر سرویس و پوشه‌ها"
id "$SERVICE_USER" >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
mkdir -p "$APP_DIR" "$DATA_DIR"

echo "==> استخراج فایل‌ها (دیتابیس و .env موجود دست‌نخورده می‌ماند)"
tar -xzf "$ARCHIVE" -C "$APP_DIR"

echo "==> محیط مجازی و وابستگی‌ها"
$PY -m venv "$APP_DIR/backend/.venv"
"$APP_DIR/backend/.venv/bin/pip" install --upgrade pip
"$APP_DIR/backend/.venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

ENV_FILE=$APP_DIR/backend/.env
if [ ! -f "$ENV_FILE" ]; then
    echo "==> ساخت .env (SECRET_KEY تصادفی)"
    SERVER_IP=$(curl -s -m 5 https://api.ipify.org || hostname -I | awk '{print $1}')
    cat > "$ENV_FILE" <<EOF
DATABASE_URL=sqlite+aiosqlite:///$DATA_DIR/rang.db
SECRET_KEY=$($PY -c 'import secrets; print(secrets.token_urlsafe(48))')
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://$SERVER_IP:$PUBLIC_PORT
TIMEZONE=Asia/Tehran
SQL_ECHO=false
EOF
    chmod 600 "$ENV_FILE"
fi

chown -R "$SERVICE_USER":"$SERVICE_USER" "$APP_DIR"

echo "==> سرویس systemd"
cat > /etc/systemd/system/rang.service <<EOF
[Unit]
Description=Rang management dashboard
After=network.target

[Service]
User=$SERVICE_USER
WorkingDirectory=$APP_DIR/backend
ExecStart=$APP_DIR/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $APP_PORT --proxy-headers
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now rang
systemctl restart rang

echo "==> nginx"
cat > /etc/nginx/sites-available/rang <<EOF
server {
    listen $PUBLIC_PORT;
    server_name _;
    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF
ln -sf /etc/nginx/sites-available/rang /etc/nginx/sites-enabled/rang
# سایت‌های موجود دست‌نخورده می‌مانند. فقط اگر nginx را همین الان خودمان نصب کردیم،
# سایت پیش‌فرضش (پورت ۸۰) حذف می‌شود تا با برنامه‌ای که پورت ۸۰ را دارد تداخل نکند.
if [ "$NGINX_WAS_INSTALLED" -eq 0 ]; then
    rm -f /etc/nginx/sites-enabled/default
    nginx -t
    systemctl enable nginx
    systemctl restart nginx
else
    nginx -t
    systemctl reload nginx   # reload بدون قطع سایت‌های دیگر
fi

sleep 3
echo "==> بررسی سلامت"
curl -fsS http://127.0.0.1:$APP_PORT/health && echo
echo
echo "نصب تمام شد. آدرس: http://$(curl -s -m 5 https://api.ipify.org || hostname -I | awk '{print $1}'):$PUBLIC_PORT"
echo "اگر فایروال (ufw) فعال است: ufw allow $PUBLIC_PORT/tcp"
echo "ساخت اولین کاربر (مدیر سیستم) — رمز را خودتان انتخاب کنید:"
echo "  curl -X POST http://127.0.0.1:$APP_PORT/auth/register -H 'Content-Type: application/json' \\"
echo "       -d '{\"email\":\"admin@yourcompany.com\",\"full_name\":\"مدیر سیستم\",\"password\":\"<رمز-قوی>\"}'"
