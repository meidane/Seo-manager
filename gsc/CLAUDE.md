# gsc/ — سرچ کنسول (Google Search Console)

اتصال با **Service Account** (کلیدِ JSON، رمزنگاری‌شده در `GSCAccount.credentials_enc`) + **پراکسیِ اختیاری** (`GSCAccount.proxy`،
برای سرورِ ایران → واسطِ خارج؛ همهٔ درخواست‌ها از آن می‌روند). کلاینت (`client.py`) JWT را با `cryptography` امضا می‌کند — بدونِ
وابستگیِ تازه. توکن ۵۰ دقیقه در cache.

## داده (`models.py`, `sync.py`)
- `GSCSite` = property (`sc-domain:x.com` یا `https://x.com/`)؛ با دامنهٔ پروژه **خودکار جفت** می‌شود (`refresh_sites`)، دستی هم از
  `/settings/gsc/`. فقط سایت‌های جفت‌شده با پروژه همگام می‌شوند.
- `GSCQueryDay` (روز×صفحه×کلمه) + `GSCPageDay` (روز×صفحه؛ جمعِ دقیقِ صفحه، چون کلماتِ ناشناس در اولی نیستند). همه ذخیره می‌شود
  (برای تحلیل‌های بعدی). `page_key` = `urls_norm.page_key` (میزبان بی‌www + مسیرِ decodeشده بی‌اسلش) تا لینکِ تسک با گوگل جور شود.
- همگام‌سازی ایدمپوتنت: بازه پاک و دوباره درج؛ هر بار از `synced_until - 3` تا ۲ روز قبل (بارِ اول `days_back` روز، پیش‌فرض ۹۵).
  تکه‌های ۳۰روزه با صفحه‌بندیِ ۲۵هزارتایی. **cron شبانه:** `python manage.py gsc_sync`. دکمهٔ «همگام‌سازیِ الان» = نخِ پس‌زمینه +
  پولِ `/settings/gsc/status/`.

## تحلیل — منبعِ واحد `analysis.py` (ایندکس بالای فایل)
- `task_pages(task)`: صفحه‌های تسک که property دارند — لینکِ صفحهٔ تسک (`Task.page_link`) و لینک‌های هدفِ رپورتاژ (`is_link_source`).
- `task_card` → کارتِ **خودکارِ زیرِ مودالِ تسک** (`tasks.js` → `GSC.taskCard`): کلماتِ ۳ ماه (کلیک/ایمپرشن/CTR/جایگاه) + نمودار
  + اگر انجام شده «اثرِ این تسک» (`impact`: ۲۸ روز قبل/بعد از `done_date`؛ اگر هنوز نگذشته با همان تعداد روز).
- `project_analysis` → تبِ «تحلیلِ سرچ کنسول»ِ پروژه (فقط اگر property جفت شده): پیشنهادها (افتِ صفحه ≥۳۰٪، نزدیکِ صفحهٔ اول ۸–۲۰،
  CTR پایین نسبت به `EXPECTED_CTR`، رقابتِ صفحه‌ها) + اثرِ کارها (قبل/بعدِ هر تسک، مقایسهٔ انواع، هزینه به‌ازای هر کلیکِ رپورتاژ
  از فیلدِ «هزینه» — `mcpgate.panel.reports._cost`). جایگاه = میانگینِ وزنی با ایمپرشن.
- MCP: `briefs_for/page_brief` در `skills_start` (کلید `search_console` وقتی لینک یا تسک در درخواست است) + ابزارهای پنل
  `gsc_page(url|task)` و `gsc_project(project)` (`project_brief`، جدول‌های فشرده).

## فرانت
`static/js/gsc.js` (منبعِ واحد: `chart` تک‌سری/تک‌محور — جایگاه با محورِ وارونه — تولتیپِ هاور، `queryTable` مرتب‌شونده، `taskCard`,
`projectTab`) + بلوکِ «سرچ کنسول» در `style.css` (`.gsc-*`). تنظیمات: `templates/gsc/settings.html` (گیت `manage_api_tokens`).
- **تله:** عددِ علامت‌دار («+۴۰») در RTL برعکس دیده می‌شود — داخلِ `<bdi dir="ltr">`.
