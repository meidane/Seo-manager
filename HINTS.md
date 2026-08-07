# راهنمای ادامه‌ی کار (HINTS)

این فایل نقشه‌ی ذهنی پروژه است تا هر جلسه‌ی بعدی **بدون کاوش دوباره‌ی کل کد**
بداند چه چیزی کجاست، چه چیزی آماده است و نقطه‌ی اتصال گام بعد کجاست.
> قانون طلایی: قبل از کدنویسی، بخش مربوط به همان گام را اینجا بخوان.

---

## معماری در یک نگاه

- **استک:** Django 5 + Vanilla JS (بدون بیلد، بدون DRF). API‌ها با `JsonResponse`.
- **قانون تاریخ:** همه‌ی تاریخ‌ها در DB **میلادی**‌اند. تبدیل شمسی فقط در نمایش
  (`|jalali`) و ورودی (`core.jalali.parse_jalali`). هیچ‌جا تاریخ شمسی ذخیره نکن.
- **بازه‌ی سراسری:** `core.daterange.DateRangeMixin` → `get_range(request)` و
  `range_context()`. در session ذخیره می‌شود. هر ویو آماری از همین استفاده کند.
- **AJAX:** فرانت از `App.fetchJSON/toast/openModal/confirm` در `static/js/app.js`
  استفاده می‌کند؛ CSRF خودکار ست می‌شود.
- **سیستم طراحی:** فقط متغیرهای CSS در `static/css/style.css`. رنگ hard-code نکن.
  ماک‌آپ استاتیک همه‌ی صفحات در `mockups/` (مرجع بصری، مطابق designpreview).

## نگاشت اپ‌ها ← گام‌ها

| اپ | مدل‌ها | وضعیت |
|---|---|---|
| `core` | TimeStampedModel, Attachment, ActivityLog, Holiday | کامل |
| `accounts` | User, Team | کامل (Team فقط ساخته شده، فاز ۳) |
| `colleagues` | Colleague | CRUD + آمار سینگل + دونات + تقویم شخصی کامل (گام ۶) |
| `projects` | Project, Credential | CRUD + آمار سینگل + تب تسک/تقویم؛ files/reports/finance placeholder |
| `tasks` | Task, TaskComment | مدل و API کامل |
| `calendarapp` | — (روی Task) | ماه/AJAX/drag کامل؛ هفته/لیست ناقص |
| `dashboard` | — (تجمیعی) | کارت‌ها/جدول‌ها/فید کامل؛ نمودارها/تب‌ها ناقص |
| `reports` | — | **ساخته نشده (گام ۷)** |
| `finance` | — | **ساخته نشده (گام ۸)** |

---

## نقاط اتصال آماده برای گام‌های بعد

### تسک‌ها (`tasks/`)
- **افزودن فیلد جدید به تسک:** ۱) فیلد در `tasks/models.py` ۲) در گروه مناسب
  `static/js/task-schema.js` (کدام نوع نمایش دهد) ۳) در لیست‌های `apply_fields`
  در `tasks/api.py` (TEXT/INT/DECIMAL/CHOICE). همین سه نقطه، تمام.
- `apply_fields()` منبع واحد ذخیره‌ی فیلدها از JSON است (هم create هم update).
- درگ تقویم پارامتر `planned_date_iso` (میلادی) می‌فرستد؛ فرم مودال `planned_date`
  (شمسی) می‌فرستد. هر دو در `apply_fields` هندل شده‌اند.
- **کامنت تسک UI:** endpoint `api/<id>/comments/` آماده است؛ فقط UI در مودال بماند (TODO).
- **کانبان drag:** در `static/js/tasks.js` → `PATCH api/<id>/status/`. کار می‌کند.

### تقویم (`calendarapp/`)
- منطق ماتریس در `calendar_logic.build_month()` — پایتونی، یک‌جا. weekday شمسی: شنبه=۰.
- **حالت انتخابگر تاریخ داخل مودال تسک + بار کاری همکار:** endpoint آماده است:
  `GET /calendar/api/workload/?assignee=&year=&month=` → `{workload:{iso:count}, total}`.
  کاری که مانده: در مودال تسک روی کلیک فیلد تاریخ، یک تقویم کوچک باز شود که این
  workload را بگیرد و اعداد روی روزها + پررنگ‌کردن تسک‌های همان همکار را نشان دهد.
- **نمای هفته و لیست (TODO):** فعلاً فقط ماه. برای هفته، یک تابع `build_week` مشابه
  `build_month` بنویس؛ برای لیست، تسک‌های بازه را مرتب‌شده نشان بده.
- **هشدار روز تعطیل هنگام ذخیره:** منطق `_next_workday` در `tasks/api.py` هست
  (برای bulk skip_holidays). برای «هشدار نرم» موقع ذخیره‌ی تکی، در فرانت چک کن.

### داشبورد (`dashboard/views.py`)
- همه‌ی آمار با `annotate(..., filter=Q(...))` — الگو را کپی کن، حلقه‌ی پایتونی نزن.
- **کارت مالی + ستون مانده‌ی پروژه:** الان `balance=0`. بعد از ساخت `finance`
  (گام ۸)، از `FinanceEntry` مانده = Σ بدهکار − Σ بستانکار محاسبه و اینجا تزریق کن.
- **تب‌های امروز/دیروز/۷روز جدول همکاران (TODO):** یک ویو AJAX در `dashboard/urls`
  اضافه کن که `?period=today|yesterday|7d` بگیرد و همان annotate را با بازه‌ی
  متناظر اجرا و partial جدول را برگرداند.
- **کشوی جزئیات همکار (TODO):** API «تسک‌های همکار در روز X» + یک drawer در فرانت.
- **نمودار دونات نوع تسک، هیت‌مپ ۱۲ هفته، اسپارک‌لاین همکار (TODO):** الگوی
  گروه‌بندی در `_daily_series()` است. برای دونات: `values('task_type').annotate(Count)`.
  برای هیت‌مپ: همان counts روزانه در بازه‌ی ۱۲ هفته. SVG دستی (بدون کتابخانه).
- **کش ۶۰ ثانیه‌ای:** طبق سند بخش ۱۴، دور آمار داشبورد `cache.get_or_set` بگذار
  (هنوز نگذاشته‌ام تا در توسعه داده تازه ببینی).

### گزارش‌ها (گام ۷ — ساخته نشده)
- مدل‌ها: `Report(project,title,date_from,date_to,description,status,public_token,is_public)`
  و `ReportItem(report,task(FK null),title,task_type,display_date,url,note,is_manual,order)`.
- **کلید طراحی:** ReportItem یک **snapshot** است (کپی از تسک)، تا ویرایش بعدی تسک
  گزارشِ تحویل‌شده را عوض نکند. «واکشی تسک‌ها» = کپی تسک‌های done بازه در ReportItemها.
- لینک عمومی `/r/<uuid>/` بدون `login_required` (تنها استثنا).
- ماک‌آپ آماده: `mockups/reports.html`, `mockups/report-detail.html`.

### حسابداری (گام ۸ — ساخته نشده)
- مدل `FinanceEntry(project,report(null),entry_type[debit/credit],title,amount,date,note)`.
  amount همیشه مثبت؛ تفکیک بدهکار/بستانکار با entry_type.
- مانده‌ی پروژه = Σ بدهکار − Σ بستانکار. خروجی اکسل با `openpyxl` (در requirements هست).
- ماک‌آپ آماده: `mockups/finance.html`.

### فایل‌ها و ادیتور (میان‌گام)
- مدل `Attachment` (GenericFK) در `core` آماده است. یک endpoint آپلود
  (`POST /api/attachments/`) + یک کامپوننت drag&drop فرانت بساز؛ به هر مدلی وصل شود.
- ادیتور غنی: TinyMCE self-host در `static/vendor/` (طبق پیوست ب). فعلاً توضیحات
  همه‌جا `<textarea>` است. موقع اتصال TinyMCE، پاکسازی با `bleach` در save.

---

## تله‌ها و نکات که وقت‌گیر بودند (تکرار نکن)

- `cryptography` سیستمی گاهی panic گذرا می‌دهد؛ `pip install --force-reinstall
  cryptography` یا صرفاً یک‌بار دوباره اجرا. در محیط تازه با requirements درست است.
- `TimeField` را با `default=time(8,0)` بده، نه رشته‌ی `'08:00'` (وگرنه روی نمونه‌ی
  تازه `strftime` ندارد).
- `INSTALLED_APPS`: مراقب افزودن تکراری اپ باش (خطای «labels aren't unique»).
- push فقط با URL کوچک‌حروف `meidane/seo-manager` کار می‌کند؛ ریموت روی
  `Seo-manager` ریدایرکت می‌دهد ولی push موفق است.
- برای تست سریع: کاربر `admin/admin1234`، سپس seed دستی در شل جنگو.

## دستورهای پرکاربرد

```bash
python manage.py migrate
python manage.py seed_holidays 1405
python manage.py createsuperuser        # یا admin/admin1234 در شل
python manage.py runserver
```

## چک‌لیست گام‌های باقی‌مانده (از سند)
- [x] گام ۶: آمار سینگل پروژه/همکار + تب تقویم آن‌ها + میان‌بر کیبورد بازبینی
      (تقویم قابل‌جاسازی: `static/js/calendar-embed.js` با data-project/data-assignee)
- [ ] گام ۷: گزارش‌دهی (Report/ReportItem + چاپ + لینک عمومی)
- [ ] گام ۸: حسابداری (FinanceEntry + داشبورد مالی + اکسل)
- [ ] گام ۹: جستجوی سراسری، ریسپانسیو موبایل، empty stateها، ایندکس‌ها، seed_demo
- [ ] تکمیل‌های TODO بالا (تب‌های داشبورد، دونات/هیت‌مپ، datepicker+workload در مودال،
      نمای هفته/لیست تقویم، UI کامنت، آپلود فایل، TinyMCE)
