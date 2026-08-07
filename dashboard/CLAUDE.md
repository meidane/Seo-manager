# dashboard/ — ویو تجمیعی

`DashboardView(LoginRequiredMixin, DateRangeMixin, TemplateView)` در `views.py`.

## اصل
همه‌ی آمار با **یک کوئری `annotate(filter=Q(...))`** یا `aggregate` — هرگز حلقه‌ی پایتونی
روی پروژه‌ها/همکاران. الگو را از همین‌جا کپی کن.

## بخش‌ها (context)
- `cards` — انجام/باقی/عقب/کلمات/مالی + درصد مقایسه با بازه‌ی قبل (`get_previous_range`)
- `alerts` — عقب‌افتاده، پروژه‌ی بدون‌برنامه، انجام‌شده بدون لینک، بازبینی‌نشده (شرطی)
- `projects` — annotate شرطی + مرتب‌سازی بدترین‌بالا (state)
- `colleagues` — annotate done/words/open/overdue
- `review_feed` — تسک‌های done بدون بازبینیِ دارای لینک
- `daily_bars` — `_daily_series` (الگوی گروه‌بندی روزانه برای نمودار/هیت‌مپ)

## TODO
- کارت مالی (`balance=0`) → بعد از ساخت `finance` وصل شود
- تب‌های امروز/دیروز/۷روز جدول همکاران (AJAX) · کشوی جزئیات همکار · دونات/هیت‌مپ · کش ۶۰ثانیه
