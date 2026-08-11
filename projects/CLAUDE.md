# projects/

## مدل‌ها
- **Project** — `name, domain, track_keyword_rank(چک‌باکس، برای بستهٔ seo), color,
  project_types(CSV), status, archived_at, amount, contract_start/end, description,
  client_*, manager(FK Colleague), members(M2M به Colleague), wp_*(فاز۳)`.
  `archive()/restore()` (غیرفعال، نه حذف). `types_list/types_display, is_active`.
  **`members` صرفاً یک تب نیست — گیتِ دسترسیِ واقعی است** (`projects/access.py:
  accessible_project_ids`، جزئیات پایین‌تر).
- **Credential** — پسورد با **Fernet** (`core/crypto.py`): `set_password/reveal_password`.
  هر «نمایش» در `ActivityLog` ثبت می‌شود. **تله‌ی جدی که رفع شد:** `credential_create/
  reveal/delete` قبلاً فقط `is_authenticated` چک می‌کردند — هر عضوِ سازمان (حتی نقشِ
  Viewer) می‌توانست پسوردِ **هر** پروژه‌ای را با حدسِ pk ببیند/حذف کند، بدونِ توجه به
  `manage_projects` یا حتی `accessible_project_ids`. الان هر سه با `require_perm(request,
  'manage_projects')` + `_project_access_ok(request, project_id)` گیت‌اند. تبِ «دسترسی‌ها»
  در تمپلیت هم فقط با `'manage_projects' in org_perms` نشان داده می‌شود (نه فقط سرور —
  وگرنه کاربرِ بدونِ دسترسی می‌بیند چند پسورد ثبت شده، فقط نمی‌تواند بازشان کند).

## دسترسی به پروژه (`access.py`)
`accessible_project_ids(request)` منبعِ واحدِ محدودسازی است — در همه‌جای اپ استفاده می‌شود
(پروژه‌ها/تسک‌ها/تقویم/داشبورد/همکاران، نه فقط اینجا؛ `docs/PLATFORM.md`):
- **مالکِ سازمان** (`Membership.role == 'owner'`) **یا** دارنده‌ی پرمیشنِ سازمانیِ
  `manage_projects` → `None` برمی‌گردد یعنی «بدونِ محدودیت».
  **باگِ جدیِ رفع‌شده:** قبلاً فقط `role == 'owner'` نامحدود بود — نقشِ سفارشی/built-inی
  که `manage_projects` (یا هر ترکیبِ دیگری) داشت هم تا وقتی به‌صراحت به `Project.members`
  هر پروژه اضافه نمی‌شد عملاً هیچ‌چیز نمی‌دید (`ids=[]`، حتی نمی‌توانست تسک بسازد) —
  یعنی «دادنِ دسترسی» از تنظیمات عملاً بی‌اثر بود. چون `manage_projects` یعنی «مدیریتِ
  همه‌ی پروژه‌ها»، الان مثلِ مالک نامحدود است.
- بقیه (بدونِ `manage_projects`، حتی مدیر یک پروژه) → فقط پروژه‌هایی که `Colleague`ِ
  متصل‌به‌کاربرشان (`request.user.colleague`) عضوِ `Project.members` آن‌هاست؛ اگر کاربر
  اصلاً `colleague` وصل ندارد → لیستِ خالی. **مدیرِ پروژه هم باید صریحاً به `members`
  اضافه شود** تا پروژه و تسک‌هایش را ببیند — تعیینِ `manager` به‌تنهایی دسترسی نمی‌دهد.
  در ویو: `ids = accessible_project_ids(request)`؛ `if ids is not None: qs = qs.filter(id__in=ids)`.
  **استثنا:** تسکی که مستقیماً به فردِ بدونِ عضویتِ پروژه دلیگیت شده را همان فرد در
  لیستِ تسک‌های خودش می‌بیند (نه در پروژه)، چون `tasks.queries.build_task_queryset`
  علاوه بر `project_id__in=ids`، `assignee_id=خودش` را هم OR می‌کند (`tasks/CLAUDE.md`).
- تبِ «دسترسی به همکاران» در سینگلِ پروژه (`project_members` API، PATCH) این فهرست را
  می‌سازد؛ نیازمندِ `manage_projects`.

## فایل‌ها / URLها
- `views.py` — List (جدولی، بازه، آخرین‌گزارش، محدودشده با `accessible_project_ids`) ·
  Detail (تب‌ها، `get_object` اگر پروژه در فهرستِ دسترسی نباشد `PermissionDenied`) ·
  CRUD(گیت‌شده با `manage_projects`) · archive/restore · API دسترسی‌ها
  (`credential_create/reveal/delete`) · **فایل‌ها** (`project_files`, `project_file_delete`
  — Attachment روی پروژه، drag&drop) · **`project_members`** (PATCH، تبِ دسترسی).
  **ستون‌های جدولِ لیست سفارشی‌سازی‌شدنی‌اند:** فقط ستونِ «پروژه» ثابت است، بقیه از
  `core.columns.get_columns('projects','page')` می‌آیند (annotate: planned/done/remaining/
  overdue/minutes/words + پایتونی: progress/state) — تنظیم در `/settings/columns/`.
- `forms.py` — نوع/تیم چک‌باکسی، تاریخ‌های `jdate`، توضیحات `rich-editor` + `clean_html`.
- تب‌های سینگل: نمای‌کلی(آمار بازه) · تسک‌ها · **کلمات کلیدی**(فقط اگر `track_keyword_rank`؛
  منطق/مدل در `seo/rank.py` + `seo/models.py`) · تقویم(embed) · فایل‌ها · دسترسی‌ها ·
  **دسترسی به همکاران**(مدیریتِ `members`) · گزارش‌ها · حسابداری(placeholder).

## نکات
- «آخرین پرداخت» در لیست فعلاً `—` است؛ بعد از ساخت `finance` وصل شود.
- **دکمه‌های «ویرایش»/«＋ پروژه‌ی جدید»/«غیرفعال‌سازی» فقط با `'manage_projects' in
  org_perms` نشان داده می‌شوند** (لیست + سینگل) — قبلاً همیشه دیده می‌شدند و کلیک روی‌شان
  ۴۰۳ِ تمام‌صفحه‌ی جنگو می‌داد (نه توستِ داخلِ صفحه، چون این‌ها ناوبریِ واقعی‌اند، نه fetch).
  هر جای دیگر هم که یک لینک/دکمه فقط برای صاحبِ یک پرمیشن معنا دارد، همین الگو را رعایت کن:
  گیت‌کردنِ سرور به‌تنهایی کافی نیست، UI هم باید پنهانش کند.
