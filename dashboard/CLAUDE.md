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
- `review_feed` — تسک‌های done بدون بازبینیِ دارای لینک
- `daily_bars` — `_daily_series` (الگوی گروه‌بندی روزانه برای نمودار/هیت‌مپ)

## TODO
- کارت مالی (`balance=0`) → بعد از ساخت `finance` وصل شود
- تب‌های امروز/دیروز/۷روز جدول همکاران (AJAX) · کشوی جزئیات همکار · دونات/هیت‌مپ · کش ۶۰ثانیه
