# projects/

## مدل‌ها
- **Project** — `name, domain, track_keyword_rank(چک‌باکس، برای بستهٔ seo), color,
  project_types(CSV), status, archived_at, priority, amount, contract_start/end, description,
  client_*, manager(FK Colleague), members(M2M به Colleague), wp_*(فاز۳)`.
  **`priority`** (`PositiveSmallInt`، اختیاری، ۱=بالاترین، خالی=ته): در فرمِ پروژه ست
  می‌شود؛ **مرتب‌سازیِ صفحهٔ پروژه‌ها و داشبورد** از آن می‌خوانند — لیست با
  `F('priority').asc(nulls_last=True)` (بعد از `_personal`/`status`)، داشبورد با
  `key=(priority or 9999, state_order, -overdue)`. بی‌اولویت‌ها همیشه ته.
  `archive()/restore()` (غیرفعال، نه حذف). `types_list/types_display, is_active`.
  **`members` صرفاً یک تب نیست — گیتِ دسترسیِ واقعی است** (`projects/access.py:
  accessible_project_ids`، جزئیات پایین‌تر).
- **Credential** — پسورد با **Fernet** (`core/crypto.py`): `set_password/reveal_password`.
  هر «نمایش» در `ActivityLog` ثبت می‌شود. **تله‌ی جدی که رفع شد:** `credential_create/
  reveal/delete` قبلاً فقط `is_authenticated` چک می‌کردند — هر عضوِ سازمان (حتی نقشِ
  Viewer) می‌توانست پسوردِ **هر** پروژه‌ای را با حدسِ pk ببیند/حذف کند. الان هر سه با
  `require_perm(request, 'project_credentials')` + `_project_access_ok(request,
  project_id)` گیت‌اند. تبِ «دسترسی‌ها» در تمپلیت هم فقط با `'project_credentials' in
  org_perms` نشان داده می‌شود (نه فقط سرور — وگرنه کاربرِ بدونِ دسترسی می‌بیند چند
  پسورد ثبت شده، فقط نمی‌تواند بازشان کند).

## پرمیشن‌های granularِ پروژه (`accounts/permissions.py`، گروهِ «پروژه‌ها»)
`manage_projects` (تکی، همه‌کاره) جایش را به هفت پرمیشنِ جدا داد — هرکدام فقط یک
تب/عملیاتِ خاص را گیت می‌کند، تا مثلاً کسی بتواند فقط فایل‌ها را ببیند بدونِ اینکه
پروژه بسازد/ویرایش کند:
| پرمیشن | چی را گیت می‌کند |
|---|---|
| `view_all_projects` | دیدنِ **همه‌ی** پروژه‌ها بدونِ نیازِ عضویتِ تک‌تک (مثلِ مالک) — `access.py` پایین |
| `add_project` | `ProjectCreateView` («＋ پروژه‌ی جدید») |
| `edit_project` | `ProjectUpdateView` + archive/restore + بنر/دکمه‌ی ویرایشِ سینگل |
| `project_files` | تبِ «فایل‌ها» (`project_files`, `project_file_delete`) |
| `project_colleagues_access` | تبِ «دسترسی به همکاران» (`project_members`، مدیریتِ `Project.members`) |
| `project_credentials` | تبِ «دسترسی‌ها» (`credential_create/reveal/delete`) |
| `project_reports` | تبِ «گزارش‌ها»ی سینگلِ پروژه |
| `manage_finance` | تبِ «حسابداری» (پرمیشنِ گروهِ پروژه‌ها، ولی خودِ اپِ `finance` جداست) |
نقشِ built-in «سرپرست» (manager) همه‌ی این هفت‌تا را دارد؛ «عضو»/«ناظر» هیچ‌کدام را ندارند.

## دسترسی به پروژه (`access.py`)
`accessible_project_ids(request)` منبعِ واحدِ محدودسازی است — در همه‌جای اپ استفاده می‌شود
(پروژه‌ها/تسک‌ها/تقویم/داشبورد/همکاران، نه فقط اینجا؛ `docs/PLATFORM.md`):
- **مالکِ سازمان** (`Membership.role == 'owner'`) **یا** دارنده‌ی پرمیشنِ سازمانیِ
  `view_all_projects` → همه‌ی پروژه‌ها **منهای پروژه‌های شخصیِ دیگران** (پایین).
  **باگِ جدیِ رفع‌شده:** قبلاً فقط `role == 'owner'` نامحدود بود — نقشِ سفارشی/built-inی
  که پرمیشنِ «مدیریتِ همه‌ی پروژه‌ها» داشت هم تا وقتی به‌صراحت به `Project.members` هر
  پروژه اضافه نمی‌شد عملاً هیچ‌چیز نمی‌دید (`ids=[]`، حتی نمی‌توانست تسک بسازد) — یعنی
  «دادنِ دسترسی» از تنظیمات عملاً بی‌اثر بود. چون این پرمیشن یعنی «مدیریتِ همه‌ی
  پروژه‌ها»، الان مثلِ مالک نامحدود است.
- بقیه (بدونِ `view_all_projects`، حتی مدیر یک پروژه) → فقط پروژه‌هایی که `Colleague`ِ
  متصل‌به‌کاربرشان (`request.user.colleague`) عضوِ `Project.members` آن‌هاست؛ اگر کاربر
  اصلاً `colleague` وصل ندارد → لیستِ خالی. **مدیرِ پروژه هم باید صریحاً به `members`
  اضافه شود** تا پروژه و تسک‌هایش را ببیند — تعیینِ `manager` به‌تنهایی دسترسی نمی‌دهد.
  در ویو: `ids = accessible_project_ids(request)`؛ `if ids is not None: qs = qs.filter(id__in=ids)`.
- **⚠️ تغییرِ قرارداد:** این تابع **دیگر هیچ‌وقت `None` («بدونِ محدودیت») برنمی‌گرداند** —
  همیشه یک لیست (ممکن است خالی). دلیل: پروژه‌ی شخصی (پایین) باید حتی از مالک/سوپریوزر هم
  پنهان بماند، پس تنها راهِ enforcementِ مطمئن این است که فهرست همیشه ساخته و پروژه‌های
  شخصیِ دیگران از آن حذف شوند. همه‌ی فراخوان‌ها الگوی `if ids is not None: filter(...)` را
  دارند که با لیست هم درست کار می‌کند، پس چیزی نمی‌شکند. اگر فراخوانِ جدیدی نوشتی، **هرگز**
  به `ids is None` به‌عنوانِ «همه را نشان بده» تکیه نکن.

## پروژه‌ی «شخصی» (`personal_owner`) — استثنای امنیتیِ سخت
هر همکار به‌صورتِ خودکار یک پروژه‌ی «شخصی» دارد که **فقط خودش** می‌بیند — هیچ‌کس دیگر،
حتی مالکِ سازمان/سوپریوزر:
- **مدل:** `Project.personal_owner` (FK به `Colleague`، `null=True`). property `is_personal`
  = `personal_owner_id is not None`.
- **ساختِ خودکار:** `projects/signals.py: ensure_personal_project` (`post_save` روی
  `Colleague`، idempotent) — نام `'شخصی'`، `manager=خودش`، `members={خودش}`. مهاجرتِ
  `0006_backfill_personal_projects` همین را برای همکارانِ موجود ساخته.
- **enforcement:** تنها نقطه `access.py` است (بالا) — پروژه‌ی شخصیِ متعلق به دیگران با
  `exclude(Q(personal_owner__isnull=False) & ~Q(personal_owner=colleague))` همیشه حذف
  می‌شود؛ چون همه‌ی صفحات از همین لیست می‌خوانند، جای دیگری لازم نیست گیت شود.
- **UI:** در لیستِ پروژه‌ها اولِ جدول می‌آید (`views.py` با annotateِ `_personal` مرتب
  می‌کند) با بَجِ «شخصی»؛ و **ردیف‌های ماهِ گزارش** (قبلی/فعلی/بعدی) برایش نمایش داده
  نمی‌شود (`{% if not p.is_personal %}` در تمپلیت).
  **استثنا:** تسکی که مستقیماً به فردِ بدونِ عضویتِ پروژه دلیگیت شده را همان فرد در
  لیستِ تسک‌های خودش می‌بیند (نه در پروژه)، چون `tasks.queries.build_task_queryset`
  علاوه بر `project_id__in=ids`، `assignee_id=خودش` را هم OR می‌کند (`tasks/CLAUDE.md`).
- تبِ «دسترسی به همکاران» در سینگلِ پروژه (`project_members` API، PATCH) این فهرست را
  می‌سازد؛ نیازمندِ `project_colleagues_access`.

## فایل‌ها / URLها
- `views.py` — List (جدولی، بازه، آخرین‌گزارش، محدودشده با `accessible_project_ids`) ·
  Detail (تب‌ها، `get_object` اگر پروژه در فهرستِ دسترسی نباشد `PermissionDenied`) ·
  CRUD(گیت‌شده با `add_project`/`edit_project` — بالا) · archive/restore(`edit_project`) ·
  API دسترسی‌ها (`credential_create/reveal/delete`، `project_credentials`) ·
  **فایل‌ها** (`project_files`, `project_file_delete` — Attachment روی پروژه، drag&drop) ·
  **`project_members`** (PATCH، تبِ دسترسی، `project_colleagues_access`).
  **ستون‌های جدولِ لیست سفارشی‌سازی‌شدنی‌اند:** فقط ستونِ «پروژه» ثابت است، بقیه از
  `core.columns.get_columns('projects','page')` می‌آیند (annotate: planned/done/remaining/
  overdue/minutes/words + پایتونی: progress/state) — تنظیم در `/settings/columns/`.
- `forms.py` — نوع/تیم چک‌باکسی، تاریخ‌های `jdate`، توضیحات `rich-editor` + `clean_html`.
- تب‌های سینگل: نمای‌کلی(آمار بازه) · تسک‌ها · **کلمات کلیدی**(فقط اگر `track_keyword_rank`؛
  منطق/مدل در `seo/rank.py` + `seo/models.py`) · تقویم(embed) · فایل‌ها(`project_files`) ·
  دسترسی‌ها(`project_credentials`) · **دسترسی به همکاران**(`project_colleagues_access`) ·
  گزارش‌ها(`project_reports`) · حسابداری(`manage_finance`، placeholder).

## لوگوی پروژه
`Project.logo` (ImageField) — آپلود در فرمِ پروژه؛ نمایش با پارشالِ `projects/_logo.html`
(لوگو یا fallbackِ رنگی از `color`+حرفِ اول) در لیستِ پروژه‌ها، ردیف‌های تسک، دراپ‌داونِ
غنی (`data-img`) و هدرِ گزارشِ عمومی.

## نکات
- «آخرین پرداخت» در لیست فعلاً `—` است؛ بعد از ساخت `finance` وصل شود.
- **دکمه‌های «ویرایش»/«＋ پروژه‌ی جدید»/«غیرفعال‌سازی» فقط با پرمیشنِ granularِ متناظرشان
  (`edit_project`/`add_project`/`edit_project`) نشان داده می‌شوند** (لیست + سینگل) —
  قبلاً همیشه دیده می‌شدند و کلیک روی‌شان ۴۰۳ِ تمام‌صفحه‌ی جنگو می‌داد (نه توستِ داخلِ
  صفحه، چون این‌ها ناوبریِ واقعی‌اند، نه fetch). هر جای دیگر هم که یک لینک/دکمه فقط
  برای صاحبِ یک پرمیشن معنا دارد، همین الگو را رعایت کن: گیت‌کردنِ سرور به‌تنهایی کافی
  نیست، UI هم باید پنهانش کند.
