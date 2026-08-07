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
- **TaskTypeDef / TaskTypeField** — انواع سفارشی کاربر (kind: text/textarea/number/checkbox/select/url/date).
  `TaskTypeDef.schema()` → لیست فیلد برای فرانت.
- **TaskComment**.

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

## TODO
- نمایش مقادیر `custom` در جدول لیست/سینگل (فعلاً فقط در مودال).
