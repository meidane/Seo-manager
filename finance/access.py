"""دسترسیِ حسابداری — همه‌ی ویوها/APIهای این اپ با `manage_finance` گیت می‌شوند."""
from functools import wraps

from accounts.access import require_perm


def require_finance(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        require_perm(request, 'manage_finance')
        return view(request, *args, **kwargs)
    return wrapper


class FinancePermMixin:
    """بعد از `LoginRequiredMixin` بگذار تا کاربرِ مهمان اول به لاگین ریدایرکت شود،
    نه ۴۰۳ بگیرد."""

    def dispatch(self, request, *args, **kwargs):
        require_perm(request, 'manage_finance')
        return super().dispatch(request, *args, **kwargs)
