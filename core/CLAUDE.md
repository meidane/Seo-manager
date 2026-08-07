# core/ — پایه‌های مشترک

## مدل‌ها (`models.py`)
- **TimeStampedModel** (abstract) · **Attachment** (GenericFK؛ `is_image, size_h`) ·
  **ActivityLog** · **Holiday** (میلادی؛ جمعه محاسباتی است و ذخیره نمی‌شود).

## ابزارها
- `jalali.py` — تبدیل میلادی↔شمسی، `parse_jalali`, `format_jalali`, `to_fa/en_digits`,
  `MONTH_NAMES`, `WEEKDAY_NAMES`. **فقط لایه‌ی نمایش/ورودی.**
- `daterange.py` — **`DateRangeMixin`**: `get_range(request)`, `get_previous_range()`,
  `range_context()`. در session ذخیره می‌شود.
- `crypto.py` — Fernet (`encrypt/decrypt`). کلید از `FERNET_KEY` یا مشتق از `SECRET_KEY`.
- `htmlsan.py` — **`clean_html`** (whitelist bleach). خروجی هر ادیتور را پاکسازی کن.
- `context_processors.py: date_range` — پیش‌تنظیم‌های بازه برای هدر.
- `templatetags/seo_extras.py` — `jalali, jalali_long, money, timeago, fa_digits, dictkey, repfield`.

## ویوها / دستورها
- `views.py`: `HolidayListView` (`/settings/holidays/`) + **`editor_upload`** (`/api/editor/upload/`
  در config/urls؛ آپلود عکس ادیتور، فقط تصویر، سقف ۲۰MB).
- `management/commands/seed_holidays.py` — از `core/data/holidays_<year>.json`.
