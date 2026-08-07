# colleagues/

## مدل
**Colleague** — `full_name, roles(CSV), avatar, color, description, phone/email, status,
archived_at, join_date, user(O2O), rate_per_word/task`. `archive()/restore(),
roles_list/roles_display, initials, is_active`.

## فایل‌ها
- `views.py`:
  - `ColleagueListView` — **جدولی** با آمار بازه‌ای (annotate) + اسپارک‌لاین ۱۴ روزه
    (یک کوئری، گروه‌بندی پایتون در `get_context_data`).
  - `ColleagueDetailView` — آمار بازه، **دونات** تفکیک نوع (`donut_segments`)، تفکیک پروژه،
    روند روزانه، تب تقویم شخصی (embed)، تب تسک‌ها.
  - CRUD + archive/restore.
- `forms.py` — نقش چک‌باکسی، `join_date` با `jdate`، توضیحات `rich-editor` + `clean_html`.

## نکته
`.who/.spark/.donut-legend` باید در `static/css/style.css` باشند (بودند نبودند → رفع شد).
