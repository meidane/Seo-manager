# tasks/ — قلب سیستم

## مدل‌ها (`models.py`)
- **Task** — یک مدل واحد، فیلدهای `null=True`، نمایش شرطی در فرانت.
  - مشترک: `project, assignee, task_type, update_type, title, description, planned_date,
    planned_time(default time(8,0)), status, done_date, priority, estimate_minutes`
  - محتوایی: `word_count, keywords, lsi_keywords, seo_title` (انتشار/آپدیت/رپورتاژ)
  - `published_url` (انتشار/رپورتاژ — نه آپدیت) · `source_url, current_rank` (فقط آپدیت)
  - رپورتاژ: `media_name, media_cost, anchor_text, target_url` · لینک‌سازی: `link_type, link_count`
  - بازبینی: `review_status, review_note, reviewed_by/at, ai_*` (فاز۳)
  - **سفارشی:** `type_def`(FK TaskTypeDef) + `custom`(JSON). فیلدهای هسته‌ای دست‌نخورده.
  - propertyها: `is_overdue, is_done, type_label, color_rgb, to_dict()` (شامل آواتار برای تقویم)
- **TaskTypeDef / TaskTypeField** — همه‌ی انواع (built-in + سفارشی) اینجا رکورد دارند.
  `builtin_key` پرشده = نوع پیش‌فرض (فیلدهای هسته‌ای + آمار داشبورد با همین کار می‌کنند)؛
  خالی = کاملاً سفارشی. `seed_task_types` انواع پیش‌فرض را می‌سازد (اجرای مکرر ایمن).
  مودال از `form_data.customTypes` درایو می‌شود؛ انتخاب نوع → `task_type=builtin_key||other`
  + `type_def=id` + فیلدهای سفارشی. `TaskTypeDef.schema()` → لیست فیلد.
- **TaskComment**.
- **TaskReviewNote** — تاریخچه‌ی «نیاز به اصلاح» (note HTML، author، created_at؛ جدیدترین اول).

## فایل‌ها
- `api.py` — همه‌ی API JSON. **`apply_fields` منبع واحد ذخیره‌ی فیلد است.**
  توابع: `form_data` (داده‌ی مودال)، `task_create/detail/status/review/bulk/comments`.
  قانون: تسک انتشارِ `done` بدون `published_url` مجاز نیست (`_publish_url_error`).
  درگ تقویم `planned_date_iso` (میلادی) می‌فرستد؛ مودال `planned_date` (شمسی).
- `views.py` — `TaskListView` (لیست+کانبان+فیلترها، بازه سراسری)، `TaskReviewView`.
- `type_views.py` + `type_urls.py` — بخش `/settings/task-types/`.
- `static/js/tasks.js` — **مودال سراسری** (در base.html لود؛ دکمه `#new-task` هرجا).
  انواع سفارشی را داینامیک رندر می‌کند؛ `openTask(id, prefill)`.
- `static/js/task-schema.js` — **کدام فیلد برای کدام نوع** (منبع واحد نمایش مودال).

## URLها
`/tasks/` لیست · `/tasks/review/` بازبینی · `/tasks/api/...` (formdata, create, `<id>/`,
`<id>/status`, `<id>/review`, `<id>/comments`, `bulk`) · `/settings/task-types/...`

## افزودن فیلد به تسک = ۳ نقطه
۱) فیلد در `models.py` (+migration) ۲) گروه در `task-schema.js` ۳) لیست مناسب در
`apply_fields` (TEXT/INT/DECIMAL/CHOICE). برای نمایش در لیست/تقویم، `to_dict` را هم ببین.

## وضعیت‌ها
`STATUS_CHOICES` = `todo/doing/done` (وضعیت «لغو شده/cancelled» حذف شد — migration 0006
مقادیر قبلی را به `todo` برمی‌گرداند).

## بازبینی (review)
`task_review`: `needs_fix` → تسک از `done` به `doing` برمی‌گردد و `done_date` پاک می‌شود؛
`review_note` (HTML، پاکسازی با clean_html) با مودال TinyMCE نوشته می‌شود. در لیست، تگ
«⚠ نیاز به اصلاح» کنار عنوان (`data-fix-note`) → کلیک، **مودالِ خودِ تسک** را باز می‌کند
(دیگر مودال‌روی‌مودال نیست). موارد و تاریخچه بالای مودال در جعبه‌ی `.fixnote-box` می‌آیند.
**تاریخچه:** هر بار `needs_fix` با یادداشت → یک رکورد **`TaskReviewNote`** (جدیدترین اول).
`task_detail` آن‌ها را در `review_notes` می‌فرستد؛ `reviewNotesHtml(t)` در tasks.js رندر می‌کند
(آخرین باز، قبلی‌ها با دکمه‌ی «سوابق قبلی» جمع).
**چرخه:** تسکِ `needs_fix` وقتی دوباره `done` شود، `review_status` به `unreviewed`
برمی‌گردد (بازبینی مجدد مدیر) — در `task_status` و `apply_fields` هر دو.

## نکته‌ی form_data
`form_data` **همه‌ی** پروژه‌ها را برمی‌گرداند (فعال اول)، نه فقط `ACTIVE`؛ وگرنه اگر
پروژه غیرفعال شود یا پروژه‌ی فعالی نباشد، دراپ‌داون خالی و ذخیره با «عنوان و پروژه لازم است»
شکست می‌خورد (باگ رفع‌شده).

## دستور
`python manage.py seed_task_types` — ساخت انواع پیش‌فرض قابل‌مدیریت.

## TODO
- نمایش مقادیر `custom` در جدول لیست/سینگل (فعلاً فقط در مودال).
