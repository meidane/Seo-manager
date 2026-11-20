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
- `must_use_text(org)` = متنِ کاملِ اجباری + نامِ عمومی‌های «همیشه» → در instructionsِ **هر سه** کانکتور (`mcpgate/views._instructions`،
  که اگر اسکیلی هست یادآوریِ «قبل از تولیدِ محتوا skills_start» را هم به کانکتورهای سایت/پنل اضافه می‌کند).
- همین `select` در تبِ «اسکیل‌ها»ی سینگلِ پروژه و «آزمایشِ تشخیص»ِ صفحه (`api_detect`) استفاده می‌شود — دقیقاً همان چیزی که AI می‌گیرد.

## MCP (`mcp.py`، ایندکس بالای فایل)
`skills_start(text, site, project, task, type)` · `skills_list` · `skill_get` (+ فایل‌ها) · `skill_save` (apply/category/tags/
task_types/append) · `skill_delete` · `skill_history` · `skill_restore` · `skill_file_get` (متن کامل؛ عکس = محتوای `image`ِ MCP با
`{'_mcp': ...}`؛ بقیه لینک) · `skill_file_save` (text|base64|url) · `skill_file_delete` · `undo`. نوشتن‌ها داخلِ `journal.Batch`.

## وب
`/skills/` (`views.index`) — مدیرِ دوستونه (فهرست با جستجو/سطح/پروژه و گروه‌بندیِ دسته + پنلِ جزئیات: مارک‌داونِ ساده، ویرایشِ درجا
با پیش‌نمایش و Ctrl+S، فایل‌ها با کشیدن‌ورهاکردن، تاریخچه/بازگردانی، کپی به پروژهٔ دیگر). `?s=<id>` اسکیلِ باز، `?project=` فیلتر.
«اسکیل‌های آماده» (`starters.py: STARTERS`: قواعدِ حیاتی، Humanize، نگارشِ فارسی، ساختارِ مقاله، رپورتاژ) + «پروفایلِ پروژه»
(`PROJECT_PROFILE`، دکمهٔ کنارِ نامِ پروژه). دیدن برای همه (پروژه‌ای فقط پروژه‌های `accessible_project_ids`)؛ ویرایش `manage_skills`.
API: `api/` ذخیره · `api/<pk>/` نسخه‌ها/حذف · `api/<pk>/restore/<vid>/` · `api/<pk>/duplicate/` · `api/<pk>/files/` آپلود ·
`api/files/<fid>/` PATCH توضیح/DELETE · `api/detect/` · `api/starters/`. CSS: بلوکِ «بخشِ اسکیل‌ها» در `style.css` (`.skm-*`, `.skf-*`).
- متنِ اسکیل با `md()`ِ همان تمپلیت رندر می‌شود: تیتر، فهرست، **جدول** (`| … |` + خطِ `|---|`)، نقل‌قول (`>`)، `---`، کد. اول escape.
- `skills_start` اگر لینکِ صفحه یا تسک در درخواست باشد، دادهٔ سرچ کنسولِ همان صفحه را هم در `search_console` می‌دهد (`gsc/CLAUDE.md`).
- **تله:** رویدادِ `input`ِ اینپوتِ فایل هم bubble می‌کند — dirtyِ فرم آن را نادیده می‌گیرد، وگرنه آپلود «تغییرِ ذخیره‌نشده» حساب می‌شد.
