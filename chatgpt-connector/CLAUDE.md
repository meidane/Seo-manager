# chatgpt-connector/ — برنامهٔ ویندوزیِ «ChatGPT-WP» (خارج از جنگو)

پلاگینِ محلیِ ChatGPT Desktop (حالتِ Work) + پنلِ کوچکِ محلی. ChatGPT ↔ این برنامه = **MCP (stdio)**؛
این برنامه ↔ سایت‌ها = **REST وردپرس** (Application Password). تنظیمات فقط از **اکسلِ کاربر**
(`%USERPROFILE%\ChatGPT-WP\sites.xlsx`). **به پنلِ جنگو وصل نیست** (به خواستِ کاربر؛ `aistudio/` جداست).
راهنمای کاربر: `README-FA.md`. امنیت به خواستِ صریحِ کاربر حداقلی است (رمز در اکسل، `browser_run`/`wp_api` آزاد).

## ساختار
| فایل | کار |
|---|---|
| `INSTALL.cmd` | دوبار کلیک: چکِ Node → `plugin/app/install.mjs` → بازکردنِ پنل (بدونِ PowerShell) |
| `plugin/plugin.json`, `mcp.json` | مانیفستِ پلاگین (الگوی پکیجِ steeltak که روی سیستمِ کاربر کار کرد) |
| `plugin/server/index.mjs` | سرورِ MCP: فهرستِ ابزارها (`tools`) + `handlers` + پروتکل. **stdout فقط پروتکل** (لاگ → stderr) |
| `plugin/server/config.mjs` | خواندنِ اکسل (تطبیقِ سرتیترها با `pick`/مستعار؛ reload با mtime) + فایل‌های پوشه‌ای + `siteBrief` + `defaultFeatured` |
| `plugin/server/wp.mjs` | `wpFetch` (fallback به `?rest_route=`)، کشف (types/taxonomies/namespaces)، `savePost`/`saveTerm`/`uploadMedia`/`setSeo`، لینکِ داخلی، بک‌آپ |
| `plugin/server/research.mjs` | Playwright با Chrome/Edgeِ ویندوز (پروفایلِ ماندگار `ChatGPT-WP\.browser-profile`)، ساجست، SERP، `extractOutline` |
| `plugin/server/text.mjs` | نرمال‌سازیِ فارسی، `relevance`، `looseRegex`، Markdown→HTML، HTML→متن/سرفصل (منبعِ واحد) |
| `plugin/server/files.mjs` | فهرستِ پوشه‌ها، خواندنِ docx/xlsx/عکس، `unzipAll` (docx + بستهٔ به‌روزرسانی) |
| `plugin/app/install.mjs` | کپی به `~\.codex\plugins\seo-wp-connector` + ادغام در `~\.agents\plugins\marketplace.json` + اکسلِ قالب (اگر نبود) + میان‌برِ دسکتاپ |
| `plugin/app/panel.mjs/.html` | پنل روی `127.0.0.1:47800`: وضعیت، تستِ اتصال، بازکردنِ اکسل/پوشه‌ها، تستِ گوگل، مرورگرِ ابزار، **به‌روزرسانی با آپلودِ zip** (+ ری‌استارتِ خودکار) |
| `plugin/skills/seo-content/SKILL.md` | روندِ کار برای ChatGPT (بریف → فقط مراحلِ `steps` → نوشتن → draft) |
| `dev/make_template.py` | ساختِ `plugin/template/sites.xlsx` (openpyxl). ستون‌ها را با `config.mjs` هماهنگ نگه دار |
| `dev/mock_wp.mjs` + `dev/test_mcp.mjs` | وردپرسِ ساختگی + تستِ سرتاسریِ ابزارها |
| `dev/build.sh` | `dist/ChatGPT-WP-<ver>.zip` (با `node_modules`؛ `dist/` و `node_modules/` گیت‌ایگنور) |

## قواعد
- **پرامپت‌ها:** «نوع پرامپت» عمومی (همه همیشه در بریف) / اختصاصی (با `sites(site, prompt)`؛ ستون‌های بله/خیرِ
  بررسی رقبا/نتایج گوگل/ساجست/لینک داخلی/عکس → `steps`؛ **خالی = انجام نده**).
- **فایل‌ها:** اکسل + پوشهٔ `files\<سایت>\[<عنوان پرامپت>\]` (+ `files\همه\`)؛ نقش از نامِ فایل (`roleOf`)،
  توضیح از txtِ هم‌نام. `پیشفرض.*` = تصویرِ شاخصِ پیش‌فرضِ نوشته‌های جدید (`savePost`)؛ کشِ ماندگارِ آپلود
  `ChatGPT-WP\.media-cache.json` تا هر بار دوباره آپلود نشود.
- محتوای ورودی Markdown یا HTML؛ H1ِ اولِ متن حذف و بقیهٔ H1ها H2 می‌شوند (عنوان خودش H1 است).
- هر ویرایشِ چیزِ موجود (نوشته/دسته/`wp_add_link`) اول JSONِ قبلی را در `ChatGPT-WP\backups\<سایت>\` می‌نویسد.
- سئو: Rank Math با `rankmath/v1/updateMeta`، بعد `meta`ِ REST؛ اگر نشد `ok:false` + مقادیر برای ورودِ دستی.
- **زمانِ ابزار:** ChatGPT احتمالاً سقفِ ~۶۰ ثانیه دارد → `competitor_research` بودجهٔ داخلیِ ~۵۲s دارد؛ ابزارِ کند نساز.
- نسخه را در `plugin/plugin.json` بالا ببر (پنل «نسخهٔ جدیدتر» را از روی همین تشخیص می‌دهد) → `dev/build.sh`.

## تست
```bash
cd chatgpt-connector/plugin && npm install          # یک بار
node ../dev/mock_wp.mjs 8765 &                       # وردپرسِ ساختگی (+ صفحهٔ رقیب در /competitor)
CWP_HOME=<tmp با sites.xlsx که سایتِ test → http://127.0.0.1:8765، admin / "abcd efgh ijkl"> \
CWP_BROWSER_PATH=/opt/pw-browsers/chromium-1194/chrome-linux/chrome node ../dev/test_mcp.mjs [wp|browser]
```
گوگل/بینگ از سندباکس در دسترس نیست — SERP/ساجست را فقط روی ویندوزِ کاربر می‌شود واقعاً تست کرد.
