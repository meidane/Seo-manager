# CLAUDE.md — راهنمای ریشه (همیشه لود می‌شود، لاغر نگه‌اش دار)

پلتفرم مدیریت پروژه‌های سئو. Django 5 + Vanilla JS (بدون بیلد، بدون DRF). RTL، تقویم شمسی، تم دارک شیشه‌ای.

> **جزئیات هر اپ در `CLAUDE.md` همان پوشه است** (فقط موقع کار روی آن اپ لود می‌شود).
> **دستورالعمل افزودن چیز جدید:** `docs/RECIPES.md` — قبل از هر feature بخوان.
> **قراردادها و تله‌ها:** `docs/CONVENTIONS.md`.

## نقشه‌ی اپ‌ها (یک خط هر کدام)
- `config/` — تنظیمات، urls ریشه، wsgi/asgi
- `core/` — پایه‌ها: TimeStampedModel, Attachment, ActivityLog, Holiday, ColumnConfig(+`columns.py` کاتالوگ) + jalali/daterange/crypto/htmlsan + templatetags + editor_upload
- `accounts/` — هویتِ چندشرکتی: Organization→Team→زیرمجموعه، Membership/نقشِ سفارشی، دعوت‌نامه(Invite، فقط با شماره تماس)، `/settings/people/` = فقط تیم‌ها/نقش‌ها (`docs/PLATFORM.md`)
- `colleagues/` — **«افراد و دسترسی‌ها»**ی سایدبار: Colleague (CRUD + آمار سینگل + جدول+اسپارک‌لاین + مدیر/needs_review + دسترسی به سیستم با شماره تماس)
- `projects/` — Project + Credential(رمزنگاری) + فایل‌ها + `members`(گیتِ دسترسیِ واقعی)؛ سینگل با تب‌ها
- `tasks/` — **قلب سیستم**: Task, TaskComment, TaskTypeDef/Field؛ api.py + مودال سراسری
- `calendarapp/` — تقویم شمسی (بدون مدل؛ منطق در calendar_logic.py) + دیت‌پیکر
- `dashboard/` — ویو تجمیعی
- `reports/` — Report/ReportItem (بدون snapshot، override، لینک عمومی مشتری) + اتصالِ اختیاریِ فاکتور
- `finance/` — حسابداری (پایه): BankAccount, Category(بابت), Transaction(+ایمپورت اکسل), Payroll,
  Invoice/InvoiceLine(فاکتور با شماره‌ی خودکار + ردیف‌ها + جمع‌ها)
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
| دعوت‌نامه‌ی در انتظار (نه عضویتِ فوری، فقط با شماره تماس) | `accounts/models.py: Invite` + `colleagues.views.colleague_grant_access` (+ `docs/PLATFORM.md`) |
| «این تسک قابلِ‌بازبینیِ این کاربر است؟» | `tasks/queries.py: reviewable_q` (صفحه‌ی بازبینی + فیدِ داشبورد) |
| فیلتر+دسترسیِ لیستِ تسک‌ها (پروژه/مسئول/نوع/…) | `tasks/queries.py: build_task_queryset` (لیست + لودِ تنبل) |
| گروه‌بندیِ تسک‌های done بر اساسِ روز | `tasks/queries.py: group_done_by_day` (`?group=day` + جدولِ ۷روزه‌ی داشبورد) |
| تسک‌های در حالِ اجرای تایمر برای کاربر/زیرمجموعه‌هایش | `tasks/queries.py: running_timers_payload` (ویجت + API) |
| نوارِ تبِ صفحاتِ تنظیمات + هابِ سایدبار | `templates/settings/_nav.html` + `accounts:settings_home` — لینکِ سایدبار «تنظیمات» یکی است، گیت‌شده با `has_settings_access` (context processor، از `accounts/permissions.py: SETTINGS_PERMS`) |
| دادنِ دسترسیِ سیستم به یک فرد | `colleagues.views._grant_access` (`mode=invite` فقط شماره / `mode=password` مدیر خودش رمز می‌سازد) |
| «این تسک نیاز به بازبینی دارد و باید `pending` بماند نه `done`؟» | `Task.needs_review` (فیلدِ تسک، پیش‌فرضش از `Colleague.needs_review` موقعِ ساخت) + دراپ‌داونِ وضعیت `templates/tasks/_status_select.html` |
| توقفِ خودکارِ تایمر با تکمیلِ تسک | `tasks/api.py: _stop_timer` (صدا زده می‌شود از `apply_fields`, `task_status`, `task_review`) |
| جمع‌های فاکتور (جمع/مالیات/تخفیف/کل) | `finance/models.py: Invoice.subtotal/tax_total/discount_total/grand_total` + `InvoiceLine.base/total` (property؛ فرانت هم همین را محاسبه می‌کند) |
| شماره‌ی خودکارِ فاکتور | `finance/models.py: Invoice.save` (`Max(number)+1` در سطحِ سازمان) |
| ذخیره‌ی ردیف‌های فاکتور (create/update) | `finance/views.py: _save_lines` (حذف و بازساخت از آرایه) |

## دستورهای کلیدی
```bash
python manage.py migrate
python manage.py seed_demo              # سازمانِ دمو کامل + ۶ کاربرِ تست (پایین) — بعدِ پاک‌کردنِ DB اول همین را بزن
python manage.py runserver
python manage.py check                  # قبل از هر کامیت
python manage.py collectstatic --noinput  # فقط برای تست مرورگر/تولید
```
DB پیش‌فرض SQLite (متغیرها در `.env`). **`seed_demo`** (`accounts/management/commands/`)
یک سازمانِ کامل («آژانس دمو») می‌سازد: نقش‌ها (built-in + یک نقشِ سفارشیِ محدود)، ۶ کاربرِ
تست با یوزر/پسوردِ ثابت (پایین)، چند پروژه با عضویتِ متفاوت، چند تسکِ نمونه (عقب‌افتاده/
این‌هفته/آینده/انجام‌شده + یک تسکِ دلیگیت‌شده برای تستِ دسترسیِ بیرون از عضویتِ پروژه)،
تعطیلات و بابت‌های مالی. اجرای مکرر ایمن است — همیشه می‌شود دوباره زد. کاربرهای تست:

| یوزرنیم | پسورد | نقش | برای تستِ چی |
|---|---|---|---|
| `admin` | `admin1234` | مالک (+ سوپریوزرِ جنگو) | دسترسیِ کامل، پنلِ ادمین |
| `admin1` | `Admin123!` | مدیر (built-in) | دسترسیِ سازمانیِ گسترده |
| `teamlead1` | `Teamlead123!` | نقشِ سفارشیِ «سرپرستِ تیم (محدود)» — بدونِ `view_all_projects` | سرپرستِ محدود‌به‌پروژه/زیرمجموعه (سناریوی واقعیِ باگ‌های این پروژه) + بازبینیِ تسکِ `member1` |
| `member1` | `Member123!` | عضو (بدونِ `view_other_tasks`)، عضوِ «پروژه‌ی الف»، زیرِنظرِ `teamlead1`، `needs_review=True` | تسکِ خودش، جریانِ کاملِ بازبینی (تسکِ جدید→`pending`→تاییدِ `teamlead1`→`done`) |
| `member2` | `Member123!` | عضو، **عضوِ هیچ پروژه‌ای نیست**، زیرِنظرِ `teamlead1` | تسکِ دلیگیت‌شده‌ی بیرون از عضویتِ پروژه |
| `viewer1` | `Viewer123!` | ناظر (فقط `view_reports`) | فقط‌خواندنی |

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
18. **«همکاران» و «افراد و دسترسی‌ها» ادغام شدند** (یک منو، `colleagues:list`؛
    `accounts:people` فقط تیم‌ها/نقش‌ها مانده). دادنِ دسترسی دو راه دارد
    (`colleagues.views._grant_access`): `mode=invite` (فقط شماره؛ اگر شماره حساب نداشت،
    `Invite` با `user=None` می‌ماند تا `/signup/` با همان شماره خودکار وصلش کند) یا
    `mode=password` (مدیر خودش نام‌کاربری/رمز می‌سازد → دسترسیِ فوری). دکمه‌ی جدای
    «افزودن فرد» حذف شد — همه‌چیز از «＋ کاربر جدید» شروع می‌شود.
19. **Django 5 دیگر GET را برای logout قبول نمی‌کند** (فقط POST) — لینکِ سایدبار خروج
    باید `<form method="post">` باشد، نه `<a href>`؛ وگرنه کلیک روی خروج فقط ۴۰۵ می‌گیرد
    و ساکت هیچ‌کاری نمی‌کند (به‌نظر «دکمه کار نمی‌کند» می‌رسد).
20. **گیتِ سرور کافی نیست، UI هم باید پنهان کند.** چند لینک/دکمه (ویرایشِ پروژه/همکار،
    «＋ پروژه‌ی جدید»، تبِ «دسترسی‌ها»ی پروژه) سرورساید درست گیت بودند ولی در تمپلیت
    همیشه دیده می‌شدند — کلیک برای کاربرِ بدونِ پرمیشن یک ۴۰۵ِ تمام‌صفحه‌ی جنگو می‌داد
    (نه توستِ داخلِ صفحه، چون این‌ها ناوبریِ واقعی‌اند، نه fetch — برخلافِ اکشن‌های
    مودالی/AJAX که خطا را `app.js: fetchJSON` خودش toast می‌کند و صفحه عوض نمی‌شود).
    **قاعده:** هر لینک/دکمه‌ای که واقعاً یک صفحه یا اکشنِ پرمیشن‌دار را باز می‌کند، در
    تمپلیت هم با همان پرمیشن (`'x' in org_perms` یا context varِ معادل) شرطی شود.
    ضمناً موقعِ همین ممیزی یک تلهٔ امنیتیِ جدی هم پیدا شد: `projects.credential_create/
    reveal/delete` اصلاً `manage_projects` چک نمی‌کردند (فقط `is_authenticated`) — هر عضوِ
    سازمان می‌توانست پسوردِ هر پروژه‌ای را با pk حدس بزند/ببیند/حذف کند.
21. **باگِ جدی (رفع‌شده): «هرچی دسترسی دادم عملاً کار نمی‌کند».** کاربرِ گزارش داد نقشِ
    «مدیر» ساخته و همه‌ی دسترسی‌ها را داده ولی آن کاربر حتی نمی‌توانست تسک بسازد. علت:
    `projects/access.py: accessible_project_ids` فقط `Membership.role == 'owner'` را
    نامحدود می‌دانست؛ دارنده‌ی پرمیشنِ `manage_projects` (مثلِ نقشِ «مدیر») هم تا وقتی
    به‌صراحت به `Project.members` **هر پروژه** اضافه نمی‌شد، هیچ پروژه/تسکی نمی‌دید —
    مستقل از این‌که چه پرمیشن‌هایی داشت. رفع شد: `manage_projects` هم مثلِ مالک نامحدود
    است. **قاعده:** پرمیشنِ سازمانی («می‌تواند همه‌ی X را مدیریت کند») هرگز نباید توسطِ
    یک گیتِ دیگر (اینجا: عضویتِ صریح در هر رکورد) بی‌اثر شود؛ اگر پرمیشنِ جدیدی به معنیِ
    «روی همه‌چیز» اضافه کردی، در `accessible_project_ids`/معادل‌هایش هم چک کن.
    **همزمان:** کسی که کاری برایش دلیگیت شده ولی عضوِ آن پروژه نیست، باید بتواند همان
    تسکِ خودش را ببیند/انجامش دهد بدونِ دیدنِ بقیه‌ی پروژه — این با یک OR جداگانه در
    سطحِ تسک حل شد (`tasks.queries.build_task_queryset` + `tasks.api._task_visible_ok`)،
    نه با شل‌کردنِ گیتِ پروژه.
22. **باگِ جدی (رفع‌شده): «سرپرست هم فقط تسکِ خودش را می‌دید».** پیش‌فرضِ «بازِ اول فقط
    تسک‌های خودم» (تلهٔ ۲۱ بالا نبود، فیچرِ جداگانه‌ای بود) بی‌قیدوشرط روی همه اعمال
    می‌شد — کسی با پرمیشنِ `review`/`manage_people`/`view_all_projects` یا زیرمجموعه
    (`Colleague.reports`) هم با بازِ اولِ `/tasks/` فقط تسکِ خودش را می‌دید و گمان
    می‌کرد پرمیشن‌هایش اثر ندارند. رفع شد: `build_task_queryset` این پیش‌فرض را برای
    «سرپرست» (`is_manager_tier`) غیرفعال می‌کند + یک OR جداگانه هم اضافه شد تا سرپرست
    تسکِ **هر زیرمجموعه‌ی مستقیمش** را ببیند، حتی در پروژه‌ای که خودش عضو نیست
    (`assignee__manager_id=my_colleague.id` — همان الگویی که ویجتِ تایمر/فیدِ بازبینی
    از قبل داشتند). `tasks/CLAUDE.md`.
23. **بازطراحیِ دسترسی‌ها + وضعیتِ بازبینیِ تسک (این تغییر).** دو چیزِ جداگانه هم‌زمان
    عوض شد، مراقبِ قاطی‌کردنشان باش:
    - **پرمیشن‌ها granular شدند و بعضی تغییرِ نام دادند:** `manage_projects` جای خودش را
      به هفت پرمیشنِ جدا داد (`view_all_projects, add_project, edit_project,
      project_files, project_colleagues_access, project_credentials, project_reports`)،
      `manage_colleagues` شد `manage_people`، `own_tasks_only`(محدودکننده) شد
      `view_other_tasks`(مثبت‌قطبی، معکوس). نقشِ سفارشیِ ساخته‌شده روی سازمانِ **قدیمی**
      (قبل از این تغییر) کلیدهای قدیمی را در `Role.perms` نگه می‌دارد — چون
      `seed_roles`ی `get_or_create` هرگز نقشِ موجود را آپدیت نمی‌کند (تلهٔ شناخته‌شده،
      پایین‌تر). برای تستِ درست باید دیتابیس را از نو بسازی یا نقش‌ها را دستی در
      `/settings/roles/` دوباره تیک بزنی.
    - **تسک حالا `needs_review` (فیلدِ خودِ تسک) دارد، نه فقط `Colleague.needs_review`.**
      مقدارِ پیش‌فرضش موقعِ ساختِ تسک از `Colleague.needs_review`ِ مسئول می‌آید، ولی
      از خودِ مودال هم قابلِ تغییر است. اگر `needs_review=True`، تسک هرگز مستقیم به
      `done` نمی‌رود — فقط تا `pending`(«تکمیل — در انتظارِ بازبینی») و از آنجا فقط با
      تاییدِ `task_review`(API) به `done` می‌رود؛ اگر `False` بود، گزینه‌ی `pending`
      اصلاً در دراپ‌داون نیست و رفتار مثلِ قبل (مستقیم `done`) است. `tasks/CLAUDE.md`،
      بخشِ «بازبینی تسک».

## انضباط نگه‌داری (مهم)
**به‌روزرسانی هینت بخشی از همان تغییر است.** وقتی فیلد/الگو/تله/منبع‌واحدِ جدید اضافه شد،
در همان کامیت `CLAUDE.md`/`RECIPES` مربوط را به‌روز کن. **Definition of Done هر تغییر:**
`check` تمیز → migrate (اگر مدل) → تست سریع → هینت به‌روز → commit/push.
قانون فایل بزرگ: هر فایل که از ~۴۰۰ خط رد شد، بالایش یک بلوک ایندکس بگذار.
