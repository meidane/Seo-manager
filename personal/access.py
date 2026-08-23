"""گیتِ دسترسیِ فضای شخصی — فقط سوپریوزر (کاربرِ `admin`).

داده‌ی شخصی است؛ برای مخفی‌ماندنِ وجودِ صفحه، به‌جای ۴۰۳، ۴۰۴ می‌دهیم (کسی که
دسترسی ندارد اصلاً نباید بفهمد چنین صفحه‌ای هست). علاوه بر این گیت، همه‌ی کوئری‌ها
هم به `user=request.user` اسکوپ‌اند تا حتی سوپریوزرِ دیگری هم دادهٔ کسی را نبیند.
"""
from functools import wraps

from django.http import Http404


def _is_admin(user):
    return bool(user and user.is_authenticated and user.is_superuser)


def admin_only(view):
    """دکوریتورِ ویو/API — اگر سوپریوزر نبود، ۴۰۴."""
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not _is_admin(request.user):
            raise Http404
        return view(request, *args, **kwargs)
    return _wrapped
