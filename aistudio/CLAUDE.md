# aistudio/ — تبِ «AI»ی پروژه (پایهٔ اتصال به ChatGPT/MCP)

> نقشهٔ کلِ کار (پلِ محلیِ واحد، اتصال به تسک‌ها، فازها): **`docs/AI_PLAN.md`** — قبل از هر
> تغییر در این اپ بخوان. این اپ «فاز ۱» است: ذخیره‌گاهِ تنظیمات/پرامپت‌ها.

## مدل‌ها (`models.py`)
- **`ProjectAI`** (یک‌به‌یک با `Project`، `related_name='ai_config'`): `site_url`, `wp_username`,
  `wp_password_enc` (WordPress **Application Password**)، `mcp_endpoint`, `mcp_token_enc`,
  `general_prompt`, `updated_at/by`. رمزها با Fernet (`core/crypto.py`):
  `set_secret(name, raw)` / `get_secret(name)` / `has_secret(name)` روی `ProjectAI.SECRETS`
  (`wp_password`, `mcp_token`) — منبعِ واحد؛ مستقیم به `*_enc` دست نزن.
- **`AIPrompt`** (FK پروژه، `related_name='ai_prompts'`): `title`, `body`, `order`,
  **`task_type`** (FK اختیاری به `tasks.TaskTypeDef`) — تسک‌های همان نوع در همان پروژه این
  پرامپت را خودکار می‌گیرند (فاز ۲). فایل‌ها = **`core.Attachment`** از طریقِ
  `files = GenericRelation` (حذفِ پرامپت ← حذفِ پیوست‌ها؛ `django-cleanup` فایلِ دیسک را پاک می‌کند).
- **`FILE_ROLES`** (منبعِ واحدِ گزینه‌های «کاربردِ فایل»): `featured` تصویرِ شاخص · `inline` داخلِ
  متن · `reference` نمونه/مرجع · `other`. روی `Attachment.role` + `Attachment.description` (توضیح:
  «با این فایل چه کند») ذخیره می‌شود — این دو فیلدِ عمومی به `core.Attachment` اضافه شدند
  (فایلِ موازی نساختیم).
- اسکوپِ سازمان مثلِ `Credential` از طریقِ پروژه است (فیلدِ `organization` ندارند) — پس هر
  دسترسی **باید** از `_gate` بگذرد.

## امنیت (قواعدِ سخت)
- **رمزها write-only‌اند:** GET فقط `has_wp_password`/`has_mcp_token` می‌دهد؛ مقدار هرگز به
  قالب/JSON/مرورگر نمی‌رود. PATCH: مقدارِ ناخالی = ست، `clear: [...]` = پاک. هر تغییرِ رمز یک
  `ActivityLog` (`verb='ai_secret_change'`، بدونِ مقدار) می‌سازد. `get_secret` فقط سمتِ سرور.
- **گیت:** پرمیشنِ `project_ai` (گروهِ «پروژه‌ها» در `accounts/permissions.py`، نقشِ «سرپرست» دارد)
  + `accessible_project_ids` — در `views._gate`. UI هم تب/پنل/اسکریپت را با `'project_ai' in
  org_perms` پنهان می‌کند. ⚠️ نقش‌های سفارشیِ قدیمی این کلید را ندارند (تلهٔ `seed_roles`) —
  از `/settings/roles/` تیک بزن.
- **`prompt_file_detail` فقط پیوست‌هایی که `content_type == AIPrompt` دارند** را می‌پذیرد
  (`get_object_or_404(Attachment, pk, content_type=ct)`)، وگرنه این اندپوینت دریچهٔ ویرایش/حذفِ
  هر فایلِ پروژه/تسک می‌شد. تست شد: فایلِ پروژه → ۴۰۴.
- **تستِ اتصال** (`project_ai_test`): `GET {site}/wp-json/wp/v2/users/me` **از سرورِ پنل** با
  `allow_redirects=False`، timeout ۱۲s، فقط http/https. شکستِ شبکه = «سرورِ پنل به سایت دسترسی
  ندارد → اجرا باید از پلِ محلی باشد» (هاست‌های ایران معمولاً از بیرون در دسترس نیستند).

## API (`/ai/api/...`، JSON، `@login_required`)
| مسیر | متد | کار |
|---|---|---|
| `project/<pk>/` | GET / PATCH | کلِ وضعیتِ تب (config + prompts + `task_types` + `roles` + `default_site_url`) / ذخیرهٔ اتصال و پرامپتِ عمومی |
| `project/<pk>/test/` | POST | تستِ REST وردپرس (همیشه ۲۰۰ با `{ok, message}`) |
| `project/<pk>/prompts/` | POST | ساختِ پرامپتِ خالی (مثلِ «＋ ردیف»؛ تا فایل بلافاصله قابلِ پیوست باشد) |
| `prompts/<id>/` | PATCH / DELETE | عنوان/متن/نوعِ تسک / حذف |
| `prompts/<id>/files/` | POST (multipart `file`) | آپلودِ چند فایل (سقف ۲۰MB؛ ردشده‌ها در `skipped`) |
| `files/<id>/` | PATCH / DELETE | `description`/`role` / حذف |

## UI
`templates/aistudio/_project_tab.html` فقط **پوسته** است (data-api/test/prompt-create)؛ همه‌چیز را
`static/js/aistudio.js` از GET می‌سازد (منبعِ واحدِ رندر) — **لودِ تنبل** با اولین کلیک روی تب
(یا `#ai` در آدرس؛ `projects/detail.html` آن را فعال می‌کند). هندلرها delegated روی `#ai-tab`.
- کارتِ اتصال (ذخیره + «تستِ اتصال» که اول ذخیره می‌کند) · پرامپتِ عمومی (شمارندهٔ نویسه) ·
  پرامپت‌های اختصاصی (نشانگرِ «تغییرِ ذخیره‌نشده»، ذخیرهٔ دستی؛ توضیح/کاربردِ فایل با `change`
  خودکار ذخیره) · رها کردنِ فایل روی کارت.
- **«📋 کپیِ پرامپتِ کامل»** = پروژه/سایت + پرامپتِ عمومی + پرامپتِ اختصاصی + فهرستِ فایل‌ها با
  کاربرد/توضیح — مسیرِ «فقط چت» (بدونِ MCP) همین حالا کار می‌کند.
- CSS: بلوکِ «تبِ AI» تهِ `style.css` (فقط متغیرها؛ `width:auto`ِ خاص‌تر برای ردیف‌های فلکس — تلهٔ ۲۹).
