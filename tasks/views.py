"""ویوهای صفحه‌ای تسک‌ها — لیست/کانبان و بازبینی."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import TemplateView

from colleagues.models import Colleague
from core.columns import get_columns
from core.daterange import DateRangeMixin
from core.models import ColumnConfig
from projects.access import accessible_project_ids
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
        # دسترسیِ پروژه‌محور: فقط مالکِ سازمان همه را می‌بیند، بقیه فقط پروژه‌هایی که عضوشان هستند
        ids = accessible_project_ids(self.request)
        if ids is not None:
            base = base.filter(project_id__in=ids)
        # own_tasks_only: فقط تسک‌های خودش
        m = getattr(self.request, 'membership', None)
        if m and m.can('own_tasks_only'):
            colleague = getattr(self.request.user, 'colleague', None)
            base = base.filter(assignee_id=colleague.id if colleague else -1)
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
        visible_projects = Project.objects.filter(id__in=ids) if ids is not None else Project.objects.all()
        ctx['projects'] = visible_projects.filter(status=Project.ACTIVE)
        ctx['colleagues'] = Colleague.objects.filter(status=Colleague.ACTIVE)
        # همهٔ پروژه‌ها/همکاران برای دراپ‌داون‌های ویرایشِ زندهٔ جدول (نه فقط فعال)
        ctx['all_projects'] = visible_projects.order_by('status', 'name')
        ctx['all_colleagues'] = Colleague.objects.order_by('status', 'full_name')
        # انواعِ فعال (built-in عمومی + سفارشی) برای دراپ‌داونِ فیلتر «نوع»
        ctx['task_types'] = TaskTypeDef.objects.filter(is_active=True)
        ctx['status_choices'] = Task.STATUS_CHOICES
        # ستون‌های اضافیِ قابل‌سفارشی‌سازی (بعد از ستون‌های ثابت جدول) — /settings/columns/
        ctx['extra_columns'] = get_columns(ColumnConfig.TASKS, ColumnConfig.PAGE)
        ctx['page_title'] = 'تسک‌ها'
        ctx['filters'] = g
        # ویرایشِ مستقیمِ زمان فقط برای مدیران (نقش‌های دارای دسترسیِ review)
        ctx['can_edit_time'] = bool(m and m.can('review'))
        return ctx


class TaskReviewView(LoginRequiredMixin, TemplateView):
    """صفحه‌ی «بازبینی تسک» — دو مسیرِ مستقل:
    ۱) نوعِ تسک «نیاز به بازبینی» دارد (`TaskTypeDef.requires_review`) → صف‌ِ عمومی،
       فقط برای کسی که دسترسیِ سازمانیِ `review` دارد.
    ۲) همکار «نیاز به بازبینیِ مدیرش» دارد (`Colleague.needs_review`) → فقط برای
       همان مدیرِ مشخص‌شده دیده می‌شود، مستقل از دسترسیِ `review` (تعیینِ مدیر خودش
       یعنی اجازه‌ی بازبینیِ کارِ او)."""

    template_name = 'tasks/review.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        m = getattr(self.request, 'membership', None)
        managed_q = Q(assignee__needs_review=True, assignee__manager__user=self.request.user)
        q = managed_q
        if m and m.can('review'):
            q |= Q(type_def__requires_review=True)
        qs = Task.objects.select_related('project', 'assignee', 'type_def').filter(
            status=Task.DONE).filter(q)
        review = self.request.GET.get('review', 'unreviewed')
        if review == 'unreviewed':
            qs = qs.filter(review_status=Task.UNREVIEWED)
        ctx['tasks'] = qs.order_by('-done_date')[:50]
        ctx['review'] = review
        ctx['page_title'] = 'بازبینی تسک'
        return ctx
