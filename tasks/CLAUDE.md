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
  **اگر نوعِ تسک هیچ KPIای نداشت** (`task_kpis` → `has: false`)، به‌جای خالی ماندنِ دکمه،
  یک امتیازِ سادهٔ ۱ تا ۱۰ جایگزین می‌شود — روی فیلدِ مستقلِ `Task.quality_score` (نه
  TaskTypeKPI/TaskKPIScore، چون آن‌ها به یک رکوردِ KPI واقعی نیاز دارند)، API جدا:
  `task_quality_score` (POST `{score}`, ۱ تا ۱۰). در `review.html`: `scoreKpis()` وقتی
  `!d.has` بود `scoreQuality()` را صدا می‌زند.
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
  توابع: `form_data` (داده‌ی مودال)، `task_create/detail/status/review/bulk/comments`،
  `task_rows_page` (لودِ تنبل، پایین)، `task_timer`/`running_timers`.
  قانون: تسک انتشارِ `done` بدون `published_url` مجاز نیست (`_publish_url_error`).
  درگ تقویم `planned_date_iso` (میلادی) می‌فرستد؛ مودال `planned_date` (شمسی).
- `queries.py` — **منبعِ واحدِ کوئری‌های مشترک**، از چند جا صدا زده می‌شود تا فیلترها
  جداگانه/متفاوت پیاده نشوند: `reviewable_q` (بازبینی)، `build_task_queryset` (فیلتر+
  دسترسیِ لیست تسک‌ها؛ `TaskListView` و `api.task_rows_page` هر دو از همین می‌خوانند)،
  `group_done_by_day` (گروه‌بندیِ روزانه؛ `?group=day` و جدولِ روزانه‌ی داشبورد)،
  `running_timers_payload` (ویجتِ تایمر؛ context processor و `api.running_timers`).
- `views.py` — `TaskListView` (لیست+کانبان+فیلترها، بازه سراسری، لودِ تنبل)، `TaskReviewView`.
- `type_views.py` + `type_urls.py` — بخش `/settings/task-types/`.
- `static/js/tasks.js` — **مودال سراسری** (در base.html لود؛ دکمه `#new-task` هرجا).
  انواع سفارشی را داینامیک رندر می‌کند؛ `openTask(id, prefill)`. تایمرِ ردیف (`.timer-cell`)
  با delegation سیم‌کشی شده (نه querySelectorAll+forEach) تا ردیف‌های بعداً اضافه‌شده
  (لودِ تنبل، جدولِ تسک‌های آینده) بدونِ سیم‌کشیِ دوباره کار کنند.
- `static/js/task-schema.js` — **کدام فیلد برای کدام نوع** (منبع واحد نمایش مودال).
- `templates/tasks/_rows.html` — **منبعِ واحدِ رندرِ ردیفِ جدولِ تسک‌ها**: جدولِ اصلی،
  جدولِ «تسک‌های آینده» (دقیقاً همین partial، هر دو کاملاً یکسان با ویرایشِ inline) و
  پاسخِ `api.task_rows_page` (لودِ تنبل) هر سه از همین `{% include %}` می‌آیند.

## URLها
`/tasks/` لیست · `/tasks/review/` بازبینی · `/tasks/api/...` (formdata, create, `<id>/`,
`<id>/status`, `<id>/review`, `<id>/comments`, `bulk`, `rows`) · `/settings/task-types/...`

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
**منبعِ واحدِ همین دو شرط:** `tasks/queries.py: reviewable_q(request)` — هرجا «این تسک
قابلِ‌بازبینیِ این کاربر است» لازم شد (خودِ `TaskReviewView` + فیدِ بازبینیِ داشبورد)،
از همین Q استفاده کن، دوباره ننویس.

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
`form_data` **همه‌ی پروژه‌های قابل‌دسترسِ کاربر** را برمی‌گرداند (فعال اول)، نه فقط
`ACTIVE`؛ وگرنه اگر پروژه غیرفعال شود یا پروژه‌ی فعالی نباشد، دراپ‌داون خالی و ذخیره با
«عنوان و پروژه لازم است» شکست می‌خورد (باگ رفع‌شده). قابل‌دسترس‌بودن هم رعایت می‌شود
(`accessible_project_ids`) — وگرنه تسکی که در پروژه‌ی خارج از دسترس ساخته شود بلافاصله
از لیست ناپدید می‌شود چون `TaskListView` با همان فهرست فیلتر می‌کند (این دقیقاً همان
دامِ enforcement بود که در `task_create`/`task_detail` PATCH هم اضافه شد — پروژه‌ی
خارج از دسترس، ۴۰۳). همچنین `myColleagueId`/`ownTasksOnly` می‌فرستد تا مودال:
(۱) فیلد «مسئول» را برای تسکِ جدید پیش‌فرض خودِ کاربر بگذارد، (۲) اگر `ownTasksOnly`
بود، دراپ‌داونِ مسئول را قفل کند (فقط خودش) — سرورساید هم `task_create`/`task_detail`
مقدارِ `assignee` را در این حالت بازنویسی می‌کنند (نه فقط UI، چون کلاینت قابلِ دورزدن است).
فیلدِ «پروژه» در مودال دیگر `<option>` پیش‌فرض ندارد (اول باید صریح انتخاب شود).

## دستور
`python manage.py seed_task_types` — ساخت `tech`/`other` عمومی + بازنشستگیِ سئوهای قدیمی.
برای سئو: `python manage.py seed_seo` (اپِ `seo/`).

## تفکیکِ روزانه (`/tasks/?group=day`)
«مشاهده‌ی همه»ی جدولِ روزانه‌ی داشبورد به همین صفحه با `?group=day` می‌آید — **صفحه‌ی
جدا نساز**، همان `TaskListView` است. وقتی فعال است: تسک‌های `status=done` در بازه‌ی
سراسری روی `done_date` (نه `planned_date`) گروه‌بندی می‌شوند (`ctx['day_groups']` از
`tasks.queries.group_done_by_day`، بقیه‌ی فیلترهای معمولی مثل پروژه/مسئول/نوع هم اعمال
می‌مانند). تمپلیت با `{% if grouped_by_day %}` بینِ نمایشِ گروه‌بندی‌شده و جدولِ معمولی
سوییچ می‌کند. همین تابع را `dashboard/views.py` هم برای جدولِ «۷ روز اخیر» صدا می‌زند —
دوباره ننویس (`dashboard/CLAUDE.md`).

## پیش‌فرض «فقط تسک‌های خودم» (قابلِ‌تغییر)
`build_task_queryset` اگر GET هیچ `assignee` صریحی نداشت (بارِ اولِ صفحه، نه کلیکِ
«همه‌ی همکاران» که `assignee=` خالی می‌فرستد) و کاربر `own_tasks_only` هم نداشت، فیلترِ
`assignee` را روی خودِ کاربر می‌گذارد — دراپ‌داونِ «مسئول» هم همزمان روی «خودم» انتخاب‌شده
نشان داده می‌شود (چون `filters['assignee']` همان چیزی است که تمپلیت برای `selected` چک
می‌کند). این یک **پیش‌فرضِ UI** است، نه محدودیتِ امنیتی — `own_tasks_only` (سختگیرانه،
همیشه فعال) جداست. برای دیدنِ همه: دراپ‌داون → «همه‌ی همکاران».

## دسترسیِ تسکِ دلیگیت‌شده (بیرون از پروژه)
کسی که پروژه‌ای عضوش نیست ولی تسکی برایش دلیگیت شده (assignee)، باید بتواند **همان
تسک** را ببیند/انجامش دهد، بدونِ اینکه بقیه‌ی پروژه/تسک‌های دیگرش را ببیند یا چیزی در
آن پروژه تغییر دهد:
- `build_task_queryset` (لیست): `project_id__in=ids` **یا** `assignee_id=my_colleague.id`
  — تسکِ دلیگیت‌شده در لیستِ خودش دیده می‌شود حتی اگر پروژه در `ids` نباشد.
- `api._task_visible_ok(request, task)` / `_is_own_task(request, task)`: در `task_detail`
  (GET/PATCH/DELETE)، `task_comments`، `task_kpis` استفاده می‌شوند — پروژه در دسترس است
  **یا** خودش مسئولِ همین تسک است.
- `task_status`: مسئولِ خودِ تسک می‌تواند وضعیت را عوض کند (تمامش کند) حتی بدونِ
  `edit_task` — اما `task_detail` PATCH (تغییرِ فیلدهای دیگر مثلِ پروژه/مسئول/تاریخ) همچنان
  `edit_task` واقعی می‌خواهد؛ مودال هم برای همین حالت فقط دکمه‌ی «ذخیره» را نشان نمی‌دهد
  (پایین‌تر) — کارمندِ بدونِ `edit_task` فقط از دراپ‌داونِ وضعیتِ ردیف یا تایمر استفاده می‌کند.

## تعریفِ تسک برای خود — بدونِ `edit_task`
هرکسی که پروفایلِ همکار دارد (`request.user.colleague`) می‌تواند برای **خودش** تسکِ
جدید بسازد، حتی بدونِ دسترسیِ سازمانیِ `edit_task` (که «ویرایش/دلیگیت‌کردن به همه» است):
`task_create` اگر `edit_task` نداشت، `assignee` را با `my_colleague.id` بازنویسی می‌کند
(کلاینت قابلِ دورزدن است، این‌جا هم اجرا می‌شود). `form_data.createTask` = `bool(my_colleague)`؛
`tasks.js: modalHtml` برای تسکِ **جدید** با `cfg.editTask || cfg.createTask` دکمه‌ی
ذخیره را نشان می‌دهد و اگر `edit_task` نداشت دراپ‌داونِ مسئول را قفل می‌کند (فقط خودش) —
برای تسکِ **موجود** هنوز فقط `edit_task` واقعی (+ `ownMatch`) کافی است. دکمه‌ی «＋ تسک
جدید» هرجا (هدر/صفحه‌ی تسک‌ها/سلولِ تقویم) با context var سراسریِ `can_create_task`
(`accounts.context_processors.org`: `bool(colleague) or 'edit_task' in perms`) گیت
می‌شود، نه `'edit_task' in org_perms` — چون این دکمه دیگر مخصوصِ `edit_task` نیست.

## تایمرِ کار — یک نفر هم‌زمان فقط یک تایمرِ فعال
`api.task_timer` (POST `{action:start|stop}`): فقط **مسئولِ خودِ تسک** (یا کسی که پرمیشنِ
`edit_time` دارد) می‌تواند استارت/استاپ بزند. استارت‌کردنِ یک تسک، هر تایمرِ دیگرِ در
حالِ اجرای **همان مسئول** (`assignee_id` یکسان) را خودکار استاپ می‌کند (پاسخ شاملِ
`stopped_id`/`stopped_spent` تا اگر آن تسکِ دیگر هم در همان صفحه دیده می‌شود، سلولش را
JS به‌روز کند). PATCH `{minutes}` (ویرایشِ دستیِ زمانِ دیگران) فقط `edit_time` —
پرمیشنِ جداگانه‌ای در نقش‌ها (پیش‌فرض: مالک/مدیر/سرپرست)، **نه** دیگر مشتق از `review`.
`ctx['can_edit_time']`/ستونِ «زمان» جدول هم از همین می‌آید.
**ویجتِ گوشه‌ی پایین‌راست** (`templates/base.html: #timer-widget`،
`static/js/timer-widget.js`) با `tasks.queries.running_timers_payload(request)` (context
processor + `api.running_timers`، منبعِ واحد) پر می‌شود: تسکِ در حالِ اجرای **خودِ کاربر**
(`mine:true`، با دکمه‌ی توقف) + تسکِ در حالِ اجرای **زیرمجموعه‌های مستقیمش**
(`Colleague.manager == خودش`، `mine:false`، فقط‌خواندنی با نامِ فرد، بدونِ دکمه).

## لودِ تنبل (اسکرول، بیش از ۵۰ تسک)
`TaskListView` فقط ۵۰ ردیفِ اول را رندر می‌کند (`tasks.queries.PAGE_SIZE`) + `has_more`
در context. تمپلیت `window.TASKS_LAZY = {hasMore, page:1}` را ست می‌کند؛ `tasks.js`
با اسکرولِ نزدیکِ ته صفحه `GET /tasks/api/rows/?...همان‌فیلترها...&page=N` را می‌زند
(`api.task_rows_page`، از همان `build_task_queryset` می‌خواند تا فیلترها با صفحه‌ی اول
هماهنگ بماند) و HTMLِ برگشتی (رندرشده با `templates/tasks/_rows.html`) را به `tbody`
اضافه می‌کند. **برای حالتِ `?group=day` صفحه‌بندی نیست** (۷۰۰ خطا اگر درخواست شود —
گروه‌بندیِ روزانه معمولاً کوچک است، اگر لازم شد بعداً اضافه کن).

## دسترسی در UI — نه فقط سرور
هر جا امکانِ ویرایش/ساخت/حذفِ تسک سرورساید گیت شده، **باید در تمپلیت/JS هم پنهان شود**،
وگرنه کاربرِ بدونِ دسترسی روی چیزی کلیک می‌کند که فقط ۴۰۳ برمی‌گرداند:
- `TaskListView.ctx['can_edit_task']` (= `m.can('edit_task')`؛ own_tasks_only از قبل
  لیست را به تسک‌های خودش محدود کرده، پس این یک چکِ تخت کافی است) — جدولِ لیست دو حالت
  دارد: ستون‌های قابل‌ویرایشِ زنده (select/input) وقتی `can_edit_task`، وگرنه متنِ ساده
  + بدونِ چک‌باکسِ گروهی/نوارِ عملیاتِ گروهی. **استثنا:** ستونِ وضعیت حتی در حالتِ
  فقط‌خواندنی هم دراپ‌داونِ قابل‌تغییر می‌ماند اگر `t.assignee_id == my_colleague_id`
  (تسکِ دلیگیت‌شده‌ی خودش — بالا) و ستونِ تایمر همیشه دکمه‌ی پلی دارد اگر خودش مسئول
  باشد یا `can_edit_time`، وگرنه فقط عددِ زمانِ صرف‌شده (بدونِ دکمه).
- دکمه‌های «＋ تسک جدید» (هدر، صفحه‌ی تسک‌ها، سلولِ تقویم) با context var سراسریِ
  `can_create_task` گیت می‌شوند (بالا)؛ تقویم چون سلول‌ها با AJAX دوباره رندر می‌شوند
  (`calendar-page.js`)، پرچم از `window.CAL_INIT.canCreateTask` می‌آید، نه فقط
  تمپلیتِ SSR اول (`calendarapp/CLAUDE.md`).
- مودالِ تسک: `form_data` پرچم‌های `editTask`/`deleteTask`/`createTask` می‌فرستد؛
  `tasks.js: modalHtml` با `ownTasksOnly`+`myColleagueId`+`isNew` ترکیبشان می‌کند تا
  تصمیم بگیرد دکمه‌های «ذخیره»/«ذخیره و ایجاد بعدی»/«حذف» را نشان بدهد یا نه (مودال
  فقط‌خواندنی می‌شود، نه اینکه کلیکِ ذخیره ۴۰۳ بخورد).

## TODO
- نمایش مقادیر `custom` در جدول لیست/سینگل (فعلاً فقط در مودال).
