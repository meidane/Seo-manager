# CLAUDE.md — راهنمای ریشه (همیشه لود می‌شود، لاغر نگه‌اش دار)

پلتفرم مدیریت پروژه‌های سئو. Django 5 + Vanilla JS (بدون بیلد، بدون DRF). RTL، تقویم شمسی، تم دارک شیشه‌ای.

> **جزئیات هر اپ در `CLAUDE.md` همان پوشه است** (فقط موقع کار روی آن اپ لود می‌شود).
> **دستورالعمل افزودن چیز جدید:** `docs/RECIPES.md` — قبل از هر feature بخوان.
> **قراردادها و تله‌ها:** `docs/CONVENTIONS.md`.

## نقشه‌ی اپ‌ها (یک خط هر کدام)
- `config/` — تنظیمات، urls ریشه، wsgi/asgi
- `core/` — پایه‌ها: TimeStampedModel, Attachment, ActivityLog, Holiday + jalali/daterange/crypto/htmlsan + templatetags + editor_upload
- `accounts/` — User سفارشی + Team، ورود/خروج
- `colleagues/` — Colleague (CRUD + آمار سینگل + جدول+اسپارک‌لاین)
- `projects/` — Project + Credential(رمزنگاری) + فایل‌ها؛ سینگل با تب‌ها
- `tasks/` — **قلب سیستم**: Task, TaskComment, TaskTypeDef/Field؛ api.py + مودال سراسری
- `calendarapp/` — تقویم شمسی (بدون مدل؛ منطق در calendar_logic.py) + دیت‌پیکر
- `dashboard/` — ویو تجمیعی
- `reports/` — Report/ReportItem (بدون snapshot، override، لینک عمومی مشتری)
- `finance/` — حسابداری (پایه): BankAccount, Category(بابت), Transaction(+ایمپورت اکسل), Payroll

## قوانین طلایی (نقض نکن)
1. **تاریخ‌ها در DB میلادی‌اند.** شمسی فقط در نمایش (`|jalali`) و ورودی (`parse_jalali`).
2. **رنگ فقط از متغیر CSS.** هیچ رنگ hard-code در CSS.
3. **استایل کامپوننت فقط در `static/css/style.css`.** `mockups/` صرفاً دیزاینِ استاتیک است، اپ از آن استایل نمی‌گیرد. (این دوبار تقویم/داشبورد را خراب کرد.)
4. **API با `JsonResponse`**، بدون DRF. الگوی `@login_required @require_http_methods([...])`.
5. **آمار با `annotate(filter=Q(...))`**، نه حلقه‌ی پایتونی.
6. **بازه‌ی زمانی با `DateRangeMixin`** (`core/daterange.py`) — در همه‌ی صفحات آماری.
7. **منبع واحد را تکرار نکن** (جدول زیر). خروجی ادیتور همیشه با `core.htmlsan.clean_html` پاکسازی شود.

## منبع‌های واحد (هرگز منطق موازی نساز)
| منبع | فایل |
|---|---|
| ذخیره‌ی فیلد تسک (create/update) | `tasks/api.py: apply_fields` |
| نمایش فیلد بر اساس نوع (مودال) | `static/js/task-schema.js` |
| داده‌ی مودال تسک (پروژه/همکار/انواع) | `tasks/api.py: form_data` → `/tasks/api/formdata/` |
| بازه‌ی سراسری | `core/daterange.py: DateRangeMixin` |
| گروه‌بندی نوع در گزارش | `reports/models.py: BUCKETS` |
| فیلدهای قابل‌نمایش به مشتری | `reports/models.py: CLIENT_FIELDS` + `Report.visible_fields` |
| پاکسازی HTML ادیتور | `core/htmlsan.py: clean_html` |
| رنگ/برچسب نوع تسک | `tasks/models.py: Task.type_label / color_rgb` (+ `TYPE_COLORS`) |
| ادیتور غنی | `static/js/richtext.js` (کلاس `rich-editor`) |
| دیت‌پیکر شمسی | `static/js/datepicker.js` (کلاس `jdate`) |

## دستورهای کلیدی
```bash
python manage.py migrate
python manage.py seed_holidays 1405
python manage.py createsuperuser        # یا admin/admin1234
python manage.py runserver
python manage.py check                  # قبل از هر کامیت
python manage.py collectstatic --noinput  # فقط برای تست مرورگر/تولید
```
کاربر تست: `admin` / `admin1234`. DB پیش‌فرض SQLite (متغیرها در `.env`).

## کجا نگاه نکن (نویز)
- `mockups/` → فقط پیش‌نمایش دیزاین، نه کد اپ
- `static/vendor/` → کتابخانه (TinyMCE, Vazirmatn)
- `*/migrations/` → تولیدشده
- `staticfiles/`, `media/`, `db.sqlite3` → گیت‌ایگنور

## تله‌های واقعی (که به ما باگ زدند)
1. استایل کامپوننت که فقط در `mockups/` بود نه `style.css` → صفحه بی‌استایل. **همیشه در `style.css`.**
2. `TimeField` با پیش‌فرض رشته → `strftime` ندارد. از `default=time(8,0)`.
3. اپ تکراری در `INSTALLED_APPS` → خطای «labels aren't unique».
4. نبودِ `select_related('type_def')` → N+1 در لیست/تقویم.
5. `<option>` نامرئی → نیاز به پس‌زمینه‌ی تیره (رفع‌شده در style.css).
6. push فقط با URL کوچک‌حروف `meidane/seo-manager`.
7. panic گذرای `cryptography` → `pip install --force-reinstall cryptography` یا اجرای دوباره.
8. **تست:** توکن CSRF بعد از لاگین می‌چرخد؛ برای POST فرم از مقدارِ کوکیِ `csrftoken` فعلی استفاده کن.

## انضباط نگه‌داری (مهم)
**به‌روزرسانی هینت بخشی از همان تغییر است.** وقتی فیلد/الگو/تله/منبع‌واحدِ جدید اضافه شد،
در همان کامیت `CLAUDE.md`/`RECIPES` مربوط را به‌روز کن. **Definition of Done هر تغییر:**
`check` تمیز → migrate (اگر مدل) → تست سریع → هینت به‌روز → commit/push.
قانون فایل بزرگ: هر فایل که از ~۴۰۰ خط رد شد، بالایش یک بلوک ایندکس بگذار.
