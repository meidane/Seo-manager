# سئوپنل — پلتفرم مدیریت پروژه‌های سئو

پلتفرم مدیریت پروژه‌های سئو با Django، تم دارک شیشه‌ای، RTL و تقویم شمسی.

> **وضعیت:** گام ۰ (پایه) پیاده‌سازی شده — اسکلت، احراز هویت، سیستم طراحی،
> بازه‌ی زمانی سراسری و مدل‌های پایه. اپ‌های پروژه‌ها/همکاران/تسک‌ها/تقویم/گزارش‌ها
> در گام‌های بعد اضافه می‌شوند.

## راه‌اندازی

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # مقادیر را پر کن
python manage.py migrate
python manage.py seed_holidays 1405
python manage.py createsuperuser
python manage.py runserver
```

## آنچه در گام پایه ساخته شد

- **config/** — تنظیمات Django (SQLite توسعه / PostgreSQL تولید)، URLها، WSGI/ASGI
- **accounts/** — مدل `User` سفارشی + `Team` (آماده‌ی چندتیمی فاز ۳)، ورود/خروج
- **core/**
  - مدل‌های پایه: `TimeStampedModel`، `Attachment` (GenericFK)، `ActivityLog`، `Holiday`
  - ابزار تاریخ شمسی (`jalali.py`) — تبدیل میلادی↔شمسی فقط در لایه‌ی نمایش
  - `DateRangeMixin` — بازه‌ی زمانی سراسری با ذخیره در session و بازه‌ی قبلی برای مقایسه
  - تمپلیت‌فیلترها: `jalali`، `jalali_long`، `money`، `timeago`، `fa_digits`
  - دستور `seed_holidays` + صفحه‌ی مدیریت تعطیلات `/settings/holidays/`
- **dashboard/** — ویو داشبورد با اسکلت کارت‌ها (اعداد در گام داشبورد پر می‌شوند)
- **static/css/style.css** — کل سیستم طراحی بخش ۲، فقط بر پایه‌ی متغیرهای CSS
- **static/js/app.js** — `fetchJSON`، `toast`، `openModal`/`closeModal`، `confirm`، CSRF
- **templates/** — `base.html` (سایدبار + هدر + انتخابگر بازه)، کامپوننت‌ها، ورود، تعطیلات

## قانون تاریخ

همه‌ی تاریخ‌ها در دیتابیس **میلادی** ذخیره می‌شوند؛ تبدیل شمسی فقط در نمایش و ورودی.
