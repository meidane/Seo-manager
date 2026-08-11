# colleagues/ — «افراد و دسترسی‌ها» (بخشِ واحد؛ /settings/people/ فقط تیم‌ها/نقش‌هاست)

> **این اپ همان چیزی است که در سایدبار «افراد و دسترسی‌ها» نامیده می‌شود.** قبلاً دو منوی
> جدا بودند («همکاران» اینجا + «افراد و دسترسی‌ها» در `accounts`) که هم‌پوشانیِ گیج‌کننده
> داشتند؛ ادغام شدند — همه‌ی افراد (چه دسترسیِ لاگین داشته باشند چه نه) اینجا مدیریت
> می‌شوند. `accounts:people` فقط برای تیم‌ها/زیرمجموعه‌ها و نقش‌های سفارشی مانده.

## مدل
**Colleague** — `full_name, roles(CSV، فقط سمتِ نمایشی — ربطی به accounts.Role ندارد),
avatar, color, description, phone/email, status, archived_at, join_date, user(O2O)،
manager(FK self، اختیاری)، needs_review(bool)`. `archive()/restore(),
roles_list/roles_display, initials, is_active`.
- **`manager`/`needs_review`**: اگر مدیر تعیین شود و `needs_review=True`، تسک‌های
  انجام‌شده‌ی این همکار برای تاییدِ همان مدیر به «بازبینی تسک» می‌رود (`tasks/views.py:
  TaskReviewView`) — مستقل از دسترسیِ سازمانیِ `review`. `save()` خودش جلوی
  خودمدیریتی و «بدونِ مدیر ولی needs_review» را می‌گیرد.
- **`user`** (O2O، اختیاری): وصلِ فرد به حسابِ کاربریِ پلتفرم. تا وقتی خالی است، فرد فقط
  یک رکورد است (بدونِ لاگین) — **این حالت عمداً حفظ شده** («افزودنِ فرد» بدونِ دسترسی
  همچنان کار می‌کند، برای موقعی که فقط می‌خواهیم کارش را ردیابی کنیم، نه اینکه لاگین
  داشته باشد).

## دسترسی به سیستم — فقط با شماره تماس، هرگز نام‌کاربری/رمز
تبِ اطلاعاتِ سینگلِ فرد (بخشِ «دسترسی به سیستم») تنها راهِ دادنِ دسترسی است. مدیر **فقط
شماره تماس** را وارد می‌کند (`colleague_grant_access`) — ساختِ حساب همیشه دستِ خودِ فرد
است، نه ما:
- شماره از قبل حساب دارد → `accounts.Invite` بلافاصله به آن حساب وصل می‌شود.
- شماره حساب ندارد → `Invite` با `user=None` + `phone` ساخته می‌شود؛ وقتی همان شماره در
  `/signup/` ثبت‌نام کند، `accounts.views.signup` به‌جای ساختِ سازمانِ تازه فقط حساب
  می‌سازد و به همین دعوت وصل می‌کند (`accounts/CLAUDE.md`).

در هر دو حالت، `Invite.accept()` هم عضویت می‌سازد هم `colleague.user` را وصل می‌کند —
بعدش تبِ «دسترسی به سیستم» یک مینی‌فرمِ نقشِ سازمانی + تیم‌ها + فعال/غیرفعال نشان می‌دهد
که مستقیم به `accounts:person_edit` (PATCH/DELETE، با `pk=colleague.user_id`) وصل است؛
منطقِ نقش/تیم را اینجا تکرار نکن، همان API را صدا بزن.

## فایل‌ها
- `views.py`:
  - `ColleagueListView` — **جدولی** با آمار بازه‌ای (annotate: planned/done/words/minutes/overdue)
    + اسپارک‌لاین ۱۴ روزه (یک کوئری، گروه‌بندی پایتون در `get_context_data`) + ستونِ
    «دسترسی» (`c.access_status`: `has_access`/`pending`/`none`، یک کوئریِ Invite برای
    کلِ صفحه). ستون‌های آماری از `core.columns.get_columns('colleagues','page')` می‌آیند
    — تنظیم در `/settings/columns/`.
  - `ColleagueDetailView` — آمار بازه، **دونات** تفکیک نوع (`donut_segments`)، تفکیک پروژه،
    روند روزانه، تب تقویم شخصی (embed)، تب تسک‌ها + بخشِ «دسترسی به سیستم» (بالا).
  - CRUD + archive/restore («افزودنِ فرد» — فقط پروفایل، بدونِ حساب).
  - `colleague_grant_access` / `colleague_revoke_invite` — API دعوت‌نامه‌ی دسترسی؛
    گیت‌شده با `manage_colleagues`.
- `forms.py` — نقش چک‌باکسی، `join_date` با `jdate`، توضیحات `rich-editor` + `clean_html`.

## نکته
`.who/.spark/.donut-legend` باید در `static/css/style.css` باشند (بودند نبودند → رفع شد).

## TODO
`donut_segments`/`TYPE_HEX`/`TYPE_LABEL` (تفکیکِ نوع در سینگل همکار) هنوز بر پایه‌ی
`task_type` خام‌اند — تسک‌های نوعِ کاملاً سفارشی (سئوی جدید و بعدی‌ها) همه زیرِ «سایر»
جمع می‌شوند چون `task_type='other'` دارند. برای تفکیکِ درست باید به `type_def` سوییچ کند
(مثلِ فیلترِ لیست/تقویم که همین گام سوییچ شد).
