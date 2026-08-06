"""ویوهای core — فعلاً صفحه‌ی مدیریت تعطیلات."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from .models import Holiday


class HolidayListView(LoginRequiredMixin, ListView):
    """صفحه‌ی مدیریت تعطیلات `/settings/holidays/`.

    فعلاً فقط فهرست را نمایش می‌دهد؛ افزودن/حذف دستی در گام‌های بعد کامل می‌شود.
    """

    model = Holiday
    template_name = 'settings/holidays.html'
    context_object_name = 'holidays'
    paginate_by = 50
