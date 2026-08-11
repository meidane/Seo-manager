# dashboard/ — ویو تجمیعی

`DashboardView(LoginRequiredMixin, DateRangeMixin, TemplateView)` در `views.py`.

## اصل
همه‌ی آمار با **یک کوئری `annotate(filter=Q(...))`** یا `aggregate` — هرگز حلقه‌ی پایتونی
روی پروژه‌ها/همکاران. الگو را از همین‌جا کپی کن.

## بخش‌ها (context)
- `cards` — انجام/باقی/عقب/کلمات/مالی + درصد مقایسه با بازه‌ی قبل (`get_previous_range`)
- `alerts` — عقب‌افتاده، پروژه‌ی بدون‌برنامه، انجام‌شده بدون لینک، بازبینی‌نشده (شرطی)
- `projects` + `project_columns` — annotate شرطی + مرتب‌سازی بدترین‌بالا (state)؛ ستون‌های
  جدول از `core.columns.get_columns('projects','dashboard')` می‌آیند، رندر با `{% column_cell %}`
  (تمپلیت `templates/dashboard/index.html`). تنظیم در `/settings/columns/`.
- `colleagues` + `colleague_columns` — annotate planned/done/words/minutes/overdue؛ همان
  الگوی ستونِ سفارشی‌سازی‌شده (جدول `colleagues`، محل `dashboard`).
- `review_feed` / `alerts.unreviewed` — از `tasks.queries.reviewable_q(request)` می‌آیند
  (همان معیارِ `TaskReviewView`)، **نه** `published_url` خالی/پر (باگِ قبلی: فیلترِ
  `.exclude(published_url='')` مالِ سئوی هارد‌کدِ قدیمی بود؛ چون انواعِ سفارشیِ جدید اصلاً
  `published_url` پر نمی‌کنند، همیشه خالی می‌ماند — فیدِ بازبینی هیچ‌وقت چیزی نشان نمی‌داد).
- `daily_groups` — **جدول، نه نمودار** (نمودارِ میله‌ایِ قبلی طبقِ درخواستِ کاربر حذف شد).
  از `tasks.queries.group_done_by_day(task_qs, today-6d, today)` می‌آید (همان تابعِ
  گروه‌بندیِ `?group=day`ِ صفحه‌ی تسک‌ها — منبعِ واحد، `tasks/CLAUDE.md`)، ثابت روی
  **۷ روز اخیر** (مستقل از بازه‌ی سراسری). تمپلیت هر روز را با تیتر+جدولِ کوچک (عنوان/
  پروژه/مسئول/نوع) رندر می‌کند؛ کلیک روی ردیف مودالِ تسک را باز می‌کند (`data-open-task`،
  دلیگیتِ سراسریِ `tasks.js`). دکمه‌ی «همه» می‌برد به `tasks:list?group=day` (بازه‌ی
  سراسری، نه فقط ۷ روز — تفکیکِ روزانه‌ی همان صفحه‌ی تسک‌ها، نه صفحه‌ی جدید).

## TODO
- کارت مالی (`balance=0`) → بعد از ساخت `finance` وصل شود
- تب‌های امروز/دیروز/۷روز جدول همکاران (AJAX) · کشوی جزئیات همکار · دونات/هیت‌مپ · کش ۶۰ثانیه
