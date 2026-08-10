# tasks/ — قلب سیستم

## مدل‌ها (`models.py`)
- **Task** — یک مدل واحد، فیلدهای `null=True`. **هسته‌ی عمومی همیشه در مودال دیده می‌شود:**
  `project, assignee, task_type, title, description, planned_date, planned_time(default
  time(8,0)), status, priority, estimate_minutes` (+ تکرار). بقیه فقط فیلدِ سفارشیِ نوع‌اند.
  - ستون‌های قدیمیِ سئوِ هارد‌کد (`word_count, keywords, lsi_keywords, seo_title,
    published_url, source_url, current_rank, media_name, media_cost, anchor_text, target_url,
    link_type, link_count, update_type`) **در مودال دیگر نیستند** (پاک‌سازیِ گام ۱) — در DB و
    `apply_fields`/`to_dict` برای سازگاری با دادهٔ قدیمی مانده‌اند، اما مسیرِ جدید همه‌شان را
    به `TaskTypeField` سفارشی می‌برد (`is_word_source` هنوز `word_count` را پر می‌کند، چون آن یکی
    برای آمار/annotate لازم است — تنها استثنا).
  - بازبینی: `review_status, review_note, reviewed_by/at, ai_*` (فاز۳)
  - **سفارشی:** `type_def`(FK TaskTypeDef) + `custom`(JSON). فیلدهای هسته‌ای دست‌نخورده.
  - propertyها: `is_overdue, is_done, type_label, color_rgb, to_dict()` (شامل آواتار برای تقویم)
- **TaskTypeDef / TaskTypeField** — همه‌ی انواع (built-in + سفارشی) اینجا رکورد دارند.
  `builtin_key` پرشده = نوع پیش‌فرض (فیلدهای هسته‌ای + آمار داشبورد با همین کار می‌کنند)؛
  خالی = کاملاً سفارشی. `seed_task_types` فقط `tech`/`other` عمومی را می‌سازد (بدون فیلدِ
  اختصاصی) + هر نوعِ سئوِ قدیمیِ فعال (publish/update/reportage/linkbuilding) را بازنشسته
  می‌کند (`is_active=False`، اجرای مکرر ایمن) — جایگزینشان بستهٔ `seo/` است.
  مودال از `form_data.customTypes` درایو می‌شود؛ انتخاب نوع → `task_type=builtin_key||other`
  + `type_def=id` + فیلدهای سفارشی. `TaskTypeDef.schema()` → لیست فیلد.
- **TaskTypeKPI / KPIChecklistItem / TaskKPIScore** — شاخص‌های کیفیتِ هر نوع تسک.
  KPI با/بدون چک‌لیست؛ `cap` = جمع آیتم‌ها (چک‌لیستی) یا `max_score`. مدیر در بازبینی
  امتیاز می‌دهد (`TaskKPIScore`، unique(task,kpi)). کارمند در مودال فقط‌خواندنی می‌بیند.
  مدیریت در صفحه‌ی نوع تسک؛ API در `type_views.py` (`kpi_*`). امتیازدهی/نمایش: `api.py`
  (`task_kpis` GET، `task_kpi_score` POST). دکمه‌ی «★ امتیاز کیفیت» در `review.html`.
- **RecurrenceRule** (+ `Task.recurrence`, `Task.is_placeholder`) — تکرارِ تنبل: همیشه
  «۱ واقعی + ۱ پیش‌نما». منطق در `recurrence.py` (`start_series`, `advance`, `create_placeholder`).
  با done شدنِ تسکِ واقعی، پیش‌نما واقعی و پیش‌نمای بعدی ساخته می‌شود (در `task_status` و
  `task_detail` PATCH، فقط در گذارِ به done). **`Task.objects` پیش‌نماها را پنهان می‌کند**
  (`TaskManager`)؛ تقویم با `Task.objects.with_placeholders()` نشانشان می‌دهد (کلاس `.placeholder`).
  حذف سری: `api.recurrence_delete` (تسک‌های done می‌مانند). ساخت: نوار تکرار در مودال (تسک جدید).
- **TaskComment** — «گزارشِ کار» ته مودال تسک (body = HTML پاکسازی‌شده). API:
  `comments/` (GET/POST) + `comment/<id>/` (PATCH/DELETE؛ فقط نویسنده یا ادمین). در tasks.js:
  `initReports(id)` ادیتور دوم TinyMCE (`#f-report`) + لیست ساده با آیکن ویرایش/حذف.
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

## نکات نوع تسک
- **`TaskTypeDef.requires_review`**: اگر true، تسک‌های done این نوع در صفحهٔ بازبینی می‌آیند
  (چک‌باکس در صفحهٔ نوع). صفحهٔ بازبینی بر همین فیلتر می‌شود، نه `published_url`.
- **`TaskTypeField.is_word_source`**: فیلدِ سفارشی‌ای که مقدارش در `apply_fields` به
  `Task.word_count` کپی می‌شود (تا آمار کلمهٔ انواع سفارشی هم کار کند).
- «جمع ساعت» در آمار = `Sum(estimate_minutes)` (فیلتر `hours` در seo_extras؛ دقیقه→ساعت).
  با تایمرِ فاز بعد به زمانِ واقعی سوییچ می‌شود.

## افزودن فیلد به تسک
تقریباً همیشه **فیلدِ سفارشیِ نوع** است، نه فیلدِ هسته‌ای: از `/settings/task-types/`
(یا برای بستهٔ عمودیِ جدید، یک seed مثل `seo/seed_seo.py`) یک `TaskTypeField` بساز —
خودکار در مودال (`tasks.js: renderCustom`) و در ستون‌های قابل‌سفارشی‌سازیِ لیست تسک‌ها
(`core/columns.py: custom_field_columns`) ظاهر می‌شود. فقط اگر واقعاً همه‌ی انواعِ سیستم
(حتی سئوهای بعدی) به آن نیاز دارند فیلدِ هسته‌ایِ جدید در `models.py` اضافه کن.

## وضعیت‌ها
`STATUS_CHOICES` = `todo/doing/done` (وضعیت «لغو شده/cancelled» حذف شد — migration 0006
مقادیر قبلی را به `todo` برمی‌گرداند).

## بازبینی تسک (review) — «بازبینی محتوا»ی قبلی، تغییرِ نام + مسیرِ مدیر
`TaskReviewView` (`/tasks/review/`) دو مسیرِ مستقلِ OR‌شده دارد: (۱) `type_def.requires_review`
→ صفِ عمومی، فقط اگر ویوکننده دسترسیِ سازمانیِ `review` را داشته باشد؛ (۲)
`assignee.needs_review=True` → فقط برای `assignee.manager.user` دیده می‌شود، **مستقل از
دسترسیِ `review`** (تعیینِ مدیر خودش اجازه‌ی بازبینیِ کارِ همان همکار است).
`task_review` API همین دو شرط را چک می‌کند (403 اگر نه دسترسیِ سازمانی نه مدیرِ مستقیم).
`Colleague.manager`/`needs_review` در فرمِ همکار تنظیم می‌شوند (`colleagues/CLAUDE.md`).

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
`python manage.py seed_task_types` — ساخت `tech`/`other` عمومی + بازنشستگیِ سئوهای قدیمی.
برای سئو: `python manage.py seed_seo` (اپِ `seo/`).

## TODO
- نمایش مقادیر `custom` در جدول لیست/سینگل (فعلاً فقط در مودال).
