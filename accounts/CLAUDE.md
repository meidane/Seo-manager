# accounts/ — هویت و سازمان (چندشرکتی — مقدمات)

> نقشه‌ی کاملِ تبدیل به پلتفرمِ چندشرکتی: **`docs/PLATFORM.md`**.

## مدل‌ها
- **Organization** (شرکت/کسب‌وکار) — بالاترین سطحِ tenant؛ `name, slug(auto), is_active`.
- **Team** — `organization(FK)` + `parent(self-FK)` برای **زیرمجموعه** (چند سطح).
- **User** (`AUTH_USER_MODEL='accounts.User'`) — `avatar` + `team` (**قدیمی/deprecated**؛
  منبعِ اصلیِ عضویت جدول‌های جدیدند). `default_membership()` = سازمانِ جاری.
- **Membership** (user↔org) — `role` + `is_active`. `can('perm')` و `.perms`.
- **TeamMembership** (user↔team) — عضویت در تیم/زیرمجموعه.

## نقش/دسترسی (`permissions.py`)
نقش‌ها: owner/admin/manager/member/viewer. کلیدها: `manage_org, manage_people,
manage_projects, manage_tasks, manage_finance, review, view_reports`. نگاشت در `ROLE_PERMS`.
بررسی: `Membership.can(perm)`؛ در تمپلیت `{% if 'x' in org_perms %}` (از context_processor).

## صفحه/API
- **`/settings/people/`** (`PeopleView`) — مدیریتِ تیم‌ها/زیرمجموعه‌ها + افراد و نقش‌ها.
  محافظت با `_require(request,'manage_people')`. تمپلیت `accounts/people.html`
  (+ include بازگشتیِ `accounts/_team_node.html`).
- API: `team_create`, `team_edit`(PATCH/DELETE), `person_create`, `person_edit`(PATCH/DELETE).
  «حداقل یک مالک باید بماند» در person_edit تضمین می‌شود.
- ورود/خروج: `LoginView/LogoutView`؛ `registration/login.html`.

## context_processor
`accounts.context_processors.org` → `current_org, current_membership, org_perms`
(در settings ثبت شده).

## ⚠️ مهم (فاز بعدی)
داده‌ی اپ‌های دیگر (Project/Task/…) هنوز به سازمان **اسکوپ نشده** — نصبِ فعلی تک‌شرکتی است.
برای چندشرکتیِ واقعی، فاز ۱ در `docs/PLATFORM.md` (افزودن `organization` + فیلترِ کوئری‌ها).

> اگر فیلد به User اضافه کردی، مراقب migration و `createsuperuser` باش.
