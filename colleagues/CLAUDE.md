# colleagues/ — «افراد و دسترسی‌ها» (بخشِ واحد؛ /settings/people/ فقط تیم‌ها/نقش‌هاست)

> **این اپ همان چیزی است که در سایدبار «افراد و دسترسی‌ها» نامیده می‌شود.** قبلاً دو منوی
> جدا بودند («همکاران» اینجا + «افراد و دسترسی‌ها» در `accounts`) که هم‌پوشانیِ گیج‌کننده
> داشتند؛ ادغام شدند — همه‌ی افراد (چه دسترسیِ لاگین داشته باشند چه نه) اینجا مدیریت
> می‌شوند. `accounts:people` فقط برای تیم‌ها/زیرمجموعه‌ها و نقش‌های سفارشی مانده.

## مدل
**Colleague** — `full_name, roles(CSV — کلیدهای accounts.Role، پایین)، avatar, color,
description, phone/email, status, archived_at, join_date, user(O2O)، manager(FK self،
اختیاری)، needs_review(bool)`. `archive()/restore(), roles_list/roles_display, initials,
is_active`.
- **`manager`/`needs_review`**: اگر مدیر تعیین شود و `needs_review=True`، تسک‌های
  انجام‌شده‌ی این همکار برای تاییدِ همان مدیر به «بازبینی تسک» می‌رود (`tasks/views.py:
  TaskReviewView`) — مستقل از دسترسیِ سازمانیِ `review`. `save()` خودش جلوی
  خودمدیریتی و «بدونِ مدیر ولی needs_review» را می‌گیرد.
- **`user`** (O2O، اختیاری): وصلِ فرد به حسابِ کاربریِ پلتفرم. تا وقتی خالی است، فرد فقط
  یک رکورد است (بدونِ لاگین) — از طریقِ ویرایشِ سینگل هنوز می‌شود ساخت (نه دیگر از دکمه‌ی
  «افزودن فرد»، که حذف شد — پایین).
- **`roles`**: دیگر از فهرستِ ثابتِ قدیمی نمی‌آید — `ColleagueForm` چک‌باکس‌هایش را از
  `org.roles.all()` می‌سازد (همان کاتالوگِ «تنظیمات → تیم‌ها و نقش‌ها») و `roles_display`
  هم برچسب را از همان‌جا resolve می‌کند (نه دیکشنریِ هارد‌کد). یعنی این تگ‌ها همیشه با
  نقش‌های واقعیِ سازمان هماهنگ‌اند، نه یک لیستِ جداگانه‌ی «نویسنده/سئو/سرپرست/فنی».
- **`ensure_colleague_for_user(user, org)`**: هرکسی که به سازمان دسترسی دارد (مثلاً
  مالکی که موقعِ ساختِ سازمان Colleague نساخته) باید در همین فهرست هم دیده شود — وگرنه
  `own_tasks_only`/پیش‌فرضِ «مسئول = خودم» برایش کار نمی‌کند. از `ColleagueListView.dispatch`
  و `tasks.api.form_data` صدا زده می‌شود (idempotent — اگر از قبل داشت کاری نمی‌کند).

## «افزودن فرد» حذف شد
دیگر راهِ جدایی برای «فقط پروفایل، بدونِ حساب» نیست — منطقی نداشت. تنها راهِ افزودنِ فرد
همان دکمه‌ی «＋ کاربر جدید» است (پایین)، همیشه همراه با یک تصمیمِ دسترسی (دعوت یا رمزِ
مستقیم). ویرایشِ فیلدهای غنی‌تر (آواتار/رنگ/توضیحات/مدیر) بعداً از صفحه‌ی ویرایشِ همان
فرد انجام می‌شود.

## دسترسیِ scoped — مدیر می‌تواند زیرمجموعه‌ی خودش را مدیریت کند، نه فقط `manage_people`
پرمیشنِ سازمانیِ `manage_people` قبلاً تنها راهِ ویرایش/آرشیو/دادنِ‌دسترسیِ یک فرد بود —
یعنی یا کسی همه‌ی سازمان را می‌دید یا هیچ‌کس. `colleagues/access.py: can_manage_colleague(
request, target)` این را باز کرد: `manage_people` (همه) **یا** مدیرِ مستقیم/غیرمستقیمِ
همان فرد بودن (`target.id in all_subordinate_ids(my_colleague)`، هر عمقی). این تابع
گیتِ `ColleagueUpdateView.get_object`، `ColleagueArchiveView`/`RestoreView`،
`colleague_grant_access`، `colleague_revoke_invite` است — نه چکِ سراسری، بلکه
per-object (این فردِ مشخص).
- **`ColleagueListView.ctx['can_manage_colleagues']`** (نمایشِ دکمه‌ی «＋ کاربر جدید») =
  `manage_people` **یا** `is_manager_tier(request)` (زیرمجموعه دارد یا پرمیشنِ ناظر).
- **`ColleagueDetailView.ctx['can_manage_colleagues']`** حالا per-object است
  (`can_manage_colleague(request, c)`) — دیگر یک بولِ سراسری نیست.
- **`ColleagueDetailView.ctx['can_manage_org_role']`** عمداً **جدا** ماند و همیشه فقط
  `manage_people` است — تغییرِ نقشِ سازمانی/تیمِ کسی که از قبل حساب دارد
  (`accounts:person_edit`، بخشِ «تنظیماتِ عضویت» در تبِ دسترسی) ریسکش از ویرایشِ
  پروفایل بالاتر است، پس scoped نشد.
- **سقفِ نقش در اعطای دسترسی:** مدیرِ scoped (بدونِ `manage_people`) وقتی برای زیردستش
  دسترسی می‌سازد (`colleague_grant_access`/`quick_create`)، نمی‌تواند نقشِ سطح‌بالا
  بدهد — `accounts.access.is_elevated_role(org, role_key)` (owner/admin یا هر نقشی که
  خودش `manage_people`/`manage_org` دارد) را `_grant_access(..., allow_elevated_roles=
  False)` مسدود می‌کند (۴۰۳). دراپ‌داونِ نقش هم همین فهرست را می‌بیند
  (`_grantable_roles(org, full_access)`، هم در فهرست هم در سینگل) — گزینه‌ای که نمی‌تواند
  انتخاب کند اصلاً در UI هم نیست.
- **`colleague_quick_create`**: اگر ساینده `manage_people` نداشت (فقط `is_manager_tier`)،
  `manager`ِ فردِ تازه خودکار خودِ ساینده می‌شود — وگرنه فردی می‌ساخت که دیگر خودش هم
  اجازه‌ی مدیریتش را نداشت (بیرون از `all_subordinate_ids` خودش می‌افتاد).
- **تست:** `teamlead1` (بدونِ `manage_people`) می‌تواند `member1`/`member2` (زیردستش) را
  ویرایش/آرشیو کند و برایشان دسترسی بسازد (فقط نقشِ غیرِسطح‌بالا)، ولی نمی‌تواند
  `viewer1` (بیرون از زیرمجموعه‌اش) را لمس کند یا نقشِ `admin` بسازد — `admin1`
  (`manage_people`) همچنان محدودیتی ندارد.

## دسترسی به سیستم — دو حالت، منبع واحد `_grant_access`
تبِ اطلاعاتِ سینگلِ فرد (بخشِ «دسترسی به سیستم») + دکمه‌ی «＋ کاربر جدید» در فهرست، هر دو
از `colleagues.views._grant_access(request, org, colleague, d)` استفاده می‌کنند — منطق را
جای دیگر تکرار نکن:
- **`mode=invite`** (پیش‌فرض): فقط شماره تماس؛ ساختِ حساب دستِ خودِ فرد است.
  شماره از قبل حساب دارد → `accounts.Invite` بلافاصله به آن حساب وصل می‌شود. شماره حساب
  ندارد → `Invite` با `user=None` + `phone` ساخته می‌شود؛ وقتی همان شماره در `/signup/`
  ثبت‌نام کند، `accounts.views.signup` به‌جای ساختِ سازمانِ تازه فقط حساب می‌سازد و به
  همین دعوت وصل می‌کند (`accounts/CLAUDE.md`). دسترسی **در انتظارِ قبولِ خودِ اوست**.
- **`mode=password`**: مدیر خودش نام‌کاربری/رمز را تعیین می‌کند — دسترسیِ **فوری**، بدونِ
  Invite/در انتظار (نسخه‌ی اولیه‌ای که خودمان دسترسی‌ها را می‌سازیم، طبق درخواستِ صریح).

دو نقطه‌ی ورود:
- **فردِ موجود، بدونِ دسترسی** → `colleague_grant_access` (پروفایلِ خودِ فرد، `pk` لازم).
- **فردِ کاملاً تازه** → `colleague_quick_create` (دکمه‌ی «＋ کاربر جدید» در `/colleagues/`)
  — یک Colleague می‌سازد + بلافاصله `_grant_access` صدا می‌زند؛ اگر دسترسی شکست خورد
  (مثلاً نام‌کاربری تکراری)، Colleagueِ تازه‌ساز هم rollback می‌شود (حذف)، نه نیمه‌کاره بماند.

در هر دو حالت، `Invite.accept()` هم عضویت می‌سازد هم `colleague.user` را وصل می‌کند —
بعدش تبِ «دسترسی به سیستم» یک مینی‌فرمِ نقشِ سازمانی + تیم‌ها + فعال/غیرفعال نشان می‌دهد
که مستقیم به `accounts:person_edit` (PATCH/DELETE، با `pk=colleague.user_id`) وصل است؛
منطقِ نقش/تیم را اینجا تکرار نکن، همان API را صدا بزن.

## فایل‌ها
- `views.py`:
  - `ColleagueListView` — **جدولی** با آمار بازه‌ای (annotate: planned/done/words/minutes/overdue)
    + اسپارک‌لاین ۱۴ روزه (یک کوئری، گروه‌بندی پایتون در `get_context_data`) + ستونِ
    «دسترسی» (`c.access_status`: `has_access`/`pending`/`none`، یک کوئریِ Invite برای
    کلِ صفحه) + دکمه‌ی «＋ کاربر جدید» (مودالِ دو-حالته، بالا). ستون‌های آماری از
    `core.columns.get_columns('colleagues','page')` می‌آیند — تنظیم در `/settings/columns/`.
  - `ColleagueDetailView` — آمار بازه، **دونات** تفکیک نوع (`donut_segments`)، تفکیک پروژه،
    روند روزانه، تب تقویم شخصی (embed)، تب تسک‌ها + بخشِ «دسترسی به سیستم» (بالا).
  - CRUD + archive/restore («افزودنِ فرد» — فقط پروفایل، بدونِ حساب). گیت‌شده با
    `can_manage_colleague` (سازمانی یا مدیرِ همان فرد — بالا)، نه فقط `manage_people`.
  - `colleague_grant_access` / `colleague_quick_create` / `colleague_revoke_invite` —
    API دسترسی؛ همان `can_manage_colleague`/`is_manager_tier` (بالا)، با سقفِ نقش
    برای مدیرِ scoped.
- `forms.py` — نقش چک‌باکسی، `join_date` با `jdate`، توضیحات `rich-editor` + `clean_html`.
- `access.py` — **منبعِ واحدِ زنجیره‌ی مدیریتی**: `all_subordinate_ids(colleague)` (BFS
  روی `Colleague.manager`، همه‌ی زیرمجموعه‌ها در هر عمقی، نه فقط مستقیم)،
  `is_manager_tier(request)` (زیرمجموعه دارد یا پرمیشنِ ناظر)، و `can_manage_colleague(
  request, target)` (بالا). `tasks/queries.py` و `tasks/api.py: task_review` هم از
  `all_subordinate_ids`/`is_manager_tier` می‌خوانند — اینجا زندگی می‌کند نه در `tasks/`
  چون فقط به `Colleague` وابسته است (جهتِ درستِ وابستگی: `tasks` به `colleagues`
  وابسته است، نه برعکس).

## اتصال به حضورغیاب (worktracker — پروژه‌ی مجزا)
هر همکار می‌تواند به سامانه‌ی حضورغیابِ **worktracker** وصل شود (`Colleague.
worktracker_username`) + `Colleague.birth_date`. seo-manager فقط **می‌خواند** (سرور-به-سرور):
- **کلاینت:** `colleagues/worktracker.py` — `today_all()` (خلاصه‌ی امروزِ همه، کشِ ۶۰ثانیه)
  و `user_detail(username, days)`. اگر `WORKTRACKER_BASE_URL/TOKEN` (settings/env) خالی
  یا سامانه در دسترس نباشد، **بی‌صدا خالی برمی‌گردد** (روی هستهٔ سیستم بی‌اثر).
- **تبِ «حضور غیاب»** = تبِ **اولِ** سینگلِ همکار (`ColleagueDetailView.wt_detail`)، تایم‌لاینِ
  چند روزِ اخیر با پارشالِ `colleagues/_attendance_day.html` (همان طرحِ worktracker:
  نوارِ آبی/بی‌فعالیتی، جمع ساعت، شروع/پایان، تعداد کلمات، آیکنِ برنامه‌ها).
- **لیستِ همکاران:** زیرِ هر فرد یک ردیفِ حضورِ امروز (`c.wt_today`) + نشانگرِ آنلاین
  (سبز) روی آواتار.
- **سایدبار، بخشِ «همکاران»** (آخرِ منو): `colleagues/context_processors.sidebar_attendance`
  (فقط اگر worktracker پیکربندی شده — وگرنه هیچ کوئری‌ای نمی‌زند). هر فرد: آواتار+آنلاین،
  نام، آخرین تسکِ انجام‌شده (هاور: تاریخ)، مینی‌تایم‌لاین + جمع ساعت + شروع/پایان (هاور).
- ساختار/APIِ worktracker: **repoِ مجزا** `meidane/worktracker` (شاخهٔ `claude/attendance-api`)
  — `CLAUDE.md`ی همان‌جا. اندپوینت‌ها: `GET /api/attendance/today/` و
  `/api/attendance/user/<username>/` (هدرِ `Authorization: Token <WORKTRACKER_API_TOKEN>`).
- فیلترها/فرمتِ زمان: `seo_extras: min_hm`(دقیقه→HH:MM)، `sec_hm`(ثانیه→HH:MM).

## نکته
`.who/.spark/.donut-legend` باید در `static/css/style.css` باشند (بودند نبودند → رفع شد).

## TODO
`donut_segments`/`TYPE_HEX`/`TYPE_LABEL` (تفکیکِ نوع در سینگل همکار) هنوز بر پایه‌ی
`task_type` خام‌اند — تسک‌های نوعِ کاملاً سفارشی (سئوی جدید و بعدی‌ها) همه زیرِ «سایر»
جمع می‌شوند چون `task_type='other'` دارند. برای تفکیکِ درست باید به `type_def` سوییچ کند
(مثلِ فیلترِ لیست/تقویم که همین گام سوییچ شد).
