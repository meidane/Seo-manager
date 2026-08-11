"""نقش‌ها و دسترسی‌های سازمانی — نسخه‌ی ساده (بعداً granular per-resource می‌شود).

هر عضو در یک سازمان یک «نقش» دارد و هر نقش مجموعه‌ای از «دسترسی» (permission flag).
این‌جا فقط تعریفِ داده است؛ منطقِ بررسی در `Membership.can()` و context_processor.
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

# کلیدهای دسترسی (قابل‌گسترش) — نقش سفارشی می‌تواند هر ترکیبی از این‌ها را داشته باشد
PERMS = [
    'manage_org',        # ویرایش سازمان و تیم‌ها
    'manage_people',     # افزودن/ویرایش اعضا و نقش‌ها (کاربرانِ لاگین‌کننده)
    'manage_projects',   # افزودن/ویرایش پروژه
    'manage_colleagues',  # افزودن/ویرایش همکار (پروفایلِ CRM، جدا از کاربرِ لاگین)
    'edit_task',          # ویرایش تسک
    'delete_task',        # حذف تسک
    'own_tasks_only',     # فقط تسک‌های خودش را ببیند (محدودکننده، نه افزاینده)
    'manage_finance',     # دسترسی به حسابداری
    'manage_task_types',  # مدیریتِ انواع تسک
    'manage_columns',     # سفارشی‌سازیِ ستون‌ها
    'manage_holidays',    # مدیریتِ تعطیلات
    'review',             # بازبینی/تایید تسک
    'edit_time',          # ویرایشِ مستقیمِ زمانِ کارکردِ دیگران (+ استارت/استاپِ تایمرِ هرکس)
    'view_reports',       # مشاهده‌ی گزارش‌ها
]

PERM_LABELS = {
    'manage_org': 'مدیریت سازمان و تیم‌ها',
    'manage_people': 'مدیریت افراد و دسترسی‌ها',
    'manage_projects': 'افزودن/ویرایش پروژه',
    'manage_colleagues': 'افزودن/ویرایش همکار',
    'edit_task': 'ویرایش تسک',
    'delete_task': 'حذف تسک',
    'own_tasks_only': 'فقط تسک‌های خودش را ببیند',
    'manage_finance': 'دسترسی به حسابداری',
    'manage_task_types': 'مدیریتِ انواع تسک',
    'manage_columns': 'سفارشی‌سازیِ ستون‌ها',
    'manage_holidays': 'مدیریتِ تعطیلات',
    'review': 'بازبینی و تایید تسک',
    'edit_time': 'ویرایشِ زمانِ کارکردِ دیگران',
    'view_reports': 'مشاهده‌ی گزارش‌ها',
}

# نگاشتِ نقش → مجموعه‌ی دسترسی‌ها (پیش‌فرضِ اولیه؛ هر سازمان می‌تواند از تنظیمات عوضش کند)
_ALL_BUT_SCOPE = set(PERMS) - {'own_tasks_only'}
ROLE_PERMS = {
    OWNER: set(PERMS),
    ADMIN: set(_ALL_BUT_SCOPE),
    MANAGER: {'manage_projects', 'manage_colleagues', 'edit_task', 'delete_task', 'review', 'edit_time', 'view_reports'},
    MEMBER: {'edit_task', 'own_tasks_only', 'view_reports'},
    VIEWER: {'view_reports'},
}


def role_can(role: str, perm: str) -> bool:
    return perm in ROLE_PERMS.get(role, set())


def role_perms(role: str) -> set:
    return ROLE_PERMS.get(role, set())


# کلیدهایی که به یکی از تب‌های «تنظیمات» راه دارند — برای گیتِ لینکِ واحدِ سایدبار/
# دسترسیِ صفحه‌ی هاب (`accounts:settings_home`)، نه یک صفحه‌ی مشخص.
SETTINGS_PERMS = ('manage_org', 'manage_people', 'manage_task_types', 'manage_columns', 'manage_holidays')
