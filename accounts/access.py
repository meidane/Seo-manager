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
