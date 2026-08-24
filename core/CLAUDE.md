# core/ — پایه‌های مشترک

## مدل‌ها (`models.py`)
- **TimeStampedModel** (abstract) · **Attachment** (GenericFK؛ `is_image, size_h`) ·
  **ActivityLog** · **Holiday** (میلادی؛ جمعه محاسباتی است و ذخیره نمی‌شود).
- **ColumnConfig** — سفارشی‌سازیِ ستون‌های جدولِ تسک/پروژه/همکار، per سازمان (tenant عادی:
  `objects`=فیلترشده، `all_objects`=بدون فیلتر). `table`(tasks/projects/colleagues) +
  `scope`(page/dashboard) + `keys`(JSON، فقط فهرستِ کلیدها به ترتیب — برچسب/حالتِ نمایش
  تکرار نمی‌شود، از کاتالوگ می‌آید). `unique_together(organization, table, scope)`.

## ابزارها
- `jalali.py` — تبدیل میلادی↔شمسی، `parse_jalali`, `format_jalali`, `to_fa/en_digits`,
  `MONTH_NAMES`, `WEEKDAY_NAMES`. **فقط لایه‌ی نمایش/ورودی.**
- `daterange.py` — **`DateRangeMixin`**: `get_range(request)`, `get_previous_range()`,
  `range_context()`. در session ذخیره می‌شود.
- `crypto.py` — Fernet (`encrypt/decrypt`). کلید از `FERNET_KEY` یا مشتق از `SECRET_KEY`.
- `htmlsan.py` — **`clean_html`** (whitelist bleach). خروجی هر ادیتور را پاکسازی کن.
- `context_processors.py: date_range` — پیش‌تنظیم‌های بازه برای هدر.
- `columns.py` — **کاتالوگِ ستون‌های قابل‌سفارشی‌سازی** (منبعِ واحدِ برچسب/حالتِ نمایش):
  `PROJECTS/COLLEAGUES` (لیست دیکشنری `{key,label,display,default}`؛ **`TASKS` عمداً خالی
  است** — ستونِ اضافیِ جدولِ تسک از فیلدهای سفارشیِ نوعِ انتخاب‌شده می‌آید، نه کاتالوگ؛ بخشِ
  «تسک‌ها»ی `/settings/columns/` هم برداشته شد. ستونِ `state`ی پروژه‌ها هم حذف شد) + `custom_field_columns()`
  (برای تسک‌ها، از فیلدهای سفارشیِ انواعِ فعالِ سازمان داینامیک می‌سازد، کلید `cf:<type_def_id>:<field_key>`)
  + `get_columns(table, scope)` (می‌خواند از `ColumnConfig`، پیش‌فرض اگر تنظیم نشده) +
  `cell_value(obj, col)`. حالت‌های نمایش: `text, number, time(دقیقه→ساعت), date, timeago,
  bool, badge(status/priority/state/عمومی), link_icon, progress`. **فیلدِ جدید = فقط اینجا
  اضافه کن**، در ویو/تمپلیت تکرار نکن.
- `templatetags/seo_extras.py` — `jalali, jalali_long, money, timeago, fa_digits, dictkey,
  repfield, elided_pages` + **`{% column_cell obj col %}`** (رندرِ یک سلولِ جدولِ سفارشی طبق
  `col.display`؛ منبعِ واحدِ رندرِ ستون‌ها — در تسک/پروژه/همکار/داشبورد همه‌جا از همین استفاده کن).
- **صفحه‌بندیِ شماره‌دارِ مشترک:** `templates/components/_pagination.html` (۱ ۲ ۳ … ۲۰) — فقط
  به `page_obj` نیاز دارد (`{% querystring %}` بقیه‌ی پارامترها را حفظ می‌کند، `elided_pages`
  بازه را می‌سازد). در هر لیستِ صفحه‌بندی‌شده `{% include %}`اش کن؛ CSS: `.pagi/.pg` در `style.css`.

## PWA / کشِ آپدیت (`pwa.py`) — «کاربران آپدیت‌ها را نمی‌بینند»
`core/pwa.py` مانیفست + سرویس‌ورکر (`/sw.js`) را می‌سازد. **قانونِ ضدِ کشِ کهنه:**
- **نسخه از محتوا مشتق می‌شود:** `_asset_version()` = هشِ بایت‌های `style.css/app.js/tasks.js`.
  با هر تغییرِ CSS/JS، هم نامِ کشِ سرویس‌ورکر عوض می‌شود (کشِ قدیمی در `activate` پاک)، هم
  `?v=` روی لینک‌های `base.html` (تگِ `{% asset_v %}`) → کشِ HTTPِ مرورگر هم باطل می‌شود.
  مستقل از DEBUG/هش‌دارشدنِ نامِ فایل کار می‌کند.
- **استاتیک = stale-while-revalidate** (نه cache-first)، **ناوبری = network-first**،
  `sw.js` با `no-store`. `skipWaiting`+`clients.claim` + رفرشِ یک‌بارهٔ صفحه در `base.html`
  (`controllerchange`) تا کاربر آپدیت را بدونِ پاک‌کردنِ دستیِ کش ببیند.
- **تله:** هرگز استاتیک را cache-first با نسخهٔ ثابت نگه ندار (باگِ قبلی: کاربران تا ابد
  روی نسخهٔ قدیمی می‌ماندند). **توصیهٔ تولید:** `DEBUG=False` تا WhiteNoiseِ
  ManifestStaticFilesStorage نامِ فایل‌ها را هم هش‌دار و immutable کند (لایهٔ محکم‌تر).

## ویوها / دستورها
- `views.py`: `HolidayListView` (`/settings/holidays/`) + **`editor_upload`** (`/api/editor/upload/`
  در config/urls؛ آپلود عکس ادیتور، فقط تصویر، سقف ۲۰MB) + `ColumnsSettingsView`/`columns_save`
  (`/settings/columns/` — پنج بخش: تسک‌ها(صفحه)، پروژه‌ها(صفحه/داشبورد)، همکاران(صفحه/داشبورد)؛
  تیک+ترتیبِ ▲▼ در `templates/settings/columns.html`، ذخیره با POST به `columns/api/save/`)
  + **`ReportMonthsView`** (`/settings/report-months/`، گیت `manage_task_types`) — تعریفِ
  ماه‌های گزارش (`tasks.models.ReportPeriod`، «مرداد ۱۴۰۵»)؛ منبعِ واحدِ مودالِ تسک و بردِ
  سئوِ پروژه (`tasks/CLAUDE.md`). `report_month_add`/`report_month_delete` (چیپ‌های افزودن/حذف).

## افزودنِ جدول/محلِ جدید به سفارشی‌سازیِ ستون‌ها
۱) آیتم‌های کاتالوگ در `core/columns.py` (`_BASE[table]`) ۲) `get_columns(table, scope)` در
ویوِ مربوطه صدا بزن و به context بده ۳) در تمپلیت با `{% column_cell obj col %}` رندر کن
۴) اگر بخشِ جدیدی از تنظیمات لازم است، ردیفش را به `COLUMN_SECTIONS` در `core/views.py` اضافه کن.
- `management/commands/seed_holidays.py` — از `core/data/holidays_<year>.json`. آرگومان
  انعطاف‌پذیر: `1405` · چند سال `1405 1406` · بازه `1405-1408` · بی‌آرگومان = همه‌ی فایل‌ها.
  داده‌ی ۱۴۰۵–۱۴۰۸ موجود است (خورشیدی ثابت + قمریِ محاسبه‌شده). **قمری‌ها بر پایه‌ی
  تقویم رصدیِ ایران (ام‌القری +۱ روز)‌اند و ممکن است ±۱ روز جابه‌جا شوند؛ JSON ویرایش‌پذیر.**
  اسکریپت تولیدِ داده (یک‌بارمصرف، نیازِ `hijridate`) در تاریخچه هست؛ seed خودش وابستگی ندارد.
  **محدودیتِ شناخته‌شده:** این دستور فقط `get_or_create`/`update` می‌کند — رکوردهایی که
  در نسخه‌ی جدیدِ JSON دیگر نیستند (تاریخ عوض شده یا مناسبت حذف شده) را خودش پاک
  نمی‌کند؛ روی دیتابیسی که قبلاً seed شده، جایگزینیِ کاملِ یک فایلِ سال باید با پاک‌کردنِ
  دستیِ `Holiday`های همان بازه (یا از نو ساختنِ DB) همراه شود.
