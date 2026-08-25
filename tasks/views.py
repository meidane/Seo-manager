"""ویوهای صفحه‌ای تسک‌ها — لیست/کانبان و بازبینی."""
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from colleagues.models import Colleague
from core.columns import get_columns
from core.daterange import DateRangeMixin
from core.models import ColumnConfig
from projects.access import accessible_project_ids
from projects.models import Project

from .api import can_manage_any_timer
from .models import Task, TaskTypeDef
from .queries import PAGE_SIZE, build_task_queryset, group_done_by_day, reviewable_q

# سقفِ دفاعی برای جعبه‌های «این هفته/عقب‌افتاده» و «آینده» — این دو لودِ تنبل ندارند
# (طبیعتاً محدودند: بارِ کاریِ نزدیک، نه کلِ تاریخچه)؛ فقط جعبه‌ی «انجام‌شده» صفحه‌بندی دارد.
BOX_CAP = 300


class TaskListView(LoginRequiredMixin, DateRangeMixin, TemplateView):
    """لیست + کانبان با فیلترها. دیدِ پیش‌فرض سه جعبه است (این‌هفته+عقب‌افتاده / آینده /
    انجام‌شده)، مستقل از بازه‌ی سراسری — `?group=day` تفکیکِ روزانه‌ی جداست."""

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
        ctx['has_more_done'] = False
        if ctx['grouped_by_day']:
            # «مشاهده‌ی همه» از داشبورد (تسک‌های انجام‌شده به تفکیک روز) — همان بازه‌ی
            # سراسری، ولی روی done_date گروه‌بندی می‌شود، نه planned_date.
            ctx['day_groups'] = group_done_by_day(base, start, end)
            ctx['box_recent'] = ctx['box_future'] = ctx['box_done'] = []
        else:
            today = date.today()
            week_end = today + timedelta(days=6)
            not_done = base.exclude(status=Task.DONE)
            # جعبه‌ی ۱: این‌هفته + عقب‌افتاده‌ها (هر چقدر قدیمی)، قدیمی‌ترین/عقب‌افتاده‌ترین اول
            # ترتیب: نزدیک‌ترین تاریخ/عقب‌افتاده اول؛ در هر روز (مثلِ امروز) جدیدترین بالا
            ctx['box_recent'] = list(not_done.filter(planned_date__lte=week_end).order_by(
                'planned_date', 'planned_time', '-created_at', '-id')[:BOX_CAP])
            # جعبه‌ی ۲: آینده، بیش از ۱ هفته — نزدیک‌ترین تاریخ اول
            ctx['box_future'] = list(not_done.filter(planned_date__gt=week_end).order_by(
                'planned_date', 'planned_time', 'id')[:BOX_CAP])
            # جعبه‌ی ۳: انجام‌شده‌ها — جدیدترین اول، لودِ تنبل (تاریخچه می‌تواند خیلی بزرگ شود)
            done_qs = base.filter(status=Task.DONE).order_by('-done_date', '-id')
            ctx['box_done'] = list(done_qs[:PAGE_SIZE])
            ctx['has_more_done'] = done_qs[PAGE_SIZE:PAGE_SIZE + 1].exists()
            # سطلِ زباله: تسک‌های حذف‌شده، آخرِ همه — فقط برای کسی که می‌تواند حذف/بازیابی کند
            ctx['box_deleted'] = []
            if m and m.can('delete_task'):
                del_qs = Task.objects.deleted().select_related('project', 'assignee', 'type_def', 'deleted_by').prefetch_related('type_def__fields')
                if ids is not None:
                    del_qs = del_qs.filter(project_id__in=ids)
                ctx['box_deleted'] = list(del_qs.order_by('-deleted_at')[:100])
        visible_projects = Project.objects.filter(id__in=ids) if ids is not None else Project.objects.all()
        ctx['projects'] = visible_projects.filter(status=Project.ACTIVE)
        ctx['colleagues'] = Colleague.objects.filter(status=Colleague.ACTIVE)
        # همهٔ پروژه‌ها/همکاران برای دراپ‌داون‌های ویرایشِ زندهٔ جدول (نه فقط فعال)
        ctx['all_projects'] = visible_projects.order_by('status', 'name')
        ctx['all_colleagues'] = Colleague.objects.order_by('status', 'full_name')
        # انواعِ فعال (built-in عمومی + سفارشی) برای دراپ‌داونِ فیلتر «نوع» + ویرایشِ زندهٔ نوع در ردیف
        ctx['task_types'] = TaskTypeDef.objects.filter(is_active=True)
        ctx['all_types'] = ctx['task_types']
        ctx['status_choices'] = Task.STATUS_CHOICES
        ctx['report_months'] = Task.REPORT_MONTH_CHOICES
        # ستون‌های اضافیِ قابل‌سفارشی‌سازی (بعد از ستون‌های ثابت جدول) — /settings/columns/.
        # عمومی همیشه؛ فیلدهای سفارشیِ نوع فقط وقتی همان نوع فیلتر شده (وگرنه جدول شلوغ می‌شود).
        from core.columns import visible_task_columns
        ctx['extra_columns'] = visible_task_columns(filters.get('type_def'))
        ctx['page_title'] = 'تسک‌ها'
        ctx['filters'] = filters
        # ویرایشِ دستیِ عددِ زمانِ دیگران: پرمیشنِ edit_time (تنظیم‌شدنی در نقش‌ها)
        ctx['can_edit_time'] = bool(m and m.can('edit_time'))
        # استارت/استاپِ تایمرِ تسکِ دیگران (نه فقط ویرایشِ دستیِ عدد) — edit_time یا
        # edit_task-بدونِ-own_tasks_only؛ دکمه‌ی ▶ روی تسکِ دیگران را همین گیت می‌کند.
        ctx['can_manage_any_timer'] = can_manage_any_timer(m)
        # own_tasks_only از قبل لیست را به تسک‌های خودش محدود کرده؛ پس این‌جا فقط چکِ
        # سطحِ سازمانی کافی است — اگر می‌بیندش، یعنی مالِ خودش است (یا own_tasks_only ندارد)
        ctx['can_edit_task'] = bool(m and m.can('edit_task'))
        ctx['my_colleague_id'] = my_colleague.id if my_colleague else None
        # ویرایشِ inline فقط وقتی یک نوعِ تسک فیلتر شده (حالتِ «همهٔ انواع» فقط‌خواندنیِ
        # ستون‌های اصلی است) — قاعدهٔ ساده‌سازیِ درخواستیِ کاربر.
        ctx['editable'] = ctx['can_edit_task'] and bool(filters.get('type_def'))
        return ctx


class TaskReviewView(LoginRequiredMixin, TemplateView):
    """صفحه‌ی «بازبینی تسک» — دو مسیرِ مستقل:
    ۱) نوعِ تسک «نیاز به بازبینی» دارد (`TaskTypeDef.requires_review`) → صفِ عمومی
       (تسکِ `status=done`)، فقط برای کسی که دسترسیِ سازمانیِ `review` دارد.
    ۲) خودِ تسک «نیاز به بازبینی» دارد (`Task.needs_review`) → تسک در وضعیتِ
       `status=pending` («تکمیل — در انتظارِ بازبینی») می‌ماند، نه `done`؛ برای کلِّ
       زنجیره‌ی مدیریتیِ بالادست (نه فقط مدیرِ مستقیم) یا هرکسی با دسترسیِ سازمانیِ
       `review` دیده می‌شود (`tasks.queries.reviewable_q`)."""

    template_name = 'tasks/review.html'

    def get_context_data(self, **kwargs):
        from colleagues.access import all_subordinate_ids

        ctx = super().get_context_data(**kwargs)
        qs = Task.objects.select_related('project', 'assignee', 'type_def').filter(
            status__in=[Task.DONE, Task.PENDING]).filter(reviewable_q(self.request))
        review = self.request.GET.get('review', 'unreviewed')
        if review == 'unreviewed':
            qs = qs.filter(review_status=Task.UNREVIEWED)
        tasks = list(qs.order_by('-updated_at')[:50])

        # «مسئولیتِ خودم» (مسئولِ تسک زیرمجموعه‌ی من است، در هر عمقی) در برابرِ «فقط
        # نظارتِ سازمانی» (فقط به‌خاطرِ دسترسیِ سازمانیِ review دیده می‌شود، مسئولش
        # مدیرِ دیگری است) — اولی همیشه بالاتر می‌آید و در تمپلیت متمایز نشان داده می‌شود.
        my_colleague = getattr(self.request.user, 'colleague', None)
        sub_ids = all_subordinate_ids(my_colleague)
        for t in tasks:
            t.is_my_scope = t.assignee_id in sub_ids
        tasks.sort(key=lambda t: not t.is_my_scope)

        ctx['tasks'] = tasks
        ctx['review'] = review
        ctx['page_title'] = 'بازبینی تسک'
        return ctx
