# skills/ — «اسکیل‌ها» (سایدبار) + کانکتورِ MCPِ جدای `/mcp/<token>/skills/`

دانش و قواعدِ کاری که کارمندها و هوش مصنوعی طبقِ آن کار می‌کنند. **فعلاً بدونِ محدودیتِ نقش در MCP** (خواستِ کاربر).
- **مدل‌ها** (tenant: `objects`/`all_objects`): `Skill(scope must|general|project, project?, title, summary, body, order, active,
  updated_by, deleted_at)` + `SkillVersion` (هر تغییرِ محتوایی در `Skill.save(actor=, source=, note=)` یک نسخه می‌سازد؛
  `source` = web|mcp — اگر داده نشود از `mcpgate.journal.current_batch()` فهمیده می‌شود). حذف = نرم (تا undoِ ژورنال کار کند).
- **«اجباری» (must)** = اطلاعاتِ حیاتی برای **هر دستور**: `text.must_use_text(org)` (سقف ۶۰۰۰ کاراکتر) در `instructions`ِ
  **هر سه** کانکتور (سایت‌ها/پنل/اسکیل‌ها) تزریق می‌شود — `mcpgate/views._instructions`. منبعِ واحدِ «کدام اسکیل‌ها برای
  این پروژه»: `text.for_project(org, project_id)` (اجباری → عمومی → پروژه) — هم MCP هم تبِ «اسکیل‌ها»ی سینگلِ پروژه.
- **MCP** (`mcp.py`، `TOOLS/HANDLERS/run`؛ endpoint در `mcpgate/urls.py` → `views.endpoint_skills`، همان توکنِ `/settings/mcp/`):
  `skills_start(project)` (متنِ کاملِ اجباری + فقط عنوان/خلاصهٔ بقیه — کم‌مصرف)، `skills_list`, `skill_get(ids|title)`,
  `skill_save(items[{id?, scope, project, title, summary, body | append, order, active, note}])`, `skill_delete`,
  `skill_history`, `skill_restore`, `undo`. نوشتن‌ها داخلِ `journal.Batch` → در `/settings/mcp/log/` و قابلِ بازگردانی.
- **وب:** `/skills/` (`views.index`؛ دیدن برای همه، اسکیلِ پروژه فقط برای پروژه‌های `accessible_project_ids`؛ ویرایش با
  پرمیشنِ `manage_skills` — نقشِ «سرپرست» پیش‌فرض دارد، نقش‌های سفارشیِ قدیمی را دستی تیک بزن). API: `skills/api/` (POST ذخیره)،
  `skills/api/<pk>/` (GET نسخه‌ها / DELETE)، `skills/api/<pk>/restore/<vid>/`. UI یک رندرکنندهٔ JS از `json_script`
  (فیلترِ سطح + پروژه + جستجو، مودالِ مشاهده/ویرایش/تاریخچه). CSS: بلوکِ «بخشِ اسکیل‌ها» در `style.css` (`.sk-*`).
- متن ساده/مارک‌داون است (textarea، نه ادیتورِ غنی) تا برای هوش مصنوعی کم‌حجم و تمیز بماند؛ نمایش با `white-space:pre-wrap`.
