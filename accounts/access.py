"""بررسیِ دسترسیِ سازمانی — منبعِ واحد، از هر اپی قابل‌استفاده (نه فقط accounts).

`require_perm` جایگزینِ `accounts.views._require` است (که برای سازگاری همچنان alias
می‌ماند)؛ سایرِ اپ‌ها (colleagues, tasks, core) مستقیم از همین‌جا وارد کنند.
"""
from django.core.exceptions import PermissionDenied


def require_perm(request, perm):
    """سازمانِ جاری را برمی‌گرداند یا اگر دسترسی نبود، 403 (`PermissionDenied`)."""
    m = getattr(request, 'membership', None)
    if not m or not m.can(perm):
        raise PermissionDenied('دسترسی کافی نداری')
    return m.organization


def has_perm(request, perm):
    m = getattr(request, 'membership', None)
    return bool(m and m.can(perm))


def is_elevated_role(org, role_key):
    """این نقش «سطحِ‌بالا» است — یعنی خودش می‌تواند مدیریتِ افراد/سازمان را در دست
    بگیرد (`manage_people`/`manage_org`) یا مالک/مدیرِ کل (built-in) است؟ برای گیتِ
    «مدیرِ scoped حق ندارد نقشی بالاتر از خودش به کسی بدهد» (`colleagues/views.py:
    _grant_access`) — کسی که فقط به‌خاطرِ زیرمجموعه‌داشتن (نه `manage_people`) اجازه‌ی
    دادنِ دسترسی دارد، نباید بتواند برای زیردستش نقشِ مدیرِ کل بسازد."""
    from .permissions import ADMIN, OWNER

    if role_key in (OWNER, ADMIN):
        return True
    role = org.roles.filter(key=role_key).first()
    if not role:
        return True  # نقشِ ناشناخته/نامعتبر → محتاطانه مسدود
    perms = set(role.perms or [])
    return 'manage_people' in perms or 'manage_org' in perms
