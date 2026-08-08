# reports/ — گزارش‌دهی (بدون snapshot)

## مدل‌ها (`models.py`)
- **Report** — `project, title, date_from/to, description(HTML), status, public_token(UUID),
  is_public, visible_fields(JSON)`. `visible_fields` = کلید فیلدهای مجاز برای نسخه‌ی عمومی.
- **ReportItem** — **مرجع زنده به Task** + فیلدهای override (`override_title/done_date/
  description`) که فقط روی همان گزارش اثر دارند. نمایش = override اگر پر باشد وگرنه مقدار زنده.
  propertyها: `eff_title/eff_done_date/eff_description/eff_type/bucket/eff_url/field_value(key)`.
  ردیف دستی: `task=None` + `manual_type/manual_url`.
- ثابت‌ها: **`BUCKETS`** (گروه‌بندی نمایش: انتشار/آپدیت/فنی/رپورتاژ+لینک‌سازی/سایر) و
  **`CLIENT_FIELDS`** (فهرست کامل فیلدهای قابل‌تنظیم برای مشتری).

## جریان کار
انتخاب بازه → `pull_tasks` (تسک‌های done گروه‌بندی‌شده) → `add_items` (چک‌باکس) →
ویرایش inline ردیف‌ها → تنظیم `visible_fields` → لینک عمومی.

## فایل‌ها / URLها
- `views.py` — صفحات (List/Detail/Public) + API (`pull_tasks, add_items, add_manual,
  item_edit, reorder, report_update, upload_image`). `clean_html` برای توضیحات (bleach).
- نسخه‌ی عمومی: `/r/<uuid>/` (بدون login؛ `report_public`؛ فقط اگر `is_public`)، تم روشن، چاپ.
- **پیش‌نمایش مالک:** `/reports/<id>/preview/` (`ReportPreviewView`، login) — همان تمپلیت public،
  بدون نیاز به عمومی‌کردن (`is_preview` بنر می‌گذارد). دکمه‌ی «پیش‌نمایش مشتری» به این می‌رود.
- تمپلیت‌ها: `list/detail/_groups/public`. **توضیحات: TinyMCE (`textarea.rich-editor`)**
  با دکمه‌ی «ذخیره توضیحات» → PATCH `description`. عکس با کشیدن‌ورهاکردن مستقیم در ادیتور
  (آپلود به `/api/editor/upload/`). ردیف‌ها هنوز contenteditable inline‌اند.

## نکات
- برای مخفی‌کردن فیلد از مشتری فقط `visible_fields` را تغییر بده (نسخه‌ی عمومی همان را می‌خواند).
- TODO: نمایش فیلدهای سفارشیِ `show_to_client` در نسخه‌ی عمومی؛ drag reorder UI؛ پیش‌نمایش نهایی.
