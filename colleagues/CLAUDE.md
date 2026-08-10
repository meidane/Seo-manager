# colleagues/

## مدل
**Colleague** — `full_name, roles(CSV، فقط سمتِ نمایشی — ربطی به accounts.Role ندارد),
avatar, color, description, phone/email, status, archived_at, join_date, user(O2O)،
manager(FK self، اختیاری)، needs_review(bool)`. `archive()/restore(),
roles_list/roles_display, initials, is_active`.
- **`manager`/`needs_review`**: اگر مدیر تعیین شود و `needs_review=True`، تسک‌های
  انجام‌شده‌ی این همکار برای تاییدِ همان مدیر به «بازبینی تسک» می‌رود (`tasks/views.py:
  TaskReviewView`) — مستقل از دسترسیِ سازمانیِ `review`. `save()` خودش جلوی
  خودمدیریتی و «بدونِ مدیر ولی needs_review» را می‌گیرد.
- `rate_per_word`/`rate_per_task` حذف شدند (بدون استفاده در finance).
- **`user`** (O2O، اختیاری): وصلِ همکار به حسابِ کاربریِ پلتفرم. تا وقتی خالی است،
  همکار فقط یک رکورد است (بدونِ لاگین). دادنِ دسترسی از تبِ «اطلاعات»ِ سینگل همکار،
  با `colleague_grant_access` (نه اتصالِ مستقیم) — همیشه `accounts.Invite`ِ در انتظار
  می‌سازد، نه عضویتِ فوری؛ `Invite.accept()` هم عضویت می‌سازد هم `colleague.user` را
  وصل می‌کند. جزئیاتِ کاملِ Invite: `accounts/CLAUDE.md`.

## فایل‌ها
- `views.py`:
  - `ColleagueListView` — **جدولی** با آمار بازه‌ای (annotate: planned/done/words/minutes/overdue)
    + اسپارک‌لاین ۱۴ روزه (یک کوئری، گروه‌بندی پایتون در `get_context_data`). ستون‌های آماری
    (نه نام/اسپارک‌لاین/وضعیت که ثابت‌اند) از `core.columns.get_columns('colleagues','page')`
    می‌آیند — تنظیم در `/settings/columns/`.
  - `ColleagueDetailView` — آمار بازه، **دونات** تفکیک نوع (`donut_segments`)، تفکیک پروژه،
    روند روزانه، تب تقویم شخصی (embed)، تب تسک‌ها.
  - CRUD + archive/restore.
  - `colleague_grant_access` / `colleague_revoke_invite` — API دعوت‌نامه‌ی دسترسی
    (تبِ اطلاعاتِ سینگل همکار)؛ گیت‌شده با `manage_colleagues`.
- `forms.py` — نقش چک‌باکسی، `join_date` با `jdate`، توضیحات `rich-editor` + `clean_html`.

## نکته
`.who/.spark/.donut-legend` باید در `static/css/style.css` باشند (بودند نبودند → رفع شد).

## TODO
`donut_segments`/`TYPE_HEX`/`TYPE_LABEL` (تفکیکِ نوع در سینگل همکار) هنوز بر پایه‌ی
`task_type` خام‌اند — تسک‌های نوعِ کاملاً سفارشی (سئوی جدید و بعدی‌ها) همه زیرِ «سایر»
جمع می‌شوند چون `task_type='other'` دارند. برای تفکیکِ درست باید به `type_def` سوییچ کند
(مثلِ فیلترِ لیست/تقویم که همین گام سوییچ شد).
