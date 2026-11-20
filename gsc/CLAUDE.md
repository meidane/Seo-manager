# gsc/ — سرچ کنسول (Google Search Console)

اتصال با **Service Account** (کلیدِ JSON، رمزنگاری‌شده در `GSCAccount.credentials_enc`) + **پراکسیِ اختیاری** (`GSCAccount.proxy`،
برای سرورِ ایران → واسطِ خارج؛ همهٔ درخواست‌ها از آن می‌روند). کلاینت (`client.py`) JWT را با `cryptography` امضا می‌کند — بدونِ
وابستگیِ تازه. توکن ۵۰ دقیقه در cache.
- **تلهٔ پراکسی (بیت‌مان زد):** `requests` پراکسیِ متغیرهای محیطی (`HTTPS_PROXY`) را بر `Session.proxies` مقدم می‌کند → پراکسیِ پنل بی‌اثر
  می‌شد. با پراکسی، `trust_env=False`.
- **واسط (relay) — راهِ پیشنهادیِ سرورِ ایران:** `GSCAccount.relay_url` (مثلاً `https://middle.lomin.co`) + `relay_key` (هدرِ
  `X-Relay-Key`). اگر پر باشد بر پراکسی مقدم است: توکن به `<relay>/oauth2/token` (ولی `aud` همان آدرسِ واقعیِ گوگل) و API به
  `<relay>/webmasters/v3/...` (همان مسیرِ گوگل). سمتِ سرورِ خارج: `deploy/gsc-relay.sh <دامنه> <ایمیل>` (nginx + Let's Encrypt، فقط این دو
  مسیر، بدونِ کلید `403 relay: bad key` که کلاینت به پیامِ «کلیدِ واسط یکی نیست» تبدیل می‌کند).
- **تلهٔ واسط (بیت‌مان زد — 404ِ HTMLِ گوگل در همگام‌سازی، با این‌که فهرستِ سایت‌ها می‌آمد):** `proxy_pass` با مسیر (`…com/;`)
  URI را normalize/decode می‌کند → `sites/https%3A%2F%2Fx.com%2F/…` به `sites/https:/x.com/…` تبدیل می‌شد. راهِ درست: `location
  /webmasters/` + `proxy_pass https://www.googleapis.com;` (بدونِ مسیر = URIِ خام دست‌نخورده). `$request_uri`+متغیر هم double-encode
  می‌کند. اصلاحِ سرورِ قبلی: sedِ `googleapis/`→`webmasters/` (در `DEPLOY.md`).
- **چند کلید:** `GSCCredential` (کلیدهای اضافه، ترجیحاً در پروژهٔ دیگرِ Google Cloud برای سایتِ پرداده) + `GSCSite.credential`
  (خالی = کلیدِ اصلیِ `GSCAccount`). `refresh_sites` همهٔ کلیدها را می‌گردد؛ سایتی که فقط کلیدِ اضافه می‌بیند خودکار به آن وصل می‌شود.
- **سهمیه:** درخواست‌ها روز‌به‌روز (`CHUNK_DAYS=1`)، مکثِ `PAUSE` بینشان، و تلاشِ دوباره با تأخیرِ نمایی روی 429/5xx/403ِ quota.

## داده (`models.py`, `sync.py`)
- `GSCSite` = property (`sc-domain:x.com` یا `https://x.com/`)؛ با دامنهٔ پروژه **خودکار جفت** می‌شود (`refresh_sites`)، دستی هم از
  `/settings/gsc/`. فقط سایت‌های جفت‌شده با پروژه همگام می‌شوند.
- `GSCPage(site, key, url)` = هر صفحه **یک بار** (آدرسِ فارسیِ کدشده طولانی است؛ قبلاً در هر ردیف تکرار می‌شد → حجم ۳-۴ برابر).
  `key` = `urls_norm.page_key` (میزبان بی‌www + مسیرِ decodeشده بی‌اسلش) تا لینکِ تسک با گوگل جور شود؛ نسخه‌های کدشده/نشده یکی می‌شوند.
  `GSCQueryDay` (روز×صفحه×کلمه) + `GSCPageDay` (روز×صفحه؛ جمعِ دقیقِ صفحه) با FKِ `page`. پیداکردنِ صفحه: `analysis._pid(site, key)`.
- **حداکثر ۶ ماه** (`sync.KEEP_DAYS=180`، خواستِ کاربر): بیشتر از آن نه گرفته می‌شود نه می‌ماند — `prune` بعد از هر همگام‌سازی
  قدیمی‌ترها و صفحه‌های بی‌داده را پاک می‌کند. خلاصهٔ ماهانه/کشِ تحلیل عمداً نداریم (خواستِ کاربر).
- همگام‌سازی ایدمپوتنت: بازه پاک و دوباره درج؛ هر بار از `synced_until - 3` تا ۲ روز قبل (بارِ اول `days_back` روز، پیش‌فرض ۹۵، سقف ۱۸۰).
  روزبه‌روز با صفحه‌بندیِ ۲۵هزارتایی؛ صفحه‌های تازه با `_page_ids` یک‌جا ساخته می‌شوند. **خودکار بدونِ cron:** `middleware.AutoSyncMiddleware` (هر ۱۰ دقیقه یک چکِ سبک با `cache.add`؛ اگر `sync.due` = بیش از ۲۰ ساعت از
  آخرین همگام‌سازی/تلاش → نخِ پس‌زمینه). قفلِ اتمیکِ `sync.claim` (`syncing`+`sync_started`، قفلِ بالای ۳ ساعت = گیرکرده) جلوی اجرای
  هم‌زمان را بینِ ورکرها/دکمه/cron می‌گیرد. `python manage.py gsc_sync` فقط برای اجرای دستی/cronِ اختیاری. دکمهٔ «همگام‌سازیِ الان» = نخِ پس‌زمینه +
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
