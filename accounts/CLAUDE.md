# accounts/ — هویت، سازمان و چندشرکتی (tenant)

> نقشه‌ی کامل: **`docs/PLATFORM.md`**.

## مدل‌ها
- **Organization** (شرکت) — بالاترین سطحِ tenant؛ `name, slug(auto), is_active`.
- **Team** — `organization` + `parent`(self) برای زیرمجموعه (چند سطح).
- **User** — `avatar, phone` + `team`(deprecated). `default_membership()`.
- **Membership** (user↔org) — `role`(کلید Role)، `is_active`. `.perms` / `.can(perm)` /
  `.role_label`. مالک همیشه `'*'` (همه).
- **TeamMembership** (user↔team).
- **Role** (per org) — `key, name, perms(JSON), is_builtin`. `seed_roles(org)` ۵ نقشِ
  پیش‌فرض می‌سازد؛ سازمان می‌تواند نقشِ سفارشی هم بسازد.

## چندشرکتی (`tenancy.py`) — مهم
- **سازمانِ جاری** در thread-local؛ `CurrentOrgMiddleware` آن را از session
  (`active_org_id`) یا اولین عضویت resolve و روی `request.organization/membership` می‌گذارد.
  مسیرهای `/admin/` اسکوپ نمی‌شوند.
- **`TenantManager`**: مدل‌های tenant `objects` را به سازمانِ جاری فیلتر می‌کنند.
  **قانون:** خواندنِ اسکوپ‌شده = `Model.objects`؛ خواندنِ بدون فیلتر (migration/command/عمومی)
  = `Model.all_objects`. در `save()` سازمان از سازمانِ جاری استمپ می‌شود (`stamp_org`).
- مدل‌های tenant: Project, Colleague, Task, TaskTypeDef, Report, BankAccount, Category,
  Transaction, Payroll. (Holiday **عمومیِ ملی** است، اسکوپ نمی‌شود.)
- **تله:** management commandها سازمانِ جاری ندارند → `objects` بدون فیلتر برمی‌گرداند؛
  seedهای per-org باید سازمان را صریح بدهند یا `set_current_org` کنند.

## صفحه/API (`/settings/people/`)
مدیریتِ تیم‌ها/زیرمجموعه‌ها، افراد+نقش، **دعوت با شماره‌ی تماس** (فردِ ثبت‌نام‌کرده)،
و **نقش‌های سفارشی**. محافظت با `_require(request, perm)`.
API: `team_create/edit`, `person_create/edit`, `person_invite`, `role_create/edit`, `switch_org`.

## ثبت‌نام و سوییچر
- **`/signup/`** — ثبت‌نامِ آزاد: کاربرِ مالک + سازمان + `seed_roles`. (`registration/signup.html`)
- **سوییچرِ سازمان** در هدر (اگر کاربر در چند سازمان باشد) → `switch_org` (session).

## context_processor
`accounts.context_processors.org` → `current_org, current_membership, org_perms, my_orgs`.

> اگر فیلد به User اضافه کردی، مراقب migration و `createsuperuser` باش.
