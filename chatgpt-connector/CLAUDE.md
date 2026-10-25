# chatgpt-connector/ — برنامهٔ ویندوزیِ «ChatGPT-WP» (خارج از جنگو)

پلاگینِ محلیِ ChatGPT Desktop (حالتِ Work) + **پنلِ محلی که همهٔ مدیریت از آن است**. ChatGPT ↔ این برنامه =
**MCP (stdio)**؛ این برنامه ↔ سایت‌ها = **REST وردپرس** (Application Password). داده:
`%USERPROFILE%\ChatGPT-WP\config.json` (فقط پنل می‌نویسد؛ اکسل حذف شد — ایمپورت هم به خواستِ کاربر نداریم).
فقط برای **همگام‌سازی** به پنلِ جنگو وصل می‌شود (اپِ `connector/`، با توکنِ API). راهنمای کاربر: `README-FA.md`. امنیت به خواستِ صریحِ کاربر
حداقلی است (رمز در config.json به‌صورتِ ساده، `browser_run`/`wp_api` آزاد).

## ساختار
| فایل | کار |
|---|---|
| `INSTALL.cmd` | دوبار کلیک: چکِ Node → `plugin/app/install.mjs` → بازکردنِ پنل (بدونِ PowerShell) |
| `plugin/plugin.json`, `mcp.json` | مانیفستِ پلاگین (الگوی پکیجِ steeltak که روی سیستمِ کاربر کار کرد). **نسخه اینجا** |
| `plugin/server/config.mjs` | **منبعِ واحدِ داده**: load/`updateConfig`/`rawConfig` (reload با mtime)، `newSite`، `getSite`، فایل‌ها (`siteFiles`/`promptDir`/`findLocal`/`roleOf`/`defaultFeatured`)، `siteBrief` |
| `plugin/server/defaults.mjs` | پرامپت‌ها/رقبای نمونهٔ سایتِ جدید + `STEP_KEYS`/`STEP_LABELS` + تنظیماتِ پیش‌فرض |
| `plugin/server/index.mjs` | سرورِ MCP: `tools` + `handlers` + پروتکل. **stdout فقط پروتکل** (لاگ → stderr) |
| `plugin/server/wp.mjs` | `wpFetch` (fallback `?rest_route=`)، کشف، `savePost`/`saveTerm`/`uploadMedia`/`setSeo`، لینکِ داخلی، بک‌آپ |
| `plugin/server/research.mjs` | Playwright با Chrome/Edgeِ ویندوز (پروفایلِ ماندگار)، ساجست، SERP، `extractOutline` |
| `plugin/server/sync.mjs` | همگام‌سازی با پنل (`connector/`): `syncNow` (هرگز throw نمی‌کند؛ قفلِ `.sync.lock` بینِ پنل و MCP)، `merge` (هر سایت با `updated_at`ِ جدیدتر؛ حذف با `deleted`)، فایل‌ها با sha1 نسبت به `base_files`، `startAutoSync` (شروع + هر N دقیقه)، `syncSoon` (بعد از تغییر) |
| `plugin/server/log.mjs` | لاگ در `ChatGPT-WP\logs\app.log` (چرخشی ۱MB؛ هرگز stdout) |
| `plugin/server/text.mjs` | نرمال‌سازیِ فارسی، `relevance`، `looseRegex`، Markdown→HTML، HTML→متن/سرفصل |
| `plugin/server/files.mjs` | `files_list`/`file_read` (docx/xlsx/عکس) + `unzipAll` |
| `plugin/app/panel.mjs` + `panel.html` | پنل روی `127.0.0.1:47800`: سایت‌ها (اتصال/تست)، **پرامپت‌های هر سایت**، **آپلود/جابه‌جاییِ فایل با پوشه‌بندیِ خودکار**، رقبا، تنظیمات، تستِ گوگل، مرورگرِ ابزار، **به‌روزرسانی با آپلودِ zip** (+ ری‌استارتِ خودکار) |
| `plugin/app/install.mjs` | کپی به `~\.codex\plugins\seo-wp-connector` + ادغام در `~\.agents\plugins\marketplace.json` + پوشهٔ کاری + میان‌برِ دسکتاپ |
| `plugin/skills/seo-content/SKILL.md` | روندِ کار برای ChatGPT (بریف → فقط مراحلِ `steps` → نوشتن → draft) |
| `dev/mock_wp.mjs` + `dev/test_mcp.mjs` + `dev/test_sync.mjs` + `dev/build.sh` | وردپرسِ ساختگی، تستِ سرتاسری، تستِ همگام‌سازیِ دو کامپیوتر، ساختِ zip → **`release/ChatGPT-WP.zip` (کامیت می‌شود؛ کاربر از گیت‌هاب برمی‌دارد)** |

## مدلِ داده (`config.json`)
`{settings, settings_updated_at, sites:[{id, key, url, user, password, seo, notes, active, updated_at, prompts[], files[], competitors[]}], deleted:[{id, at}]}`
— `updated_at`/`deleted`/`settings_updated_at` را `config.updateConfig` (`stamp`) خودکار می‌گذارد (پایهٔ ادغام). `replaceConfig` =
نوشتنِ همگام‌سازی (بدونِ stamp و بدونِ خبر به شنونده‌ها، تا حلقه نشود). هر نوشتن قبلش `config.json.bak` می‌سازد و فایلِ خراب از
`.bak` خوانده می‌شود. **`local.json`** = تنظیماتِ همین کامپیوتر (آدرس/توکن/فاصلهٔ همگام‌سازی + وضعیت + `base_files`) — همگام نمی‌شود؛
از تنظیماتِ عمومی هم فقط `hl, gl, maxChars, insecure` همگام می‌شوند (مسیرِ مرورگر/پراکسی/نمایش مالِ هر کامپیوتر است).
- **prompt:** `{id, kind: general|specific, title, use, body, steps:{competitors, competitors_n, serp, suggest, internal_links, images}}`.
  عمومی‌ها همه در بریف؛ اختصاصی با `sites(site, prompt)` + `steps` (**تیک‌نخورده = انجام نده**).
- **files (فقط متادیتا):** `{path (نسبت به ChatGPT-WP), prompt (id یا ''), role, description}`. فایلِ واقعی در
  `files\<key>\` (کلِ سایت) یا `files\<key>\<عنوانِ پرامپت>\`. فایلی که دستی در پوشه گذاشته شود هم دیده می‌شود
  (نقش از نام، توضیح از txtِ هم‌نام). تغییرِ «برای» در پنل = جابه‌جاییِ واقعیِ فایل؛ تغییرِ نامِ سایت/عنوانِ پرامپت = تغییرِ
  نامِ پوشه (`panel.mjs: saveSite`). `default_featured` = تصویرِ شاخصِ خودکارِ نوشتهٔ جدید (+ کشِ آپلود `.media-cache.json`).
- **competitors:** `{domain, kind: competitor|ignore, notes}`.

## قواعد
- محتوای ورودی Markdown یا HTML؛ H1ِ اولِ متن حذف و بقیهٔ H1ها H2 (عنوان خودش H1 است).
- هر ویرایشِ چیزِ موجود (نوشته/دسته/`wp_add_link`) اول JSONِ قبلی را در `ChatGPT-WP\backups\<سایت>\` می‌نویسد.
- سئو: `rankmath/v1/updateMeta`، بعد `meta`ِ REST؛ اگر نشد `ok:false` + مقادیر برای ورودِ دستی.
- **زمانِ ابزار:** ChatGPT احتمالاً سقفِ ~۶۰ ثانیه دارد → `competitor_research` بودجهٔ ~۵۲s دارد؛ ابزارِ کند نساز.
- پنل: POST فقط از همان مبدأ (چکِ `Origin`)؛ `/api/thumb` فقط داخلِ پوشهٔ ChatGPT-WP.
- نسخه را در `plugin/plugin.json` بالا ببر (پنل «نسخهٔ جدیدتر» را از روی همین تشخیص می‌دهد) → `dev/build.sh` → `release/ChatGPT-WP.zip` را هم کامیت کن.
- **فایروال/افزونهٔ امنیتی (تجربهٔ واقعی: 403ِ HTMLِ LiteSpeed):** پاسخِ غیرِJSON یعنی وردپرس جواب نداده. `wpFetch` یک بار
  با `?rest_route=` امتحان می‌کند (بعضی‌ها فقط مسیرِ `/wp-json/` را می‌بندند) و پیامِ «فایروال، نه وردپرس» می‌دهد؛ `wpCheck` اگر
  `users/me` بسته بود (ضدِ user enumeration) با `posts?context=edit` اتصال را تأیید می‌کند. تست: `MOCK_BLOCK=users|wpjson node dev/mock_wp.mjs`.
- **رمزِ برنامه ساخته می‌شود ولی کد نشان داده نمی‌شود / بعد از «تأیید» برنمی‌گردد** (افزونهٔ امنیتی `/wp-json/` را بسته و
  JSِ پیشخوانِ وردپرس از همان مسیر رمز را می‌سازد): «🔑 اتصالِ خودکار» در تبِ اتصال = `panel.mjs: connectWp` — صفحهٔ
  `wp-admin/authorize-application.php` را در مرورگرِ برنامه باز می‌کند، با `page.route` هر `/wp-json/…`ِ همان دامنه را به
  `?rest_route=` می‌فرستد، رمز را از پاسخِ `application-passwords` (یا `#new-application-password-value`) و نامِ کاربری را از
  `window.authApp.user_login` برمی‌دارد، ذخیره و `wpCheck` می‌کند. تست: `MOCK_BLOCK=wpjson MOCK_AUTOAPPROVE=1` + `CWP_FORCE_HEADLESS=1`.
- `getSite`: کیبوردِ اشتباه (فا↔en)، دامنه/بخشی از نام، پیامِ «غیرفعال است»، «منظورت … بود؟»؛ `SiteNotFound` در `index.mjs` یک
  همگام‌سازی و تلاشِ دوباره می‌گیرد (سایتِ اضافه‌شده روی کامپیوترِ دیگر).
- همگام‌سازی **هرگز** نباید ابزار یا پنل را متوقف کند: خطا فقط در `sync_status` (چیپِ بالای پنل) و لاگ.

## تست
```bash
cd chatgpt-connector/plugin && npm install                 # یک بار
node ../dev/mock_wp.mjs 8766 &                             # وردپرسِ ساختگی (+ صفحهٔ رقیب در /competitor)
# config.json با سایتِ test → http://127.0.0.1:8766، admin / "abcd efgh ijkl"
CWP_HOME=<tmp> CWP_BROWSER_PATH=/opt/pw-browsers/chromium-1194/chrome-linux/chrome node ../dev/test_mcp.mjs [wp|browser]
CWP_HOME=<tmp> CWP_NO_OPEN=1 node app/panel.mjs            # پنل → با Playwright واقعاً باز کن و ببین
```
همگام‌سازی: `runserver` + توکن (`APIToken.generate`) → `CWP_HOME=<A> node ../dev/test_sync.mjs setup <url> <token>` و همین برای B،
بعد `add-site / add-file / edit-prompt / del-file / del-site / sync / dump` روی A و B.
گوگل/بینگ از سندباکس در دسترس نیست — SERP/ساجست را فقط روی ویندوزِ کاربر می‌شود واقعاً تست کرد.
⚠ `pkill -f <الگو>` در همان فرمانی که الگو را دارد شلِ خودش را می‌کشد (exit 144) — از `pkill -f "[m]ock_wp"` استفاده کن و فرمانِ
  شروعِ سرور را در همان خط نیاور. پروسه‌های پس‌زمینهٔ یک تستِ timeoutشده یتیم می‌مانند و پورت را نگه می‌دارند (پنلِ جدید «از قبل باز است» و exit 0).
