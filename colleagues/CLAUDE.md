# colleagues/

## مدل
**Colleague** — `full_name, roles(CSV), avatar, color, description, phone/email, status,
archived_at, join_date, user(O2O), rate_per_word/task`. `archive()/restore(),
roles_list/roles_display, initials, is_active`.

## فایل‌ها
- `views.py`:
  - `ColleagueListView` — **جدولی** با آمار بازه‌ای (annotate: planned/done/words/minutes/overdue)
    + اسپارک‌لاین ۱۴ روزه (یک کوئری، گروه‌بندی پایتون در `get_context_data`). ستون‌های آماری
    (نه نام/اسپارک‌لاین/وضعیت که ثابت‌اند) از `core.columns.get_columns('colleagues','page')`
    می‌آیند — تنظیم در `/settings/columns/`.
  - `ColleagueDetailView` — آمار بازه، **دونات** تفکیک نوع (`donut_segments`)، تفکیک پروژه،
    روند روزانه، تب تقویم شخصی (embed)، تب تسک‌ها.
  - CRUD + archive/restore.
- `forms.py` — نقش چک‌باکسی، `join_date` با `jdate`، توضیحات `rich-editor` + `clean_html`.

## نکته
`.who/.spark/.donut-legend` باید در `static/css/style.css` باشند (بودند نبودند → رفع شد).

## TODO
`donut_segments`/`TYPE_HEX`/`TYPE_LABEL` (تفکیکِ نوع در سینگل همکار) هنوز بر پایه‌ی
`task_type` خام‌اند — تسک‌های نوعِ کاملاً سفارشی (سئوی جدید و بعدی‌ها) همه زیرِ «سایر»
جمع می‌شوند چون `task_type='other'` دارند. برای تفکیکِ درست باید به `type_def` سوییچ کند
(مثلِ فیلترِ لیست/تقویم که همین گام سوییچ شد).
