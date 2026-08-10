"""ویوهای صفحه‌ای تسک‌ها — لیست/کانبان و بازبینی."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import TemplateView

from colleagues.models import Colleague
from core.columns import get_columns
from core.daterange import DateRangeMixin
from core.models import ColumnConfig
from projects.models import Project

from .models import Task, TaskTypeDef


class TaskListView(LoginRequiredMixin, DateRangeMixin, TemplateView):
    """لیست + کانبان با فیلترها. بازه‌ی زمانی سراسری روی planned_date اعمال می‌شود."""

    template_name = 'tasks/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_range(self.request)
        g = self.request.GET

        # پیش‌نماهای تکرار (placeholder) فقط در تقویم دیده می‌شوند، نه در لیست
        base = Task.objects.filter(is_placeholder=False).select_related('project', 'assignee', 'type_def')
        # فیلترهای غیر-تاریخی (روی همه اعمال می‌شوند)
        if g.get('project'):
            base = base.filter(project_id=g['project'])
        if g.get('assignee'):
            base = base.filter(assignee_id=g['assignee'])
        if g.get('type_def'):
            base = base.filter(type_def_id=g['type_def'])
        elif g.get('type'):  # سازگاری با لینک‌های قدیمی (نوع built-inِ خام)
            base = base.filter(task_type=g['type'])
        if g.get('status'):
            base = base.filter(status=g['status'])
        if g.get('priority'):
            base = base.filter(priority=g['priority'])
        if g.get('review'):
            base = base.filter(review_status=g['review'])
        if g.get('overdue') == '1':
            from datetime import date
            base = base.filter(status__in=[Task.TODO, Task.DOING], planned_date__lt=date.today())
        if g.get('q'):
            base = base.filter(title__icontains=g['q'])

        ctx.update(self.range_context())
        if g.get('all') == '1':
            ctx['tasks'] = base
            ctx['future_tasks'] = []
        else:
            ctx['tasks'] = base.filter(planned_date__range=(start, end))
            # #۳: تسک‌های آینده (پس از پایانِ بازه، هنوز انجام‌نشده) در انتهای لیست
            ctx['future_tasks'] = base.filter(planned_date__gt=end).exclude(
                status=Task.DONE).order_by('planned_date', 'planned_time')[:100]
        ctx['projects'] = Project.objects.filter(status=Project.ACTIVE)
        ctx['colleagues'] = Colleague.objects.filter(status=Colleague.ACTIVE)
        # همهٔ پروژه‌ها/همکاران برای دراپ‌داون‌های ویرایشِ زندهٔ جدول (نه فقط فعال)
        ctx['all_projects'] = Project.objects.order_by('status', 'name')
        ctx['all_colleagues'] = Colleague.objects.order_by('status', 'full_name')
        # انواعِ فعال (built-in عمومی + سفارشی) برای دراپ‌داونِ فیلتر «نوع»
        ctx['task_types'] = TaskTypeDef.objects.filter(is_active=True)
        ctx['status_choices'] = Task.STATUS_CHOICES
        # ستون‌های اضافیِ قابل‌سفارشی‌سازی (بعد از ستون‌های ثابت جدول) — /settings/columns/
        ctx['extra_columns'] = get_columns(ColumnConfig.TASKS, ColumnConfig.PAGE)
        ctx['page_title'] = 'تسک‌ها'
        ctx['filters'] = g
        # ویرایشِ مستقیمِ زمان فقط برای مدیران (نقش‌های دارای دسترسیِ review)
        m = getattr(self.request, 'membership', None)
        ctx['can_edit_time'] = bool(m and m.can('review'))
        return ctx


class TaskReviewView(LoginRequiredMixin, TemplateView):
    """صفحه‌ی بازبینی محتوا — فقط تسک‌های انجام‌شده‌ی دارای لینک."""

    template_name = 'tasks/review.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # فقط تسک‌های انجام‌شده‌ای که نوعشان «نیاز به بازبینی» دارد
        qs = Task.objects.select_related('project', 'assignee', 'type_def').filter(
            status=Task.DONE, type_def__requires_review=True)
        review = self.request.GET.get('review', 'unreviewed')
        if review == 'unreviewed':
            qs = qs.filter(review_status=Task.UNREVIEWED)
        ctx['tasks'] = qs.order_by('-done_date')[:50]
        ctx['review'] = review
        ctx['page_title'] = 'بازبینی محتوا'
        return ctx
