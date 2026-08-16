#!/usr/bin/env bash
# استقرارِ «Teams» روی سرور — گرفتنِ آخرین تغییرات از گیت و راه‌اندازیِ دوباره.
# اجرا از ریشه‌ی پروژه:  ./deploy.sh
set -euo pipefail

# برنچِ فعالِ توسعه/استقرار (کارها روی همین برنچ‌اند، نه main). قابلِ override:
#   ./deploy.sh <branch>
BRANCH="${1:-claude/invoices-reports-section-2lydte}"
SERVICE="${SERVICE:-teams}"         # نامِ سرویسِ systemd
cd "$(dirname "$0")"

echo "▶ گرفتنِ کد از گیت (origin/$BRANCH)…"
git fetch --prune origin
git checkout -B "$BRANCH" "origin/$BRANCH"   # سوییچ + همگام با ریموت (حتی اگر روی main باشد)

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
