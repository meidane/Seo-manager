# CONVENTIONS — قراردادها و تله‌ها (چیزهایی که از کد پیدا نمی‌شوند)

## قراردادهای کد
- **تاریخ:** DB میلادی؛ شمسی فقط نمایش/ورودی. هرگز شمسی ذخیره نکن.
- **رنگ:** فقط متغیر CSS (`var(--...)`). آماده‌ی حالت روشن با `[data-theme="light"]`.
- **API:** `JsonResponse` + دکوراتور `@login_required @require_http_methods([...])`. بدون DRF.
- **فرانت:** از `App.fetchJSON/toast/openModal/confirm` (در `static/js/app.js`). CSRF خودکار.
- **آمار:** `annotate(filter=Q())`/`aggregate`، نه حلقه. `select_related` برای FKهای پرتکرار.
- **بازه:** `DateRangeMixin` + `range_context()` در تمپلیت (`range_start_fa` و…).
- **HTML ادیتور:** موقع ذخیره `core.htmlsan.clean_html`.
- **فارسی:** اعداد نمایش با `|fa_digits`؛ پول با `|money`؛ زمان نسبی `|timeago`.
- **نام‌گذاری:** کلاس‌های وضعیت `t-ok/t-warn/t-bad/t-info/t-mute`؛ کارت شیشه‌ای `.glass .card`.

## استایل (مهم‌ترین منبع باگ ما)
- **هر کلاس CSS که اپ استفاده می‌کند باید در `static/css/style.css` باشد.**
  `mockups/assets/style.css` نسخه‌ی دیزاین است و اپ از آن استایل نمی‌گیرد.
  قبل از استفاده از یک کلاس در تمپلیت، مطمئن شو در `style.css` تعریف شده
  (`grep '^\.classname' static/css/style.css`).
- بعد از تغییر static برای تست مرورگر: `collectstatic --noinput`.

## تله‌ها (که واقعاً باگ زدند)
| تله | راه‌درست |
|---|---|
| استایل فقط در mockups | همیشه در `static/css/style.css` |
| `TimeField(default='08:00')` | `default=time(8,0)` |
| اپ تکراری در INSTALLED_APPS | یک‌بار |
| N+1 در لیست تسک/تقویم | `select_related(...,'type_def')` |
| `<option>` نامرئی | پس‌زمینه‌ی تیره (در style.css، رفع‌شده) |
| CSRF کهنه در تست | مقدار کوکی `csrftoken` فعلی را بفرست |
| `cryptography` panic گذرا | `pip install --force-reinstall cryptography` |
| push 403 | remote کوچک‌حروف `meidane/seo-manager` |

## Git / تحویل
- برنچ کاری: `claude/base-resources-nwomol`. push با `-u origin <branch>` (retry با backoff).
- **Definition of Done هر تغییر:** `manage.py check` تمیز → migrate (اگر مدل) → تست سریع →
  به‌روزرسانی `CLAUDE.md`/`RECIPES` مرتبط → commit → push. local باید = remote.
- کامیت‌ها فارسی و توصیفی. `db.sqlite3/staticfiles/media/.env` گیت‌ایگنور — کامیت نشوند.

## وضعیت کلی (به‌روز نگه دار)
ساخته‌شده: core, accounts, colleagues, projects, tasks (+انواع سفارشی), calendarapp
(+دیت‌پیکر), dashboard, reports. ادیتور TinyMCE + آپلود فایل پروژه.
**بعدی:** finance (اپ مجزا — فرانتش در `mockups/finance*.html` آماده است).
باقی‌مانده‌ی ریز: نمای هفته/لیست تقویم، اتصال کارت مالی داشبورد به finance، نمایش مقادیر
custom در جدول‌ها. (انجام‌شده: بازبینی #۱۲، پیش‌نمایش گزارش #۶، انواع پیش‌فرض در مدیریت #۱۰.)
