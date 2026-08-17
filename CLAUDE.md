# CLAUDE.md — راهنمای ریشه (همیشه لود می‌شود، لاغر نگه‌اش دار)

پلتفرم مدیریت پروژه‌های سئو. Django 5 + Vanilla JS (بدون بیلد، بدون DRF). RTL، تقویم شمسی، تم دارک شیشه‌ای.

> **جزئیات هر اپ در `CLAUDE.md` همان پوشه است** (فقط موقع کار روی آن اپ لود می‌شود).
> **دستورالعمل افزودن چیز جدید:** `docs/RECIPES.md` — قبل از هر feature بخوان.
> **قراردادها و تله‌ها:** `docs/CONVENTIONS.md`.
>
> **پروژه‌ی مجزا `worktracker`** (repoِ `meidane/worktracker`): سامانه‌ی حضورغیاب/ساعتِ
> کاری. **فقط وقتی روی worktracker یا کارِ مرتبط با ساعاتِ کاریِ افراد کار می‌کنی** به آن
> repo مراجعه کن (اضافه‌کردنش با `add_repo`؛ `CLAUDE.md`ی خودش را دارد). اتصالِ seo-manager
> به آن فقط **خواندنِ API** است — جزئیات در `colleagues/CLAUDE.md` (بخشِ حضورغیاب).

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
| اعتبارسنجیِ الزامِ فیلدِ سفارشی (required/required_on_done) | `tasks/api.py: _custom_fields_error` |
| فیلدهای اختصاصیِ نوع در مودال (نه هسته‌ای) | `TaskTypeDef.fields` → `tasks.js: renderCustom` (هسته فقط ۱۰ فیلد عمومی دارد؛ `task-schema.js` فقط fallback برچسب/رنگِ tech/other) — فیلدِ `tags` با ویجتِ tagbox (`tasks.js: tagboxHtml/wireTagboxes`) |
| اتصالِ کلمهٔ کلیدیِ تسک به ردیابیِ رتبهٔ سئو | `seo/signals.py: sync_tracked_keywords` |
| پیشرفتِ رتبه نسبت به تاریخِ برنامه‌ریزی («+۲ بعدِ ۴ روز») | `seo/rank.py: rank_progress` |
| بردِ سئوِ پروژه (سکشنِ ماهِ گزارش + استراتژی + شیتِ ویرایشی) | تبِ «تسک‌ها»ی `projects/detail.html` + `projects/views.py: seo_*` + `tasks.models.ReportMonthStrategy`/`Task.board_order` (`tasks/CLAUDE.md`) |
| استراتژیِ ماهانهٔ هر پروژه | `tasks.models.ReportMonthStrategy(project,year,month,description)` |
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
| جلوگیری از دابل‌کلیکِ ذخیره/ایجاد | `static/js/app.js: fetchJSON` (دکمه‌ی آغازگر خودکار disable + `.is-loading` تا پایانِ درخواست؛ نیازی به کد در هر دکمه نیست) |
| ویرگولِ زندهٔ اینپوت مبلغ (سه‌تاسه‌تا) | `static/js/app.js` — کلاسِ `.money` روی `<input>` (بک‌اند `finance/utils.parse_amount` و فرمِ نیتیو روی submit ویرگول را پاک می‌کنند) |
| دیت‌پیکر شمسی | `static/js/datepicker.js` (کلاس `jdate`) |
| چکِ دسترسیِ سازمانی در ویو/API | `accounts/access.py: require_perm/has_perm` |
| فهرستِ id پروژه‌های قابل‌دیدنِ کاربرِ جاری (همیشه لیست، دیگر هیچ‌وقت `None` — پروژه‌ی شخصیِ دیگران همیشه حذف) | `projects/access.py: accessible_project_ids` |
| پروژه‌ی «شخصی»ِ خودکارِ هر همکار (فقط خودش می‌بیند، حتی مالک نه) | `projects/models.py: Project.personal_owner/is_personal` + `projects/signals.py: ensure_personal_project` (enforcement فقط در `access.py`) |
| دعوت‌نامه‌ی در انتظار (نه عضویتِ فوری، فقط با شماره تماس) | `accounts/models.py: Invite` + `colleagues.views.colleague_grant_access` (+ `docs/PLATFORM.md`) |
| «این تسک قابلِ‌بازبینیِ این کاربر است؟» | `tasks/queries.py: reviewable_q` (صفحه‌ی بازبینی + فیدِ داشبورد) — زنجیره‌ای، نه فقط مدیرِ مستقیم (`colleagues/access.py: all_subordinate_ids`) |
| زیرمجموعه‌ی مدیریتی در هر عمقی (نه فقط مدیرِ مستقیم) | `colleagues/access.py: all_subordinate_ids` (BFS روی `Colleague.manager`) — `tasks/queries.py` و `tasks/api.py: task_review` از همین می‌خوانند |
| «سرپرست است؟» (زیرمجموعه دارد یا پرمیشنِ ناظر) | `colleagues/access.py: is_manager_tier` |
| «می‌تواند این فردِ مشخص را مدیریت کند؟» (سازمانی یا مدیرِ زنجیره‌ایِ همان فرد) | `colleagues/access.py: can_manage_colleague` — `colleagues/views.py` (ویرایش/آرشیو/دسترسی) |
| «این نقش سطح‌بالاست؟» (برای سقفِ نقشِ قابل‌اعطا توسطِ مدیرِ scoped) | `accounts/access.py: is_elevated_role` |
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
| بابتِ حقوقِ هر همکار (خودکار «حقوق <نام>») | `finance/signals.py: ensure_salary_category` (`post_save` روی Colleague) + `Category.colleague` |
| مانده‌ی «کل حساب با همکار» در تبِ حقوق | `finance/views.py: PayrollListView` (Σتعهد حقوق − Σبرداشتِ تراکنش‌های `category__colleague`) |
| مانده‌ی گردش حساب (پروژه/حقوق) | `finance/balances.py: project_balances/salary_balances` (منبع واحدِ ستونِ مانده + بنر + هشدار) |
| هشدارهای حسابداری (نرم) | `finance/alerts.py: compute_alerts` (بانکِ منفی/پروژه‌ی مثبت/اضافه‌پرداختِ حقوق) + `_tx_anomaly_warning` |

## دستورهای کلیدی
```bash
python manage.py migrate
python manage.py seed_demo              # سازمانِ دمو کامل + ۵ کاربرِ واقعی + ۱۴ پروژه (پایین) — بعدِ پاک‌کردنِ DB اول همین را بزن
python manage.py runserver
python manage.py check                  # قبل از هر کامیت
python manage.py collectstatic --noinput  # فقط برای تست مرورگر/تولید
```
DB پیش‌فرض SQLite (متغیرها در `.env`). **`seed_demo`** (`accounts/management/commands/`)
یک سازمانِ کامل («آژانس دمو») می‌سازد: نقش‌ها (built-in + دو نقشِ سفارشی: «مدیرِ ارشد» و
«تولید محتوا»)، ۵ فردِ واقعیِ نمونه با دسترسیِ متفاوت، ۱۴ پروژه‌ی واقعی (نام/دامنه/رنگ)،
چند تسکِ نمونه (عقب‌افتاده/این‌هفته/آینده/انجام‌شده + یک `pending` برای صفِ بازبینی)،
تعطیلات و بابت‌های مالی. اجرای مکرر ایمن است. کاربرهای تست:

| یوزرنیم | پسورد | نقش | برای تستِ چی |
|---|---|---|---|
| `admin` | `admin1234` | امیر گودرزی — مالک (+ سوپریوزر) | دسترسیِ کامل، پنلِ ادمین |
| `fsalehi` | `Salehi123!` | فاطمه صالحی — «مدیرِ ارشد» (همه جز حسابداری)، مسئولِ همه‌ی ۱۴ پروژه | مدیرِ سئو، دسترسیِ گسترده بدونِ حسابداری |
| `sebrahimi` | `Sara123!` | سارا ابراهیمی — «مدیرِ ارشد» (همه جز حسابداری) | مدیرِ طراحی/فنی |
| `amoradi` | `Moradi123!` | امیر مرادی — «تولید محتوا» (بدونِ حسابداری/گزارش/تنظیمات/حذف)، زیرِنظرِ `fsalehi`، `needs_review` | تولیدِ محتوا + جریانِ بازبینیِ صالحی |
| `mziarati` | `Ziarati123!` | مهتاب زیارتی — «تولید محتوا»، دقیقاً مثلِ `amoradi` | همان سناریو |

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
24. **رفعِ‌شده: مودالِ سراسری (`.modal`) کلاً اسکرول می‌شد، نه فقط بدنه‌اش.** فرمِ تسک با
    فیلدِ زیاد (تکرار/توضیحات/گزارش) از ۸۸vh بلندتر می‌شد و برای زدنِ «ذخیره» باید کلِ
    مودال (هدر+بدنه+فوتر با هم) اسکرول می‌شد تا دکمه پیدا شود. `.modal` الان
    `display:flex;flex-direction:column` است؛ فقط `.modal-b{flex:1;overflow-y:auto;
    min-height:0}` اسکرول می‌کند، `.modal-h`/`.modal-f`(دکمه‌های ذخیره/انصراف) با
    `flex:none` همیشه ثابت/دیده‌اند. چون `.modal` مشترکِ همه‌ی مودال‌های سایت است
    (`app.js: openModal`)، این رفتار خودکار روی همه‌شان اعمال شد، نه فقط تسک.
25. **نمای «گوگل‌شیت»ِ سراسری + ریسپانسیوِ جدول‌ها (بلاکِ «فاز ۳» در `style.css`).**
    هر جدولِ سادهٔ داخلِ `.card.glass` (نه `.sheet`/`.tsheet` که خودشان خط‌کشی دارند)
    خودکار خط‌کشیِ عمودیِ سلولی می‌گیرد تا کلِ سایت یکدست شبیهِ صفحه‌گسترده شود — بدونِ
    نیاز به کلاسِ اضافه روی هر `<table>`. **قاعده:** چون `.card{overflow:hidden}` جدولِ
    عریض را روی موبایل می‌بُرد و صفحه را افقی می‌کرد، هر جدولِ عریض را در
    `<div class="tscroll">` بپیچ (اسکرولِ افقیِ داخلِ خودش؛ بدنهٔ صفحه هیچ‌وقت افقی
    اسکرول نشود). گریدهای آماری (`.stats`) از `minmax(0,1fr)` استفاده می‌کنند نه `1fr`،
    وگرنه عددِ بلندِ ریال ستون را از عرضِ سلول بازتر می‌کند و سرریز می‌شود.
26. **کامنتِ `{# … #}`ِ چندخطی در تمپلیت لو می‌رود (بیت‌مان زد).** رجکسِ توکنایزرِ جنگو
    (`tag_re`) بدونِ DOTALL است — `{#.*?#}` فقط وقتی مچ می‌شود که `{#` و `#}` **در یک
    خط** باشند. کامنتِ چندخطی مچ نمی‌شود: `{#` متنِ خام می‌شود و اگر داخلش `{% … %}`
    باشد آن تگ **اجرا** می‌شود (مثلاً `_pagination.html` کامنتش را روی هر صفحهٔ صفحه‌بندی
    نمایش می‌داد + `querystring` را اجرا می‌کرد). برای توضیحِ چندخطی از
    `{% comment %}…{% endcomment %}` استفاده کن، نه `{# … #}`.
27. **سایدبارِ ثابتِ باریک (شبیهِ کلیک‌اپ) — نه هاور، نه جمع‌شونده (بلاکِ «فاز ۲» در
    `style.css`، فقط `@media(min-width:1101px)`).** رِیلِ ۸۲px که همیشه باز است:
    آیکن بالا + برچسبِ ریزِ وسط‌چینِ زیرش (`.nav a{flex-direction:column}`)، برچسبِ
    بخش‌ها (`.nav-label`) به جداکنندهٔ نازک تبدیل می‌شود، و «همکاران» (`.side-att`)
    فقط آواتار + نقطهٔ آنلاین نشان می‌دهد (`.satt-main/.satt-sum/.satt-task/.satt-tl`
    مخفی). سایدبار در فلوِ گرید می‌ماند (`position:sticky`)، **نه `fixed`** — نسخهٔ
    قبلی fixed بود و `.main` را به ستونِ اشتباهِ گرید می‌انداخت (تلهٔ رفع‌شده). موبایل
    (`≤1100px`) همان کشوی افقیِ برچسب‌دار می‌ماند.
28. **تمِ سرزنده‌تر (ایندیگو/بنفش) + اسکرول‌شدوی صحیح.** `--primary` به ایندیگو
    (`#6366F1`) و `--bg` به نیلیِ عمیق (`#090A1B`) رفت؛ هاله‌های رنگیِ `body` غنی‌تر شد
    (ایندیگو/بنفش/صورتی). **نشانگرِ اسکرولِ افقی** دیگر فِیدِ `position:absolute` نیست
    (که با اسکرول روی محتوا می‌افتاد) — به‌جایش (۱) اسکرول‌بارِ همیشه‌دیده با ترَکِ روشن،
    (۲) تکنیکِ **scroll-shadows** (لایه‌های `background` با `attachment:local` برای ماسکِ
    هم‌رنگِ کارت + `attachment:scroll` برای هالهٔ لبه) که به لبهٔ دیدهٔ کانتینر می‌چسبد و
    در دو انتهای مسیر محو می‌شود. رنگِ ماسک = `--card-solid`. روی `.sheet-wrap/.tscroll/
    .tsheet-wrap`. جدولِ تسک‌ها (`.tsheet`) هم حالا خط‌کشیِ سلولی + هدرِ چسبان + راه‌راه
    گرفت (نمای گوگل‌شیت). بابتِ درون‌جدولِ تراکنش (`.txcat-wrap`) تک‌خطیِ فشرده شد
    (`flex-wrap:nowrap`) تا ردیف را بلند نکند.

## انضباط نگه‌داری (مهم)
**به‌روزرسانی هینت بخشی از همان تغییر است.** وقتی فیلد/الگو/تله/منبع‌واحدِ جدید اضافه شد،
در همان کامیت `CLAUDE.md`/`RECIPES` مربوط را به‌روز کن. **Definition of Done هر تغییر:**
`check` تمیز → migrate (اگر مدل) → تست سریع → هینت به‌روز → commit/push.
قانون فایل بزرگ: هر فایل که از ~۴۰۰ خط رد شد، بالایش یک بلوک ایندکس بگذار.
