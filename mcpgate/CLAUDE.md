# mcpgate/ — دروازهٔ MCP: ChatGPT/Claude → پنل → سایت‌ها

پنل خودش **سرورِ MCP (Streamable HTTP، بی‌حالت، JSON-RPC با `JsonResponse`)** است. هیچ درخواستی مستقیم از
ChatGPT/Claude به سایت نمی‌رود؛ پنل با دسترسیِ ذخیره‌شدهٔ هر سایت درخواست می‌دهد (برای سایت‌هایی که از سرورهای
OpenAI/Anthropic در دسترس نیستند). **عمداً بدونِ محدودیت** (خواستِ صریحِ کاربر): REST آزاد + همهٔ ابزارهای Novamira.

- **مدل‌ها** (اسکوپِ صریح با FK، نه TenantManager — endpoint بدونِ سشن است):
  `MCPGate` (یکی برای هر سازمان؛ `token` **خام** ذخیره می‌شود تا آدرس همیشه قابلِ کپی باشد — برخلافِ `APIToken` که هش است)،
  `MCPSite` (key/url/wp_user/`password` رمزنگاری‌شده با Fernet/`mcp_path`/active/`last_check`)، `MCPLog` (هر فراخوانی + `backup` =
  JSONِ قبلیِ چیزی که `wp_save_post`/`wp_save_term` ویرایش کرد).
- **endpoint:** `/mcp/<token>/` (یا `/mcp/` با `Authorization: Bearer <token>`)، `csrf_exempt` + CORS. `views._handle`:
  initialize / tools/list / tools/call / ping؛ notification → 202. هر خطای ابزار → `isError` (هرگز ۵۰۰).
- **ابزارها** (`tools.py: TOOLS` + `run`): `sites`, `wp_check`, `wp_api` (هر مسیر/متد)، `site_tools`/`site_call` (پراکسیِ MCPِ سایت)،
  `wp_find`, `wp_get`, `wp_save_post`, `wp_save_term`, `wp_upload_media` (URL/base64)، `wp_internal_links`.
  نسخهٔ پایتونیِ `chatgpt-connector/plugin/server/wp.mjs` است (بدونِ پرامپت/فایل/تحقیقِ رقبا — آن‌ها مالِ برنامهٔ ویندوزی‌اند).
- **کلاینت** (`wp.py`): `request` (Application Password؛ پاسخِ HTML از `/wp-json/` → یک بار `?rest_route=` و کش ۱روز)،
  `mcp` = کلاینتِ MCPِ سایت: initialize → `Mcp-Session-Id` → `notifications/initialized` → متد؛ پاسخِ JSON یا SSE؛ سشن ۲۰دقیقه
  در cache، 400/404 → سشنِ تازه. مسیر: `mcp_path` (پیش‌فرض `mcp/novamira`) و بعد `mcp/mcp-adapter-default-server`؛ مسیرِ کارکرده
  روی سایت ذخیره می‌شود. **Novamira** (افزونهٔ وردپرس، novamira.ai): اجرای PHP، فایل‌ها، WP-CLI — باید در Novamira → Configuration
  «AI abilities» روشن باشد.
- **صفحه:** `/settings/mcp/` (گیت `manage_api_tokens`، تب در `settings/_nav.html`): آدرس + کپی/توکنِ جدید/فعال، راهنمای ChatGPT
  (Developer mode → Create, No authentication) و Claude (Add custom connector)، جدولِ سایت‌ها (مودال + «تستِ اتصال»)، لاگ.
- **ایمپورت از برنامهٔ ویندوزی:** `views.import_from_sync` سایت‌ها را از انبارِ `connector.SyncStore` می‌خواند (ادغام با key).
  بارِ اولِ صفحه وقتی هیچ سایتی نیست خودکار، بعداً دکمهٔ «دریافت از ChatGPT-WP».
- **زمان:** gunicorn پیش‌فرض ۳۰ثانیه کارگر را می‌کشد → `deploy/teams.service` `--timeout 180 --threads 4` و nginx `proxy_read_timeout 180s`.

## تست
`scratchpad`-مانند: یک وردپرسِ ساختگیِ پایتونی (REST + `mcp/novamira` با session و پاسخِ SSE) بالا بیاور، `MCPSite` بساز و با curl
`initialize` / `tools/list` / `tools/call` را روی `/mcp/<token>/` بزن (همهٔ ابزارها + خطای سایتِ ناموجود + توکنِ غلط → 401).

## MCPِ خودِ پنل — `/mcp/<token>/panel/` (همان توکن، کانکتورِ جدا تا هر گفتگو فقط ابزارهای لازم را بار کند)
ابزارها در `panel/registry.py` (`TOOLS` با توضیحِ کوتاه + `INSTRUCTIONS` که قالبِ ردیفِ تسک را یک‌جا می‌گوید + `HANDLERS`):
`panel_info`, `find`, `tasks_query/task_get/tasks_save/tasks_update_where/tasks_delete/tasks_restore/task_comment/task_review`,
`projects_query/project_get/project_save`, `import_inspect/import_tasks`, `stats/project_health`,
`reports_query/report_get/report_create/report_update`, `tx_queue/tx_suggest/tx_query/finance_stats`, `actions_list/undo`.
- **اجراکننده:** `MCPGate.user` (اولین کسی که صفحهٔ `/settings/mcp/` را باز کرد؛ وگرنه مالک). `panel/ctx.fake_request` یک درخواستِ
  ساختگی با user/organization/membership می‌سازد تا **کدِ موجودِ پنل** (`tasks.api.apply_fields`، `_custom_fields_error`، ویوهای
  `task_review`/`task_comments` با `ctx.call_view`) عیناً اجرا شود — منطقِ ذخیره تکرار نشده. `registry.run` سازمانِ جاری را ست می‌کند.
- **کم‌مصرف:** خروجیِ جدولی `{'cols','rows'}`، پیش‌فرض ۲۰ ردیف + `next_offset`، `fields` اختیاری، پیداکردنِ پروژه/فرد/نوع/بابت با نام
  یا دامنه سمتِ سرور (`ctx.Resolver`، با پیشنهادِ «منظورت…؟»)، آمار سمتِ سرور (`stats`)، پیش‌نمایش فقط شمارش + ۵ نمونه.
- **تاریخ:** ورودی شمسی یا ISO (`ctx.pdate`، سال<۱۷۰۰ = شمسی)، خروجی شمسی. ماهِ گزارش «1403-07»/«مهر 1403»/none.
- **ژورنال/بازگردانی (`journal.py`):** هر ابزارِ نویسنده داخلِ `with journal.Batch(org, user, tool, summary)` (= `transaction.atomic`؛
  خطا = هیچ تغییری نمی‌ماند؛ دستهٔ بدونِ تغییر حذف). `snap` قبل، `note_update/note_create/note_hard_delete` بعد — فقط فیلدهای عوض‌شده
  ذخیره می‌شوند. `undo` معکوس: ساخته‌شده → حذفِ نرم (اگر `deleted_at` دارد) وگرنه حذف؛ ویرایش → مقدارِ قبل؛ حذف → بازیابی؛ `purge` →
  بازسازی با همان id. رکوردی که بعداً دستی عوض شده (مقدارِ فعلی ≠ `after`) رد می‌شود مگر `force`. خودِ undo هم یک دسته است.
- **تاریخچهٔ تسک:** `TaskHistory.source='mcp'` + `batch_id` (خودکار از `current_batch()` در `tasks.history.record`) → در مودال برچسبِ
  «MCP #n» با لینک به `/settings/mcp/log/<n>/`.
- **صفحهٔ لاگ:** `/settings/mcp/log/` (`views.log_page`, `log_undo`) — فهرستِ دسته‌ها + جزئیاتِ قبل/بعد + «بازگردانی»/«بازگردانیِ اجباری».
- **ورود از اکسل (`panel/importer.py`):** فایل در «فایل‌ها»ی پنل (`filebox`) یا لینکش → `import_inspect` روی سرور می‌خواند (ردیف‌های پر،
  شمارهٔ ردیفِ اصلی، سلولِ بلند کوتاه) → خودِ هوش مصنوعی اکسلِ نامرتب را به ردیف‌های تمیز تبدیل می‌کند → `import_tasks` (پیش‌فرض
  dry_run، status=done، تشخیصِ تکراری با لینکِ صفحه/رپورتاژ در همان پروژه یا عنوان+تاریخ، هم با DB هم داخلِ فایل؛ `on_duplicate=update`).
  نوعِ بدونِ نوع → «سایر». ماهِ گزارش خودکار از تاریخ اگر آن ماه در `ReportPeriod` تعریف شده باشد.
- **رپورتاژ:** فیلدهای «رسانه»، «هزینه»، «لینک رپورتاژ» (`is_page_link`) با مهاجرتِ `seo/0002` به نوعِ موجود اضافه شدند؛
  `stats(metric=cost)` از فیلدِ «هزینه» (یا `media_cost`ِ قدیمی) جمع می‌زند.
- **تراکنش‌ها = فقط پیشنهاد** (خواستِ کاربر): `tx_queue` (بی‌تخصیص‌های بدونِ پیشنهادِ در انتظار + بارِ اول ۴۰ نمونهٔ تخصیصِ قبلی)
  → `tx_suggest` یک `finance.TxSuggestion(source=mcp)` می‌سازد؛ تأیید/رد در جدولِ تراکنش‌ها (`finance/CLAUDE.md`).

### تست
اسکریپتِ ساده با `django.test.Client`: `POST /mcp/<token>/panel/` با `tools/call` برای هر ابزار (همهٔ ابزارها + dry_run + undo + رکوردِ
دستی‌تغییرکرده → skip → force). اکسلِ آزمایشی با openpyxl بساز و در `SharedFile` بگذار.

## کانکتورِ سوم: اسکیل‌ها — `/mcp/<token>/skills/`
`views._server(kind)` (site|panel|skills) ابزار/اجراکننده را انتخاب می‌کند؛ ابزارها در `skills/mcp.py` (`skills/CLAUDE.md`).
`views._instructions` متنِ اسکیل‌های **اجباری** را به instructionsِ **هر سه** کانکتور اضافه می‌کند. صفحهٔ `/settings/mcp/` آدرسِ سوم را نشان می‌دهد.
