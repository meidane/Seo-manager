# سئوپنل — پلتفرم مدیریت پروژه‌های سئو

پلتفرم مدیریت پروژه‌های سئو با Django، تم دارک شیشه‌ای (Glassmorphism)، RTL و
تقویم شمسی. بدون بیلد فرانت، بدون DRF، بدون ادمین جنگو برای کار روزمره.

> **برای ادامه‌ی توسعه، اول [`HINTS.md`](./HINTS.md) را بخوان** — نقشه‌ی اتصال
> گام‌های بعد و تله‌هایی که نباید تکرار شوند آنجاست.

## وضعیت پیاده‌سازی

| گام | بخش | وضعیت |
|---|---|---|
| ۰ | پایه (Django، مدل‌های core، تاریخ شمسی، style.css، base.html، app.js) | ✅ |
| ۱ | همکاران — CRUD کامل | ✅ |
| ۲ | پروژه‌ها — CRUD + دسترسی‌های رمزنگاری‌شده + تب‌ها | ✅ |
| ۳ | تسک‌ها — مدل کامل، مودال چندحالته، لیست/کانبان، عملیات گروهی، بازبینی | ✅ |
| ۴ | تقویم شمسی — ماه، ناوبری AJAX، drag تغییر تاریخ، workload API | ✅ (هفته/لیست: TODO) |
| ۵ | داشبورد — کارت‌ها، هشدارها، جدول‌های تجمیعی، فید بازبینی، نمودار میله‌ای | ✅ (تب‌ها/دونات/هیت‌مپ: TODO) |
| ۶ | تکمیل آمار سینگل پروژه/همکار + تب تقویم + میان‌بر بازبینی | ✅ |
| ۷ | گزارش‌دهی — بدون snapshot، override، گروه‌بندی نوع، نمایش قابل‌تنظیم مشتری، لینک عمومی | ✅ |
| ۸–۹ | حسابداری، جمع‌بندی + نوع تسک سفارشی | ⬜ (نقطه‌ی اتصال در HINTS) |

**ماک‌آپ استاتیک همه‌ی صفحات** برای بازبینی دیزاین: پوشه‌ی `mockups/` را باز کن
(`index.html`). این‌ها مرجع بصری‌اند و مطابق `designpreview.html` ساخته شده‌اند.

## راه‌اندازی

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # مقادیر را پر کن (به‌ویژه SECRET_KEY و FERNET_KEY)
python manage.py migrate
python manage.py seed_holidays 1405
python manage.py createsuperuser
python manage.py runserver
```

## ساختار

```
config/         تنظیمات، URLها، WSGI/ASGI
core/           TimeStampedModel, Attachment, ActivityLog, Holiday,
                jalali.py, daterange.py (بازه‌ی سراسری), crypto.py (Fernet),
                templatetags/seo_extras.py (jalali|money|timeago|fa_digits|dictkey)
accounts/       User سفارشی + Team، ورود/خروج
colleagues/     Colleague — CRUD
projects/       Project + Credential (رمزنگاری‌شده) — CRUD + تب‌ها + API دسترسی‌ها
tasks/          Task + TaskComment — مدل قلب سیستم، api.py (JSON), views.py (لیست/کانبان/بازبینی)
calendarapp/    منطق ماه شمسی (calendar_logic.py) + ویو صفحه + API تقویم/workload
dashboard/      ویو تجمیعی داشبورد
templates/      base.html + components/ + هر اپ
static/         css/style.css، js/{app,tasks,task-schema,calendar-page}.js
mockups/        پیش‌نمایش استاتیک همه‌ی صفحات (HTML/CSS، داده‌ی ساختگی)
```

## اصول کلیدی (خلاصه — کامل در HINTS)

- **تاریخ‌ها در DB میلادی‌اند؛** تبدیل شمسی فقط در نمایش/ورودی.
- **بازه‌ی زمانی سراسری** (`DateRangeMixin`) روی همه‌ی صفحات آماری اثر می‌گذارد و
  در session می‌ماند.
- **task-schema.js** منبع واحد «کدام فیلد برای کدام نوع تسک»؛ هم مودال هم منطق فرانت.
- **آمار داشبورد با یک کوئری تجمیعی** (`annotate + filter=Q`)، نه حلقه‌ی پایتونی.
- **هیچ رنگ hard-code در CSS نیست** — فقط متغیر، آماده‌ی حالت روشن.

## API (خلاصه)

```
# تسک
POST   /tasks/api/                     ایجاد
GET|PATCH|DELETE /tasks/api/<id>/      خواندن برای مودال / ویرایش / حذف
PATCH  /tasks/api/<id>/status/         تغییر سریع وضعیت (کانبان)
PATCH  /tasks/api/<id>/review/         تایید / نیاز به اصلاح
POST   /tasks/api/<id>/comments/       کامنت
POST   /tasks/api/bulk/                عملیات گروهی (تاریخ نسبی/مطلق، مسئول، وضعیت...)
# تقویم
GET    /calendar/api/?year=&month=&project=&assignee=&type=
GET    /calendar/api/workload/?assignee=&year=&month=
# پروژه (دسترسی‌ها)
POST   /projects/api/<id>/credentials/  |  GET /projects/api/credentials/<id>/reveal/
```
