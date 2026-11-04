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
