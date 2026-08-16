"""نقش‌ها و دسترسی‌های سازمانی — نسخه‌ی ساده (بعداً granular per-resource می‌شود).

هر عضو در یک سازمان یک «نقش» دارد و هر نقش مجموعه‌ای از «دسترسی» (permission flag).
این‌جا فقط تعریفِ داده است؛ منطقِ بررسی در `Membership.can()` و context_processor.

**کاتالوگ سه‌گروهی است** (`PERM_GROUPS`، برای نمایشِ گروه‌بندی‌شده در ویرایشگرِ نقش):
تنظیمات · پروژه‌ها · تسک‌ها — هر پرمیشنِ جدید را هم به `PERMS`/`PERM_LABELS` هم به
گروهِ درستش در `PERM_GROUPS` اضافه کن، وگرنه در ویرایشگرِ نقش دیده نمی‌شود.
"""

OWNER = 'owner'
ADMIN = 'admin'
MANAGER = 'manager'
MEMBER = 'member'
VIEWER = 'viewer'

ROLE_CHOICES = [
    (OWNER, 'مالک'),
    (ADMIN, 'مدیر'),
    (MANAGER, 'سرپرست'),
    (MEMBER, 'عضو'),
    (VIEWER, 'ناظر'),
]

# ── گروه ۱: تنظیمات ──────────────────────────────────────────────────────
_SETTINGS_PERMS = {
    'manage_org': 'مدیریتِ سازمان',
    'manage_teams': 'مدیریتِ تیم‌ها',
    'manage_people': 'مدیریتِ افراد (نقش‌ها و دسترسی‌ها)',
    'manage_api_tokens': 'توکن و API',
    'manage_columns': 'سفارشی‌سازیِ ستون‌ها',
    'manage_task_types': 'مدیریتِ انواعِ تسک',
    'manage_holidays': 'مدیریتِ تعطیلات',
}

# ── گروه ۲: پروژه‌ها ──────────────────────────────────────────────────────
_PROJECT_PERMS = {
    'view_all_projects': 'فعال‌سازیِ همه‌ی پروژه‌ها (دیدنِ همه، مثلِ مالک — بدونِ نیاز به عضویتِ تک‌تکِ پروژه‌ها)',
    'add_project': 'افزودنِ پروژه',
    'edit_project': 'ویرایش/فعال‌غیرفعال‌سازیِ پروژه',
    'project_files': 'دسترسی به فایل‌های پروژه',
    'project_colleagues_access': 'دسترسی به تبِ «همکاران» پروژه',
    'project_credentials': 'دسترسی به تبِ «دسترسی‌ها» (رمزهای پروژه)',
    'project_reports': 'دسترسی به تبِ «گزارش‌ها»ی پروژه',
    'manage_finance': 'دسترسی به حسابداری',
}

# ── گروه ۳: تسک‌ها ────────────────────────────────────────────────────────
_TASK_PERMS = {
    'edit_task': 'ویرایشِ تسک',
    'delete_task': 'حذفِ تسک',
    'view_other_tasks': 'مشاهده‌ی تسک‌های بقیه (بدونِ این، فقط تسک‌های خودش)',
    'edit_time': 'امکانِ ویرایشِ زمان (زمانِ دیگران)',
    'review': 'بازبینیِ تسک',
    'view_reports': 'مشاهده‌ی گزارش‌ها',
}

PERM_GROUPS = [
    ('تنظیمات', _SETTINGS_PERMS),
    ('پروژه‌ها', _PROJECT_PERMS),
    ('تسک‌ها', _TASK_PERMS),
]

PERM_LABELS = {}
for _name, _group in PERM_GROUPS:
    PERM_LABELS.update(_group)

# کلیدهای دسترسی (قابل‌گسترش) — نقش سفارشی می‌تواند هر ترکیبی از این‌ها را داشته باشد
PERMS = list(PERM_LABELS.keys())

# نگاشتِ نقش → مجموعه‌ی دسترسی‌ها (پیش‌فرضِ اولیه؛ هر سازمان می‌تواند از تنظیمات عوضش کند)
_ALL = set(PERMS)
ROLE_PERMS = {
    OWNER: _ALL,
    ADMIN: _ALL,  # «مدیر» — دسترسیِ کامل (مالک علاوه‌براین همیشه wildcard `{'*'}` هم دارد)
    MANAGER: {
        'add_project', 'edit_project', 'view_all_projects', 'project_files',
        'project_colleagues_access', 'project_credentials', 'project_reports',
        'edit_task', 'delete_task', 'view_other_tasks', 'edit_time', 'review', 'view_reports',
    },
    MEMBER: {'edit_task', 'view_reports'},  # view_other_tasks ندارد → فقط تسکِ خودش
    VIEWER: {'view_reports'},
}


def role_can(role: str, perm: str) -> bool:
    return perm in ROLE_PERMS.get(role, set())


def role_perms(role: str) -> set:
    return ROLE_PERMS.get(role, set())


# کلیدهایی که به یکی از تب‌های «تنظیمات» راه دارند — برای گیتِ لینکِ واحدِ سایدبار/
# دسترسیِ صفحه‌ی هاب (`accounts:settings_home`)، نه یک صفحه‌ی مشخص.
SETTINGS_PERMS = tuple(_SETTINGS_PERMS.keys())
