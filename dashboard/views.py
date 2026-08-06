"""ویو داشبورد — قلب سیستم.

در این گام فقط اسکلت صفحه با بازه‌ی زمانی سراسری رندر می‌شود؛ کوئری‌های
تجمیعی و کارت‌های آماری در گام داشبورد کامل می‌شوند.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from core.daterange import DateRangeMixin


class DashboardView(LoginRequiredMixin, DateRangeMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.get_range(self.request)
        context.update(self.range_context())
        context['page_title'] = 'داشبورد'
        return context
