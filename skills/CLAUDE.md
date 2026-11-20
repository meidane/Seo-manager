# skills/ — «اسکیل‌ها» (سایدبار) + کانکتورِ MCPِ جدای `/mcp/<token>/skills/`

مدیرِ اسکیل برای تولیدِ محتوا: هوش مصنوعی از روی خودِ درخواست پروژه/نوع را تشخیص می‌دهد و اسکیل‌های لازم را کامل می‌گیرد.
**فعلاً بدونِ محدودیتِ نقش در MCP** (خواستِ کاربر).

## مدل‌ها (tenant: `objects`/`all_objects`)
- `Skill(scope must|general|project, project?, title, summary, body, apply always|auto|manual, category, tags (CSV), task_types M2M,
  order, active, updated_by, deleted_at)` — حذف نرم (undoِ ژورنال). `tag_list` = کلیدواژه‌ها.
- `SkillVersion` — هر تغییرِ محتوایی در `Skill.save(actor=, source=, note=)` یک نسخه؛ `source` web|mcp (پیش‌فرض از `current_batch()`).
- `SkillFile(skill, name, file, size, note, token, deleted_at)` — ضمیمه (کد/عکسِ نمونه/قالب). `kind` image|text|file. لینکِ توکنیِ
  بدونِ ورود `/skills/f/<token>/<نام>` (`views.public_file`؛ فایلِ متنی/کد همیشه `text/plain` سرو می‌شود تا اجرا نشود).
  هم‌نام در همان اسکیل → جایگزینیِ محتوا (لینک ثابت). منبعِ واحدِ ذخیره: `mcp.save_file_bytes` (وب و MCP).

## تشخیص — منبعِ واحد `text.py`
- `detect(org, project, site, task, type, text)` → پروژه از: id/نام/دامنه، کلیدِ سایتِ MCP (`MCPSite.url` → دامنهٔ پروژه)، آدرس/دامنه
  در متن، `#123` (تسک → پروژه+نوع+عنوان)، نامِ پروژه در متن؛ نوع از نامش در متن. `how` = سرنخ‌ها.
- `select(org, project_id, type_id, text)` → `(load, available)` با «چرا»: load = اجباری + `always` (عمومی؛ اگر `task_types` دارد فقط
  همان نوع) + `always`ِ همین پروژه + `auto`هایی که نوع یا کلیدواژه‌شان جور است + `auto`ِ پروژه‌ایِ بی‌شرط؛ بقیه available (فقط عنوان).
- **بدونِ رفرشِ کانکتور (قاعده):** `instructions` و فهرستِ ابزارهای MCP را ChatGPT فقط موقعِ وصل‌شدن می‌خواند و تا رفرش نگه می‌دارد؛
  جوابِ ابزارها هر بار تازه است. پس **هیچ دادهٔ متغیری در instructions نگذار** — دستورالعمل‌ها ثابت‌اند (`skills/mcp.py:
  BASE_INSTRUCTIONS`، `mcpgate/views.py: RULES_LINE`) و متنِ اسکیل‌های اجباری فقط از جوابِ `skills_start` (کانکتورِ اسکیل‌ها) و ابزارِ
  `rules` (کانکتورهای سایت/پنل، `views.rules_payload`) می‌آید. رفرش فقط وقتی لازم است که خودِ ابزارها اضافه/عوض شوند.
  (`text.must_use_text` دیگر در instructions استفاده نمی‌شود — تلهٔ قبلی: هر ویرایشِ اسکیلِ اجباری رفرشِ دستیِ کانکتور می‌خواست.)
- همین `select` در تبِ «اسکیل‌ها»ی سینگلِ پروژه استفاده می‌شود — دقیقاً همان چیزی که AI می‌گیرد. (`api_detect` هنوز هست ولی دکمهٔ «آزمایشِ تشخیص» به خواستِ کاربر از صفحه حذف شد.)

## MCP (`mcp.py`، ایندکس بالای فایل)
`skills_start(text, site, project, task, type)` · `skills_list` · `skill_get` (+ فایل‌ها) · `skill_save` (apply/category/tags/
task_types/append) · `skill_delete` · `skill_history` · `skill_restore` · `skill_file_get` (متن کامل؛ عکس = محتوای `image`ِ MCP با
`{'_mcp': ...}`؛ بقیه لینک) · `skill_file_save` (text|base64|url) · `skill_file_delete` · `undo`. نوشتن‌ها داخلِ `journal.Batch`.

## وب
`/skills/` (`views.index`) — مدیرِ دوستونه (فهرستِ خلوت: جستجو + سگمنتِ سطح (همه/اجباری/عمومی/پروژه) + چیپ‌های **دسته = نوعِ کار**
(از `category`ِ موجود، با شمارش، فقط اگر ≥۲ دسته) + پروژه؛ هر ردیف فقط عنوان + نقطهٔ سبز=«همیشه»/توخالی=«دستی» + تعدادِ فایل. هدرِ صفحه
فقط «＋ اسکیلِ جدید» (دکمه‌های آزمایشِ تشخیص/اسکیل‌های آماده/اتصالِ MCP به خواستِ کاربر حذف شدند) + پنلِ جزئیات: مارک‌داونِ ساده، ویرایشِ درجا
با پیش‌نمایش و Ctrl+S، فایل‌ها با کشیدن‌ورهاکردن، تاریخچه/بازگردانی، کپی به پروژهٔ دیگر). `?s=<id>` اسکیلِ باز، `?project=` فیلتر.
`starters.py: STARTERS` دیگر دکمه‌ای در صفحه ندارد؛ فقط «پروفایلِ پروژه» (`PROJECT_PROFILE`، دکمهٔ کنارِ نامِ پروژه) از `api/starters/` استفاده می‌شود. دیدن برای همه (پروژه‌ای فقط پروژه‌های `accessible_project_ids`)؛ ویرایش `manage_skills`.
API: `api/` ذخیره · `api/<pk>/` نسخه‌ها/حذف · `api/<pk>/restore/<vid>/` · `api/<pk>/duplicate/` · `api/<pk>/files/` آپلود ·
`api/files/<fid>/` PATCH توضیح/DELETE · `api/detect/` · `api/starters/`. CSS: بلوکِ «بخشِ اسکیل‌ها» در `style.css` (`.skm-*`, `.skf-*`).
- متنِ اسکیل با `md()`ِ همان تمپلیت رندر می‌شود: تیتر، فهرست، **جدول** (`| … |` + خطِ `|---|`)، نقل‌قول (`>`)، `---`، کد. اول escape.
- `skills_start` اگر لینکِ صفحه یا تسک در درخواست باشد، دادهٔ سرچ کنسولِ همان صفحه را هم در `search_console` می‌دهد (`gsc/CLAUDE.md`).
- **تله:** رویدادِ `input`ِ اینپوتِ فایل هم bubble می‌کند — dirtyِ فرم آن را نادیده می‌گیرد، وگرنه آپلود «تغییرِ ذخیره‌نشده» حساب می‌شد.

## بازخورد برای بهبودِ اسکیل‌ها (`feedback.py`، منبعِ واحد)
- `SkillFeedback(kind conflict|missing|rework|guess|quality|other, skill?, project?, summary, suggestion, request, source mcp|web,
  status open|resolved|dismissed, resolved_by/at)` — اشتباه/کمبودی که درخواستِ نویسنده کیفیت را پایین آورد. **نویسنده عمداً ثبت
  نمی‌شود** (حسابِ ChatGPTِ مشترک؛ بعداً با کانکتورِ جدا برای هر نفر).
- ابزارِ MCPِ `skill_feedback(items)` (کانکتورِ اسکیل‌ها) — skill با id یا عنوان، kind فارسی هم قبول.
- اسکیلِ پیش‌فرضِ «ثبتِ بازخورد برای بهبودِ اسکیل‌ها» (`ensure_skill`؛ عمومی·همیشه، دستهٔ «بازخورد»، `Skill.key='feedback'` تا با
  تغییرِ عنوان دوباره ساخته نشود؛ حذف‌شده هم برنمی‌گردد) — موقعِ بازکردنِ `/skills/` یا `skills_start` ساخته می‌شود؛ متنش را کاربر کامل می‌کند.
- صفحهٔ `/skills/feedback/` (`views.feedback`؛ دکمهٔ «بازخوردها» با شمارِ باز در هدرِ `/skills/`): هشدارِ تکرار (`alarms`: یک
  نوع×اسکیل ≥۳ بارِ باز در ۷ روز) + شمارِ بازها به تفکیکِ نوع/اسکیل (کلیک = فیلتر) + فهرست. عمل‌ها (`api/feedback/<id>/`، `manage_skills`):
  «افزودن به اسکیل» (`append_to_skill`: پیشنهاد به تهِ متن + نسخهٔ تازه + حل‌شده)، حل شد، نادیده، بازکردن، حذف. CSS: `.fb-*`.
