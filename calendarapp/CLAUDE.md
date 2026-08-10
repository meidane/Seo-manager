# calendarapp/ — تقویم شمسی (بدون مدل)

روی داده‌ی `tasks.Task` کار می‌کند. **قلب مدیریت روزانه.**

## فایل‌ها
- `calendar_logic.py` — منطق ماتریس ماه در **پایتون** (نه JS). `build_month(jyear, jmonth,
  tasks_by_date, holiday_map)`. **weekday شمسی: شنبه=۰، جمعه=۶.** هر سلول `jdate` (شمسی لاتین)
  برای پرکردن فیلد تاریخ دارد.
- `views.py` — `CalendarView` (SSR اول)، `calendar_api` (ناوبری AJAX + فیلتر project/assignee/type_def —
  فیلترِ نوع دیگر با `task_type` خام نیست، با `type_def`(id)؛ `?type=` قدیمی فقط fallback است)،
  `picker_api` (فقط پرچم تعطیلی/امروز برای دیت‌پیکر)، `workload_api` (بار کاری همکار برای مودال).
  `_tasks_by_date` تسک‌های انجام‌شده را ته سلول مرتب می‌کند (طوسی).
  **`_virtual_recurrence`/`_merge_virtual`**: رخدادهای آینده‌ی قواعدِ تکرار را به‌صورت
  «مجازی» (بدون ساختِ رکورد، با `raw_next_date`) برای نمایشِ محوِ کلِ ماه اضافه می‌کند
  (کلاس `.tk.virtual`، غیرقابل‌کلیک). تاریخ‌هایی که تسکِ واقعی دارند رد می‌شوند.
- `static/js/calendar-page.js` — رندر سلول‌ها، آواتار نویسنده، دکمه‌ی + (hover → `openTask(null,{planned_date_fa})`),
  درگ‌ودراپ بین روزها (`PATCH planned_date_iso`).
- `static/js/calendar-embed.js` — تقویم قابل‌جاسازی در تب‌ها (`data-project`/`data-assignee`).
- `static/js/datepicker.js` — دیت‌پیکر شمسی برای هر `input.jdate` (تعطیلات قرمز).

## استایل
همه‌ی کلاس‌های تقویم (`.grid7 .cell .tk .tk-av .cell-add .dp-*` …) در `static/css/style.css`
هستند. (یک‌بار نبودند و تقویم خراب دیده شد — هرگز فقط در mockups نگذار.)

## URLها
`/calendar/` · `/calendar/api/` · `/calendar/api/picker/` · `/calendar/api/workload/`

## TODO
نمای هفته و لیست (فقط ماه ساخته شده) · اتصال workload به دیت‌پیکرِ مودال.
