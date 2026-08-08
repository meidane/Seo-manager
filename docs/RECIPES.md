# RECIPES — دستورالعمل افزودن/تغییر (قبل از هر feature بخوان)

هدف: بدون grep و بدون خواندن فایل‌های اضافی، دقیقاً بدانی کدام ۳-۴ فایل را دست بزنی.

---

## نقشه‌ی سطح (Surface Map): URL → view → template → JS/CSS
| صفحه | url | view | template | js |
|---|---|---|---|---|
| داشبورد | `/` | `dashboard/views.py` | `dashboard/index.html` | — |
| پروژه‌ها | `/projects/` | `projects/views.py:ProjectListView` | `projects/list.html` | — |
| سینگل پروژه | `/projects/<id>/` | `ProjectDetailView` | `projects/detail.html` | inline (فایل/تب) + calendar-embed |
| همکاران | `/colleagues/` | `ColleagueListView` | `colleagues/list.html` | — |
| سینگل همکار | `/colleagues/<id>/` | `ColleagueDetailView` | `colleagues/detail.html` | calendar-embed |
| تسک‌ها | `/tasks/` | `tasks/views.py:TaskListView` | `tasks/list.html` | tasks.js (سراسری) |
| بازبینی | `/tasks/review/` | `TaskReviewView` | `tasks/review.html` | inline |
| تقویم | `/calendar/` | `calendarapp/views.py` | `calendarapp/index.html`+`_cells.html` | calendar-page.js |
| گزارش‌ها | `/reports/` | `reports/views.py` | `reports/{list,detail,public,_groups}.html` | inline |
| انواع تسک | `/settings/task-types/` | `tasks/type_views.py` | `settings/task_type*.html` | inline |
| تعطیلات | `/settings/holidays/` | `core/views.py` | `settings/holidays.html` | — |
| مودال تسک (سراسری) | — | `tasks/api.py` | ساخته‌شده در JS | `tasks.js`+`task-schema.js` |

JS سراسری (در `base.html` برای کاربر واردشده): `app.js, datepicker.js, richtext.js, task-schema.js, tasks.js`.
CSS: **همه** در `static/css/style.css`.

---

## افزودن فیلد به تسک
1. فیلد در `tasks/models.py` (+ `makemigrations tasks && migrate`).
2. اگر شرطیِ نوع است: گروه در `static/js/task-schema.js`؛ اگر همیشگی: به `ALWAYS` در `tasks.js`.
3. اینپوت در `modalHtml` (`tasks.js`) + کلید در `collect()`.
4. پذیرش در `apply_fields` (`tasks/api.py`): لیست TEXT/INT/DECIMAL/CHOICE مناسب + در GET `task_detail`.
5. اگر باید در لیست/تقویم دیده شود: `Task.to_dict()`.

## افزودن ستون آمار به داشبورد/جدول
- در view مربوط: `annotate(x=Count('tasks', filter=Q(...)))` یا `Sum(..., filter=Q(...))`.
- **هرگز حلقه‌ی پایتونی روی رکوردها.** برای N+1: `select_related('project','assignee','type_def')`.
- ستون در تمپلیت با `|fa_digits`.

## افزودن یک صفحه‌ی جدید (در اپ موجود)
1. view (`LoginRequiredMixin` [+`DateRangeMixin` اگر آماری]).
2. مسیر در `<app>/urls.py`.
3. تمپلیت که `base.html` را extends می‌کند (`{% load static seo_extras %}`).
4. لینک در `templates/components/sidebar.html` (کلاس `on` با `resolver_match`).
5. استایلِ لازم در `static/css/style.css`.

## افزودن اپ جدید (مثل finance)
1. پوشه با `__init__, apps.py, models.py, views.py, urls.py, admin.py, migrations/__init__.py`.
2. ثبت در `config/settings.py: LOCAL_APPS` (مراقب تکراری‌نبودن).
3. `include` در `config/urls.py`.
4. لینک سایدبار. مدل‌ها → `makemigrations <app> && migrate`.
5. `CLAUDE.md` همان اپ را بنویس + این فایل و ریشه را به‌روز کن.

## افزودن API JSON
```python
@login_required
@require_http_methods(['POST'])   # یا GET/PATCH/DELETE
def my_view(request, pk):
    data = json.loads(request.body or '{}')
    ...
    return JsonResponse({...}, status=201)
```
فرانت: `App.fetchJSON(url, {method, body})` (CSRF خودکار). خروجی HTML ادیتور → `clean_html`.

## افزودن فیلد تاریخ (شمسی)
اینپوت با کلاس `jdate` → دیت‌پیکر خودکار باز می‌شود. سمت سرور `parse_jalali(value)`.

## افزودن ادیتور غنی به یک فیلد
`<textarea class="rich-editor">` → TinyMCE خودکار. سمت سرور `clean_html(value)`.

## اجرای تست سریع (الگو)
سرور را بالا بیاور، لاگین کن، با `curl -b cookiejar` صفحات را بزن. برای تست بصری:
Chromium در `/opt/pw-browsers/chromium-1194/chrome-linux/chrome` + کوکی از cookiejar.
(نمونه‌ی کامل در تاریخچه‌ی کامیت‌ها موجود است.)
