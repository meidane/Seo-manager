# reports/ — گزارش‌دهی (بدون snapshot)

## مدل‌ها (`models.py`)
- **Report** — `project, invoice(FK به finance.Invoice، اختیاری), title, date_from/to,
  description(HTML), status, public_token(UUID), is_public, visible_fields(JSON)`.
  `visible_fields` = کلید فیلدهای مجاز برای نسخه‌ی عمومی. اتصالِ فاکتور در مودالِ ساختِ
  گزارش (`list.html`) و دراپ‌داونِ صفحه‌ی گزارش (`detail.html` → PATCH `invoice`).
- **ReportItem** — **مرجع زنده به Task** + فیلدهای override (`override_title/done_date/
  description`) که فقط روی همان گزارش اثر دارند. نمایش = override اگر پر باشد وگرنه مقدار زنده.
  propertyها: `eff_title/eff_done_date/eff_description/eff_type/bucket/eff_url/field_value(key)`.
  ردیف دستی: `task=None` + `manual_type/manual_url`.
- ثابت‌ها: **`BUCKETS`** (گروه‌بندی نمایش: انتشار/آپدیت/فنی/رپورتاژ+لینک‌سازی/سایر) و
  **`CLIENT_FIELDS`** (فهرست کامل فیلدهای قابل‌تنظیم برای مشتری).

## جریان کار
انتخاب بازه → `pull_tasks` (تسک‌های بازه، انجام‌شده **و انجام‌نشده**، گروه‌بندی‌شده) →
`add_items` (چک‌باکس) → ویرایش inline ردیف‌ها → تنظیم `visible_fields` → لینک عمومی.

## `pull_tasks` — انجام‌نشده هم قابلِ‌واکشی است
قبلاً فقط `status=done` را می‌آورد (فیلترِ `done_date__range`). الان هر دو را می‌آورد:
`done` با `done_date` در بازه، بقیه (`todo/doing/pending`) با `planned_date` در بازه
(چون هنوز `done_date` ندارند). پاسخِ هر تسک `done`(bool) + `status_label` دارد؛ UIِ
واکشی (`detail.html: p-fetch`) برای غیر-done یک برچسبِ ⏳ کنارش می‌گذارد (`.pull-not-done`
در `style.css`) — **این برچسب فقط برای خودِ ماست**، هیچ‌جای گزارشِ نهایی/عمومی چاپ
نمی‌شود (نمایشِ مشتری همیشه از `CLIENT_FIELDS`/`Report.visible_fields` می‌آید، منبعِ
کاملاً جدا از پاسخِ این API). همین برچسب در `_groups.html` هم برای ردیف‌های
از‌قبل‌اضافه‌شده‌ی هنوز-انجام‌نشده تکرار می‌شود (فقط تمپلیتِ داخلی، نه `public.html`).

## فاکتورِ متصل — جزئیاتِ کامل، نه فقط لینک
`Report.invoice` قبلاً فقط یک دراپ‌داون + لینکِ «مشاهده‌ی فاکتور» بود؛ خودِ ردیف‌ها/جمع‌ها
هیچ‌جا رندر نمی‌شدند. `reports/views.py: _invoice_ctx(report)` منبعِ واحدِ این داده است
(فاکتور + `lines`) — هم `ReportDetailView` (ادیت) هم `PublicReportView`/`ReportPreviewView`
(نسخه‌ی مشتری/پیش‌نمایش) از همین می‌خوانند، جمع‌ها (`subtotal/tax_total/discount_total/
grand_total`) از خودِ `finance.Invoice` (property، منبعِ واحد، `finance/CLAUDE.md`) —
دوباره حساب نمی‌شوند. در `detail.html` جدولِ ردیف‌ها زیرِ دراپ‌داونِ فاکتور می‌آید؛ در
`public.html` همان جدول **آخرِ گزارش** (بعدِ گروه‌های تسک، قبلِ فوتر) — دقیقاً طبقِ
درخواست: مشتری هم می‌بیندش.

## مانده‌ی کل مشتری
هدرِ همان کارتِ فاکتور در `detail.html` یک تگ دارد: «مانده‌ی کل مشتری» = `finance.balances.
project_balance(report.project_id)` (همان منبعِ واحدِ ستونِ مانده در لیستِ فاکتورها/بنرِ
داشبورد، `finance/CLAUDE.md`) — **کلِّ تاریخچه‌ی پروژه**، نه فقط همین گزارش/فاکتور. فقط
داخلی (ادیت)، در نسخه‌ی عمومی/پیش‌نمایشِ مشتری نمایش داده نمی‌شود.

## فایل‌ها / URLها
- `views.py` — صفحات (List/Detail/Public/Preview) + API (`pull_tasks, add_items,
  add_manual, item_edit, reorder, report_update, upload_image`). `clean_html` برای
  توضیحات (bleach). `_invoice_ctx` منبعِ واحدِ داده‌ی فاکتور (بالا).
- نسخه‌ی عمومی: `/r/<uuid>/` (بدون login؛ `report_public`؛ فقط اگر `is_public`)، تم روشن، چاپ.
- **پیش‌نمایش مالک:** `/reports/<id>/preview/` (`ReportPreviewView`، login) — همان تمپلیت public،
  بدون نیاز به عمومی‌کردن (`is_preview` بنر می‌گذارد). دکمه‌ی «پیش‌نمایش مشتری» به این می‌رود.
- تمپلیت‌ها: `list/detail/_groups/public`. **توضیحات: TinyMCE (`textarea.rich-editor`)**
  با دکمه‌ی «ذخیره توضیحات» → PATCH `description`. عکس با کشیدن‌ورهاکردن مستقیم در ادیتور
  (آپلود به `/api/editor/upload/`). ردیف‌ها هنوز contenteditable inline‌اند.
  **فاصله‌ی بینِ بخش‌های صفحه‌ی ادیت** یک قانونِ CSSِ اسکوپ‌شده است، نه استایلِ تکی روی
  هر `<section>`: `[data-report] > section{margin-bottom:14px}` (`style.css`).

## نکات
- برای مخفی‌کردن فیلد از مشتری فقط `visible_fields` را تغییر بده (نسخه‌ی عمومی همان را می‌خواند).
- دسترسیِ این اپ گیت‌شده به `manage_finance` نیست — لینکِ دراپ‌داونِ فاکتور و جزئیاتش قبلاً
  هم بدونِ آن پرمیشن دیده می‌شد (جمعِ کل در `<option>` دراپ‌داون)؛ نمایشِ ردیف‌های کامل
  همان مرزِ دسترسیِ قبلی را دارد، مرزِ جدیدی باز نکرده.
- TODO: نمایش فیلدهای سفارشیِ `show_to_client` در نسخه‌ی عمومی؛ drag reorder UI.
