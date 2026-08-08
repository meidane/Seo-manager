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

# کلیدهای دسترسی (قابل‌گسترش)
PERMS = [
    'manage_org',       # ویرایش سازمان و تیم‌ها
    'manage_people',    # افزودن/ویرایش اعضا و نقش‌ها
    'manage_projects',  # پروژه‌ها
    'manage_tasks',     # تسک‌ها
    'manage_finance',   # حسابداری
    'review',           # بازبینی/تایید محتوا
    'view_reports',     # مشاهده‌ی گزارش‌ها
]

PERM_LABELS = {
    'manage_org': 'مدیریت سازمان و تیم‌ها',
    'manage_people': 'مدیریت افراد و دسترسی‌ها',
    'manage_projects': 'مدیریت پروژه‌ها',
    'manage_tasks': 'مدیریت تسک‌ها',
    'manage_finance': 'مدیریت حسابداری',
    'review': 'بازبینی و تایید',
    'view_reports': 'مشاهده‌ی گزارش‌ها',
}

# نگاشتِ نقش → مجموعه‌ی دسترسی‌ها
ROLE_PERMS = {
    OWNER: set(PERMS),
    ADMIN: set(PERMS),
    MANAGER: {'manage_projects', 'manage_tasks', 'review', 'view_reports'},
    MEMBER: {'manage_tasks', 'view_reports'},
    VIEWER: {'view_reports'},
}


def role_can(role: str, perm: str) -> bool:
    return perm in ROLE_PERMS.get(role, set())


def role_perms(role: str) -> set:
    return ROLE_PERMS.get(role, set())
