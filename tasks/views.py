"""ویوهای صفحه‌ای تسک‌ها — لیست/کانبان و بازبینی."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from colleagues.models import Colleague
from core.columns import get_columns
from core.daterange import DateRangeMixin
from core.models import ColumnConfig
from projects.access import accessible_project_ids
from projects.models import Project

from .models import Task, TaskTypeDef
from .queries import PAGE_SIZE, build_task_queryset, group_done_by_day, reviewable_q


class TaskListView(LoginRequiredMixin, DateRangeMixin, TemplateView):
    """لیست + کانبان با فیلترها. بازه‌ی زمانی سراسری روی planned_date اعمال می‌شود."""

    template_name = 'tasks/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_range(self.request)
        g = self.request.GET
        m = getattr(self.request, 'membership', None)
        my_colleague = getattr(self.request.user, 'colleague', None)

        base, filters = build_task_queryset(self.request)
        ids = accessible_project_ids(self.request)

        ctx.update(self.range_context())
        ctx['grouped_by_day'] = g.get('group') == 'day'
        ctx['has_more'] = False
        if ctx['grouped_by_day']:
            # «مشاهده‌ی همه» از داشبورد (تسک‌های انجام‌شده به تفکیک روز) — همان بازه‌ی
            # سراسری، ولی روی done_date گروه‌بندی می‌شود، نه planned_date.
            ctx['day_groups'] = group_done_by_day(base, start, end)
            ctx['tasks'] = []
            ctx['future_tasks'] = []
        else:
            if g.get('all') == '1':
                ranged = base.order_by('planned_date', 'planned_time', 'id')
                ctx['future_tasks'] = []
            else:
                ranged = base.filter(planned_date__range=(start, end)).order_by(
                    'planned_date', 'planned_time', 'id')
                # #۳: تسک‌های آینده (پس از پایانِ بازه، هنوز انجام‌نشده) در انتهای لیست
                ctx['future_tasks'] = base.filter(planned_date__gt=end).exclude(
                    status=Task.DONE).order_by('planned_date', 'planned_time')[:100]
            # لودِ تنبل: صفحه‌ی اول ۵۰ تا؛ بقیه با اسکرول از api.task_rows_page می‌آید
            ctx['tasks'] = list(ranged[:PAGE_SIZE])
            ctx['has_more'] = ranged[PAGE_SIZE:PAGE_SIZE + 1].exists()
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
        ctx['filters'] = filters
        # ویرایشِ مستقیمِ زمانِ دیگران: پرمیشنِ جداگانه‌ی edit_time (تنظیم‌شدنی در نقش‌ها)
        ctx['can_edit_time'] = bool(m and m.can('edit_time'))
        # own_tasks_only از قبل لیست را به تسک‌های خودش محدود کرده؛ پس این‌جا فقط چکِ
        # سطحِ سازمانی کافی است — اگر می‌بیندش، یعنی مالِ خودش است (یا own_tasks_only ندارد)
        ctx['can_edit_task'] = bool(m and m.can('edit_task'))
        ctx['my_colleague_id'] = my_colleague.id if my_colleague else None
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
        qs = Task.objects.select_related('project', 'assignee', 'type_def').filter(
            status=Task.DONE).filter(reviewable_q(self.request))
        review = self.request.GET.get('review', 'unreviewed')
        if review == 'unreviewed':
            qs = qs.filter(review_status=Task.UNREVIEWED)
        ctx['tasks'] = qs.order_by('-done_date')[:50]
        ctx['review'] = review
        ctx['page_title'] = 'بازبینی تسک'
        return ctx
