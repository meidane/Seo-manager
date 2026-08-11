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
- **Invite** — دعوت‌نامه‌ی **در انتظار** (نه عضویتِ فوری). `organization, user(اختیاری)،
  phone، role، colleague(اختیاری، FK به `colleagues.Colleague`)، status(pending/accepted/
  rejected)، invited_by`. تنها راهِ ساخت: `colleagues.views.colleague_grant_access` (تبِ
  «دسترسی به سیستم» در سینگلِ فرد) — **فقط با شماره تماس**، هرگز نام‌کاربری/رمز نمی‌سازیم:
  - شماره از قبل حساب دارد → `user` بلافاصله ست می‌شود.
  - شماره حساب ندارد → `user=None`، فقط `phone` ذخیره می‌شود؛ وقتی همان شماره در
    `/signup/` ثبت‌نام کند، `views.signup` به‌جای ساختِ سازمانِ تازه فقط حساب می‌سازد و
    آن را به همین دعوت وصل می‌کند («claim» — بدونِ این مسیر، سازمانِ تازه ساخته می‌شود).
  `accept()` عضویت می‌سازد (+ `colleague.user` را هم وصل می‌کند)؛ `reject()` فقط وضعیت
  را عوض می‌کند (می‌شود دوباره دعوت کرد).

## چندشرکتی (`tenancy.py`) — مهم
- **سازمانِ جاری** در thread-local؛ `CurrentOrgMiddleware` آن را از session
  (`active_org_id`) یا اولین عضویت resolve و روی `request.organization/membership` می‌گذارد.
  مسیرهای `/admin/` اسکوپ نمی‌شوند.
- **`OrgRequiredMiddleware`** (بعد از `CurrentOrgMiddleware`): کاربرِ لاگین‌شده‌ای که هنوز
  عضوِ هیچ سازمانی نیست (دعوتی تازه، هنوز قبول نکرده) را به `/invites/` می‌فرستد — جز
  مسیرهای `_ORG_LESS_ALLOWED` (لاگین/خروج/ثبت‌نام/ادمین/استاتیک/خودِ `/invites/`).
- **`TenantManager`**: مدل‌های tenant `objects` را به سازمانِ جاری فیلتر می‌کنند.
  **قانون:** خواندنِ اسکوپ‌شده = `Model.objects`؛ خواندنِ بدون فیلتر (migration/command/عمومی)
  = `Model.all_objects`. در `save()` سازمان از سازمانِ جاری استمپ می‌شود (`stamp_org`).
- مدل‌های tenant: Project, Colleague, Task, TaskTypeDef, Report, BankAccount, Category,
  Transaction, Payroll. (Holiday **عمومیِ ملی** است، اسکوپ نمی‌شود.)
- **تله:** management commandها سازمانِ جاری ندارند → `objects` بدون فیلتر برمی‌گرداند؛
  seedهای per-org باید سازمان را صریح بدهند یا `set_current_org` کنند.

## صفحه/API (`/settings/people/`) — **فقط تیم‌ها و نقش‌های سفارشی**
«افراد» (فهرست/دسترسیِ تک‌تکِ افراد) اینجا نیست — به `colleagues:list` منتقل شد (یک بخشِ
واحدِ «افراد و دسترسی‌ها»، نه دو منوی جدا؛ جزئیات در `colleagues/CLAUDE.md`). این صفحه
فقط تیم‌ها/زیرمجموعه‌ها و نقش‌های سفارشی را مدیریت می‌کند. محافظت با `_require(request, perm)`.
API: `team_create/edit`, `person_edit`(ویرایشِ نقش/فعال‌بودن/تیمِ کسی که دعوت را پذیرفته —
از تبِ «دسترسی به سیستم» در سینگلِ فرد صدا زده می‌شود، نه از جدولی اینجا)، `role_create/edit`,
`switch_org`.

## ثبت‌نام و سوییچر
- **`/signup/`** — دو مسیر: (۱) عادی → کاربرِ مالک + سازمانِ تازه + `seed_roles`؛
  (۲) اگر شماره‌ی واردشده دعوت‌نامه‌ی در انتظارِ بدونِ‌کاربر دارد → فقط حساب ساخته و به
  همان دعوت وصل می‌شود (سازمانِ تازه ساخته نمی‌شود) — نگاه کن `Invite` بالا.
  (`registration/signup.html`)
- **سوییچرِ سازمان** در هدر (اگر کاربر در چند سازمان باشد) → `switch_org` (session).

## دعوت‌نامه‌ها (`/invites/`)
- کاربرِ بدونِ سازمان با `OrgRequiredMiddleware` به اینجا می‌افتد (`InvitesLandingView`،
  تمپلیتِ مستقل `accounts/invites.html`، بدونِ سایدبار).
- **تله‌ای که رفع شد:** کاربرِ لاگین‌شده‌ی بدونِ عضویت (مثلاً سوپریوزرِ ساخته‌شده با
  `createsuperuser`، نه از `/signup/`) قبلاً در همین صفحه گیر می‌کرد — چون `/signup/`
  کاربرِ لاگین‌شده را مستقیم به داشبورد ریدایرکت می‌کند (نه صفحه‌ی ثبت‌نام)، و داشبورد هم
  چون سازمان ندارد دوباره به `/invites/` برمی‌گشت (بن‌بست). برای همین همین صفحه یک فرمِ
  «ساختِ سازمان» هم دارد: `create_own_org` (POST، لاگین‌شده) دقیقاً همان کاری را می‌کند
  که `/signup/` برای کاربرِ لاگین‌نشده می‌کند (Organization + `seed_roles` + Membership
  owner + `active_org_id`).
- کاربرِ **با** سازمان که دعوتِ اضافه هم دارد (مثلاً به سازمانِ دوم دعوت شده) آن را در
  **بنرِ بالای هر صفحه** می‌بیند (`templates/base.html`، از `pending_invites` که
  context processor روی هر ریکوئستِ لاگین‌شده می‌گذارد).
- قبول/رد با دکمه‌های `.invite-accept`/`.invite-reject` (کلاسِ CSS، نه ID) — دلیگیتِ
  کلیکِ سراسری در `app.js` روی `data-url` اجرا می‌کند؛ همان الگو در بنر و در صفحه‌ی
  `/invites/` هر دو کار می‌کند بدون تکرارِ JS.

## context_processor
`accounts.context_processors.org` → `current_org, current_membership, org_perms, my_orgs,
pending_invites`. **تله:** `Membership.perms` برای مالک `{'*'}` است ولی چک‌های تمپلیت
(`{% if 'x' in org_perms %}`) رشته‌ی دقیق می‌خواهند — این‌جا `'*'` به `set(PERMS)` باز
می‌شود تا لینک‌های گیت‌شده برای مالک هم دیده شوند.

> اگر فیلد به User اضافه کردی، مراقب migration و `createsuperuser` باش.
