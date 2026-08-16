#!/usr/bin/env bash
# استقرارِ «Teams» روی سرور — گرفتنِ آخرین تغییرات از گیت و راه‌اندازیِ دوباره.
# اجرا از ریشه‌ی پروژه:  ./deploy.sh
set -euo pipefail

BRANCH="${1:-main}"                 # ./deploy.sh <branch>  (پیش‌فرض: main)
SERVICE="${SERVICE:-teams}"         # نامِ سرویسِ systemd
cd "$(dirname "$0")"

echo "▶ گرفتنِ کد از گیت (origin/$BRANCH)…"
git fetch --prune origin
git reset --hard "origin/$BRANCH"   # دقیقاً برابرِ ریموت (تغییرِ محلی نگه داشته نمی‌شود)

echo "▶ فعال‌سازیِ venv و نصبِ وابستگی‌ها…"
source .venv/bin/activate
pip install -r requirements.txt -q

echo "▶ مهاجرت دیتابیس…"
python manage.py migrate --noinput

echo "▶ جمع‌آوریِ استاتیک…"
python manage.py collectstatic --noinput

echo "▶ بررسیِ سلامت…"
python manage.py check --deploy || true

echo "▶ راه‌اندازیِ دوباره‌ی سرویس…"
sudo systemctl restart "$SERVICE"

echo "✅ استقرارِ Teams کامل شد ($(git rev-parse --short HEAD))"
