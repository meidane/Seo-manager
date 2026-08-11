# CLAUDE.md — راهنمای ریشه (همیشه لود می‌شود، لاغر نگه‌اش دار)

پلتفرم مدیریت پروژه‌های سئو. Django 5 + Vanilla JS (بدون بیلد، بدون DRF). RTL، تقویم شمسی، تم دارک شیشه‌ای.

> **جزئیات هر اپ در `CLAUDE.md` همان پوشه است** (فقط موقع کار روی آن اپ لود می‌شود).
> **دستورالعمل افزودن چیز جدید:** `docs/RECIPES.md` — قبل از هر feature بخوان.
> **قراردادها و تله‌ها:** `docs/CONVENTIONS.md`.

## نقشه‌ی اپ‌ها (یک خط هر کدام)
- `config/` — تنظیمات، urls ریشه، wsgi/asgi
- `core/` — پایه‌ها: TimeStampedModel, Attachment, ActivityLog, Holiday, ColumnConfig(+`columns.py` کاتالوگ) + jalali/daterange/crypto/htmlsan + templatetags + editor_upload
- `accounts/` — هویتِ چندشرکتی: Organization→Team→زیرمجموعه، Membership/نقشِ سفارشی، دعوت‌نامه(Invite)، صفحه‌ی افراد (`docs/PLATFORM.md`)
- `colleagues/` — Colleague (CRUD + آمار سینگل + جدول+اسپارک‌لاین + مدیر/needs_review + دسترسی به سیستم)
- `projects/` — Project + Credential(رمزنگاری) + فایل‌ها + `members`(گیتِ دسترسیِ واقعی)؛ سینگل با تب‌ها
- `tasks/` — **قلب سیستم**: Task, TaskComment, TaskTypeDef/Field؛ api.py + مودال سراسری
- `calendarapp/` — تقویم شمسی (بدون مدل؛ منطق در calendar_logic.py) + دیت‌پیکر
- `dashboard/` — ویو تجمیعی
- `reports/` — Report/ReportItem (بدون snapshot، override، لینک عمومی مشتری)
- `finance/` — حسابداری (پایه): BankAccount, Category(بابت), Transaction(+ایمپورت اکسل), Payroll
- `seo/` — بستهٔ عمودیِ سئو: `seed_seo` (۴ نوع تسکِ سئوِ کاملاً سفارشی) + ردیابیِ رتبهٔ کلمات
  کلیدی (مدل + API برای افزونهٔ مرورگر). الگوی «بسته برای هر شرکت» — برای مشتریِ بعدی یک اپِ مشابه بساز.
- `rank-tracker-extension/` — **افزونهٔ کروم** (MV3، خارج از جنگو)، سازگار با `seo/api.py`.
  جزئیات در `seo/CLAUDE.md`، بخشِ «افزونهٔ مرورگر».

## قوانین طلایی (نقض نکن)
1. **تاریخ‌ها در DB میلادی‌اند.** شمسی فقط در نمایش (`|jalali`) و ورودی (`parse_jalali`).
2. **رنگ فقط از متغیر CSS.** هیچ رنگ hard-code در CSS.
3. **استایل کامپوننت فقط در `static/css/style.css`.** `mockups/` صرفاً دیزاینِ استاتیک است، اپ از آن استایل نمی‌گیرد. (این دوبار تقویم/داشبورد را خراب کرد.)
4. **API با `JsonResponse`**، بدون DRF. الگوی `@login_required @require_http_methods([...])`.
5. **آمار با `annotate(filter=Q(...))`**، نه حلقه‌ی پایتونی.
6. **بازه‌ی زمانی با `DateRangeMixin`** (`core/daterange.py`) — در همه‌ی صفحات آماری.
7. **منبع واحد را تکرار نکن** (جدول زیر). خروجی ادیتور همیشه با `core.htmlsan.clean_html` پاکسازی شود.
8. **چندشرکتی (tenant):** مدل‌های اصلی به سازمان اسکوپ‌اند. `Model.objects` = فیلترشده به
   سازمانِ جاری؛ `Model.all_objects` = بدون فیلتر (migration/command/عمومی). جزئیات: `accounts/CLAUDE.md` + `docs/PLATFORM.md`.

## منبع‌های واحد (هرگز منطق موازی نساز)
| منبع | فایل |
|---|---|
| ذخیره‌ی فیلد تسک (create/update) | `tasks/api.py: apply_fields` |
| فیلدهای اختصاصیِ نوع در مودال (نه هسته‌ای) | `TaskTypeDef.fields` → `tasks.js: renderCustom` (هسته فقط ۱۰ فیلد عمومی دارد؛ `task-schema.js` فقط fallback برچسب/رنگِ tech/other) |
| داده‌ی مودال تسک (پروژه/همکار/انواع) | `tasks/api.py: form_data` → `/tasks/api/formdata/` |
| بازه‌ی سراسری | `core/daterange.py: DateRangeMixin` |
| کاتالوگِ ستون‌های قابل‌سفارشی‌سازی (تسک/پروژه/همکار) | `core/columns.py: get_catalog/get_columns/cell_value` + `core/models.py: ColumnConfig` + تگ `{% column_cell %}` |
| اتصالِ اپ/افزونهٔ بیرونی/AI به API | **توکنِ API** (`accounts.APIToken`، هدرِ `Authorization: Token xxx`، از `/settings/api-tokens/`) — نه سشن+کوکی؛ SameSite=Lax کوکیِ سشن را در fetchِ کراس‌سایتِ افزونه نمی‌فرستد. الگو: `seo/api.py: token_required` / `token_or_login_required`. |
| گروه‌بندی نوع در گزارش | `reports/models.py: BUCKETS` |
| فیلدهای قابل‌نمایش به مشتری | `reports/models.py: CLIENT_FIELDS` + `Report.visible_fields` |
| پاکسازی HTML ادیتور | `core/htmlsan.py: clean_html` |
| رنگ/برچسب نوع تسک | `tasks/models.py: Task.type_label / color_rgb` (+ `TYPE_COLORS`) |
| KPI (تعریف/امتیاز/سقف) | `tasks/models.py: TaskTypeKPI/KPIChecklistItem/TaskKPIScore` |
| تکرارِ تسک (تولید تنبل) | `tasks/recurrence.py` + `RecurrenceRule` |
| ادیتور غنی | `static/js/richtext.js` (کلاس `rich-editor`) |
| دیت‌پیکر شمسی | `static/js/datepicker.js` (کلاس `jdate`) |
| چکِ دسترسیِ سازمانی در ویو/API | `accounts/access.py: require_perm/has_perm` |
| فهرستِ id پروژه‌های قابل‌دیدنِ کاربرِ جاری | `projects/access.py: accessible_project_ids` |
| دعوت‌نامه‌ی در انتظار (نه عضویتِ فوری) | `accounts/models.py: Invite` (+ `docs/PLATFORM.md`) |
| نوارِ تبِ صفحاتِ تنظیمات | `templates/settings/_nav.html` (کلاسِ CSS: `.settings-nav`) |

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
9. `QuerySet.update()` یک `int` برمی‌گرداند نه tuple — `n, _ = qs.update(...)` ارور می‌دهد.
10. انواعِ تسکِ built-inِ سئویی (انتشار/آپدیت/رپورتاژ/لینک‌سازی) بازنشسته شدند؛ فقط `tech`/`other`
    عمومی مانده‌اند و بستهٔ `seo/` جایگزینِ کاملاً سفارشی‌شان است. فیلترِ نوع در لیست/تقویم
    دیگر با `task_type` نیست، با `type_def` (id) — `?type=` قدیمی فقط fallback است.
11. برای اتصالِ بیرونی (افزونه/AI) هرگز به کوکیِ سشن تکیه نکن — `SameSite=Lax` آن را در
    fetchِ کراس‌سایت نمی‌فرستد، حتی اگر همان مرورگرِ لاگین‌شده باشد. توکنِ API استفاده کن.
12. `ColumnConfig`: نبودِ رکورد = پیش‌فرض؛ رکوردِ خالی = **واقعاً هیچ‌کدام**، نه پیش‌فرض
    (باگِ قبلی: `if cfg and cfg.keys` این دو را قاطی می‌کرد و ذخیره‌ی خالی بی‌اثر می‌شد).
13. `Membership.perms` برای مالک `{'*'}` است، ولی تمپلیت‌ها `{% if 'x' in org_perms %}`
    رشته‌ی دقیق می‌خواهند — سرورساید همیشه با `.can(perm)` چک کن (نه `in` روی `perms`
    خام)؛ در context processor `'*'` به `set(PERMS)` باز شده تا لینک‌های گیت‌شده برای
    مالک هم دیده شوند.
14. `accessible_project_ids(request)` می‌تواند `None` (بدونِ محدودیت) یا لیست برگرداند —
    همیشه `if ids is not None: qs = qs.filter(...)`؛ چک کردنِ `if ids:` اشتباه است چون
    لیستِ خالیِ معتبر (کاربرِ بدونِ colleague) را هم فیلتر می‌کند.
15. کاربرِ لاگین‌شده‌ی بدونِ سازمان (دعوتی تازه، هنوز قبول نکرده) با `OrgRequiredMiddleware`
    به `/invites/` می‌افتد؛ مسیرِ جدیدی که باید بدونِ سازمان هم در دسترس باشد را به
    `_ORG_LESS_ALLOWED` در `accounts/tenancy.py` اضافه کن، وگرنه ریدایرکت‌لوپ می‌شود.
16. **باگِ جدی (رفع‌شده):** `own_tasks_only` یک محدودیت است نه یک قابلیت — نباید با
    ویلدکارد `'*'` مشتق شود. مالک (`Membership.perms` لفظاً `{'*'}`) قبلاً به‌خاطرِ
    `'*' in p or perm in p` در `Membership.can()` به‌اشتباه «فقط تسک‌های خودش» تلقی
    می‌شد؛ چون مالک معمولاً Colleagueِ وصل ندارد، همه‌ی تسک‌ها برایش ناپدید می‌شدند
    (ساخت/ویرایش/دیدنِ تسک همه خراب به‌نظر می‌رسید). `Membership.can()` الان
    `own_tasks_only` را همیشه صریح چک می‌کند، نه از ویلدکارد. اگر پرمیشنِ محدودکننده‌ی
    مشابهی اضافه کردی (نه افزاینده)، همین الگو را رعایت کن.
17. مودالِ سراسری (`app.js: openModal`) با کلیکِ بیرون فقط وقتی می‌بندد که چیزی توی
    فرم تغییر نکرده باشد (`root.dataset.dirty`، با اولین `input`/`change` ست می‌شود)؛
    اگر تغییر داده شده، فقط دکمه‌ی × یا انصراف می‌بندد. فیلدهایی که از طریق ادیتورِ
    TinyMCE (iframe) تغییر می‌کنند این رویداد را به بیرون bubble نمی‌کنند — پس تغییرِ
    فقط‌متنِ ادیتور به‌تنهایی دیرتی نمی‌شود (محدودیتِ شناخته‌شده).

## انضباط نگه‌داری (مهم)
**به‌روزرسانی هینت بخشی از همان تغییر است.** وقتی فیلد/الگو/تله/منبع‌واحدِ جدید اضافه شد،
در همان کامیت `CLAUDE.md`/`RECIPES` مربوط را به‌روز کن. **Definition of Done هر تغییر:**
`check` تمیز → migrate (اگر مدل) → تست سریع → هینت به‌روز → commit/push.
قانون فایل بزرگ: هر فایل که از ~۴۰۰ خط رد شد، بالایش یک بلوک ایندکس بگذار.
