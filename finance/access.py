"""دسترسیِ حسابداری — اغلبِ ویوها/APIها با `manage_finance` گیت می‌شوند.

استثنا: مشاهده‌ی فاکتورها و گزارشِ مالیِ پروژه با `view_invoices` **یا** `manage_finance`
(فقط دیدن). ساخت/ویرایشِ فاکتور همچنان `manage_finance` می‌خواهد.
"""
from django.core.exceptions import PermissionDenied
from functools import wraps

from accounts.access import has_perm, require_perm


def require_finance(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        require_perm(request, 'manage_finance')
        return view(request, *args, **kwargs)
    return wrapper


def can_view_invoices(request):
    """اجازه‌ی فقط-خواندنِ فاکتور/گزارشِ مالی: `manage_finance` یا `view_invoices`."""
    return has_perm(request, 'manage_finance') or has_perm(request, 'view_invoices')


def require_invoice_view(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not can_view_invoices(request):
            raise PermissionDenied('دسترسی کافی نداری')
        return view(request, *args, **kwargs)
    return wrapper


class FinancePermMixin:
    """بعد از `LoginRequiredMixin` بگذار تا کاربرِ مهمان اول به لاگین ریدایرکت شود،
    نه ۴۰۳ بگیرد."""

    def dispatch(self, request, *args, **kwargs):
        require_perm(request, 'manage_finance')
        return super().dispatch(request, *args, **kwargs)


class InvoiceViewPermMixin:
    """گیتِ فقط-خواندنِ فاکتور: `manage_finance` یا `view_invoices`.

    `can_edit_finance` را هم به context می‌گذارد تا تمپلیت دکمه‌های ویرایش/ساخت را برای
    کاربرِ فقط-بیننده پنهان کند."""

    def dispatch(self, request, *args, **kwargs):
        if not can_view_invoices(request):
            raise PermissionDenied('دسترسی کافی نداری')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['can_edit_finance'] = has_perm(self.request, 'manage_finance')
        return ctx
