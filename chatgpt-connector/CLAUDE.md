# chatgpt-connector/ — برنامهٔ ویندوزیِ «ChatGPT-WP» (خارج از جنگو)

پلاگینِ محلیِ ChatGPT Desktop (حالتِ Work) + **پنلِ محلی که همهٔ مدیریت از آن است**. ChatGPT ↔ این برنامه =
**MCP (stdio)**؛ این برنامه ↔ سایت‌ها = **REST وردپرس** (Application Password). داده:
`%USERPROFILE%\ChatGPT-WP\config.json` (فقط پنل می‌نویسد؛ اکسل حذف شد — ایمپورت هم به خواستِ کاربر نداریم).
**به پنلِ جنگو وصل نیست** (`aistudio/` جداست). راهنمای کاربر: `README-FA.md`. امنیت به خواستِ صریحِ کاربر
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
| `plugin/server/text.mjs` | نرمال‌سازیِ فارسی، `relevance`، `looseRegex`، Markdown→HTML، HTML→متن/سرفصل |
| `plugin/server/files.mjs` | `files_list`/`file_read` (docx/xlsx/عکس) + `unzipAll` |
| `plugin/app/panel.mjs` + `panel.html` | پنل روی `127.0.0.1:47800`: سایت‌ها (اتصال/تست)، **پرامپت‌های هر سایت**، **آپلود/جابه‌جاییِ فایل با پوشه‌بندیِ خودکار**، رقبا، تنظیمات، تستِ گوگل، مرورگرِ ابزار، **به‌روزرسانی با آپلودِ zip** (+ ری‌استارتِ خودکار) |
| `plugin/app/install.mjs` | کپی به `~\.codex\plugins\seo-wp-connector` + ادغام در `~\.agents\plugins\marketplace.json` + پوشهٔ کاری + میان‌برِ دسکتاپ |
| `plugin/skills/seo-content/SKILL.md` | روندِ کار برای ChatGPT (بریف → فقط مراحلِ `steps` → نوشتن → draft) |
| `dev/mock_wp.mjs` + `dev/test_mcp.mjs` + `dev/build.sh` | وردپرسِ ساختگی، تستِ سرتاسری، ساختِ `dist/ChatGPT-WP-<ver>.zip` |

## مدلِ داده (`config.json`)
`{settings, sites:[{id, key, url, user, password, seo, notes, active, prompts[], files[], competitors[]}]}`
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
- نسخه را در `plugin/plugin.json` بالا ببر (پنل «نسخهٔ جدیدتر» را از روی همین تشخیص می‌دهد) → `dev/build.sh`.

## تست
```bash
cd chatgpt-connector/plugin && npm install                 # یک بار
node ../dev/mock_wp.mjs 8766 &                             # وردپرسِ ساختگی (+ صفحهٔ رقیب در /competitor)
# config.json با سایتِ test → http://127.0.0.1:8766، admin / "abcd efgh ijkl"
CWP_HOME=<tmp> CWP_BROWSER_PATH=/opt/pw-browsers/chromium-1194/chrome-linux/chrome node ../dev/test_mcp.mjs [wp|browser]
CWP_HOME=<tmp> CWP_NO_OPEN=1 node app/panel.mjs            # پنل → با Playwright واقعاً باز کن و ببین
```
گوگل/بینگ از سندباکس در دسترس نیست — SERP/ساجست را فقط روی ویندوزِ کاربر می‌شود واقعاً تست کرد.
⚠ `pkill -f <الگو>` در همان فرمانی که الگو را دارد شلِ خودش را می‌کشد (exit 144) — از `pkill -f "[m]ock_wp"` استفاده کن.
