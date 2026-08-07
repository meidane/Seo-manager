"""ویوهای صفحه‌ای تسک‌ها — لیست/کانبان و بازبینی."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import TemplateView

from colleagues.models import Colleague
from core.daterange import DateRangeMixin
from projects.models import Project

from .models import Task


class TaskListView(LoginRequiredMixin, DateRangeMixin, TemplateView):
    """لیست + کانبان با فیلترها. بازه‌ی زمانی سراسری روی planned_date اعمال می‌شود."""

    template_name = 'tasks/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_range(self.request)
        g = self.request.GET

        qs = Task.objects.select_related('project', 'assignee', 'type_def')
        # بازه فقط وقتی اعمال شود که کاربر «همه» را نخواسته باشد
        if g.get('all') != '1':
            qs = qs.filter(planned_date__range=(start, end))

        if g.get('project'):
            qs = qs.filter(project_id=g['project'])
        if g.get('assignee'):
            qs = qs.filter(assignee_id=g['assignee'])
        if g.get('type'):
            qs = qs.filter(task_type=g['type'])
        if g.get('status'):
            qs = qs.filter(status=g['status'])
        if g.get('priority'):
            qs = qs.filter(priority=g['priority'])
        if g.get('review'):
            qs = qs.filter(review_status=g['review'])
        if g.get('overdue') == '1':
            from datetime import date
            qs = qs.filter(status__in=[Task.TODO, Task.DOING], planned_date__lt=date.today())
        if g.get('q'):
            qs = qs.filter(title__icontains=g['q'])

        ctx.update(self.range_context())
        ctx['tasks'] = qs
        ctx['kanban'] = {
            'todo': qs.filter(status=Task.TODO),
            'doing': qs.filter(status=Task.DOING),
            'done': qs.filter(status=Task.DONE),
            'cancelled': qs.filter(status=Task.CANCELLED),
        }
        ctx['projects'] = Project.objects.filter(status=Project.ACTIVE)
        ctx['colleagues'] = Colleague.objects.filter(status=Colleague.ACTIVE)
        ctx['type_choices'] = Task.TYPE_CHOICES
        ctx['status_choices'] = Task.STATUS_CHOICES
        ctx['page_title'] = 'تسک‌ها'
        ctx['filters'] = g
        return ctx


class TaskReviewView(LoginRequiredMixin, TemplateView):
    """صفحه‌ی بازبینی محتوا — فقط تسک‌های انجام‌شده‌ی دارای لینک."""

    template_name = 'tasks/review.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = Task.objects.select_related('project', 'assignee', 'type_def').filter(
            status=Task.DONE).exclude(published_url='')
        review = self.request.GET.get('review', 'unreviewed')
        if review == 'unreviewed':
            qs = qs.filter(review_status=Task.UNREVIEWED)
        ctx['tasks'] = qs.order_by('-done_date')[:50]
        ctx['review'] = review
        ctx['page_title'] = 'بازبینی محتوا'
        return ctx
