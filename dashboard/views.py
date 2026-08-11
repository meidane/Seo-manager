"""ویو داشبورد — قلب سیستم.

همه‌ی آمار با کوئری‌های تجمیعی (annotate/aggregate) و فیلترهای شرطی محاسبه
می‌شوند، نه حلقه‌ی پایتونی روی رکوردها. بازه‌ی زمانی سراسری روی همه اثر دارد.

هینت تکمیل (گام‌های بعد):
- تب‌های امروز/دیروز/۷روز جدول همکاران فعلاً بازه‌ی جاری را نشان می‌دهند؛
  برای AJAX سبک یک endpoint در dashboard/urls اضافه کن که period بگیرد.
- کشوی جزئیات همکار (کلیک روی ردیف) هنوز نیست — یک API «تسک‌های همکار در روز X».
- نمودار دونات و هیت‌مپ ۱۲ هفته: داده‌شان اینجا آماده نشده؛ `tasks.queries.group_done_by_day`
  نمونه‌ی الگوی گروه‌بندیِ روزانه است. کارت مالی به FinanceEntry (گام ۸) وصل شود.
"""
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Max, Q, Sum
from django.views.generic import TemplateView

from colleagues.models import Colleague
from core.columns import get_columns
from core.daterange import DateRangeMixin
from core.models import ColumnConfig
from projects.access import accessible_project_ids
from projects.models import Project
from tasks.models import Task
from tasks.queries import group_done_by_day, reviewable_q


def _pct(cur, prev):
    """درصد تغییر نسبت به بازه‌ی قبل؛ None اگر مبنا صفر باشد."""
    if not prev:
        return None
    return round((cur - prev) / prev * 100)


class DashboardView(LoginRequiredMixin, DateRangeMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_range(self.request)
        pstart, pend = self.get_previous_range()
        today = date.today()
        ctx.update(self.range_context())

        # دسترسیِ پروژه‌محور: فقط مالکِ سازمان همه را می‌بیند؛ بقیه فقط پروژه‌هایی که
        # عضوشان هستند — همه‌جای داشبورد یکسان اعمال می‌شود (کارت‌ها/هشدار/جدول‌ها).
        ids = accessible_project_ids(self.request)
        task_qs = Task.objects.filter(project_id__in=ids) if ids is not None else Task.objects.all()
        project_qs = Project.objects.filter(id__in=ids) if ids is not None else Project.objects.all()
        colleague_task_q = Q(tasks__project_id__in=ids) if ids is not None else Q()

        done_q = Q(status=Task.DONE, done_date__range=(start, end))
        prev_done_q = Q(status=Task.DONE, done_date__range=(pstart, pend))
        open_q = Q(status__in=[Task.TODO, Task.DOING])

        # ── ردیف ۱: کارت‌های وضعیت ──
        done_count = task_qs.filter(done_q).count()
        prev_done = task_qs.filter(prev_done_q).count()
        remaining = task_qs.filter(open_q, planned_date__range=(start, end)).count()
        overdue = task_qs.filter(open_q, planned_date__lt=today).count()
        minutes = task_qs.filter(done_q).aggregate(s=Sum('spent_minutes'))['s'] or 0
        prev_minutes = task_qs.filter(prev_done_q).aggregate(s=Sum('spent_minutes'))['s'] or 0

        ctx['cards'] = {
            'done': done_count, 'done_pct': _pct(done_count, prev_done),
            'remaining': remaining, 'overdue': overdue,
            'minutes': minutes, 'minutes_pct': _pct(minutes, prev_minutes),
            'balance': 0,  # هینت: از FinanceEntry (گام ۸) محاسبه شود
        }

        # ── ردیف ۲: نوار هشدارها ──
        projects_with_plan = set(
            task_qs.filter(planned_date__range=(start, end))
            .values_list('project_id', flat=True)
        )
        active_ids = set(project_qs.filter(status=Project.ACTIVE).values_list('id', flat=True))
        no_plan = len(active_ids - projects_with_plan)
        done_no_link = task_qs.filter(done_q, published_url='').count()
        unreviewed = task_qs.filter(
            status=Task.DONE, review_status=Task.UNREVIEWED).filter(reviewable_q(self.request)).count()

        ctx['alerts'] = {'overdue': overdue, 'no_plan': no_plan,
                         'done_no_link': done_no_link, 'unreviewed': unreviewed}

        # ── ردیف ۳: جدول وضعیت پروژه‌ها (یک کوئری با annotate شرطی) ──
        projects = list(project_qs.filter(status=Project.ACTIVE).annotate(
            planned=Count('tasks', filter=Q(tasks__planned_date__range=(start, end))),
            done=Count('tasks', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            words=Sum('tasks__word_count', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            minutes=Sum('tasks__spent_minutes', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            overdue=Count('tasks', filter=Q(tasks__status__in=[Task.TODO, Task.DOING], tasks__planned_date__lt=today)),
            last_activity=Max('tasks__updated_at'),
            last_report=Max('reports__date_to'),
        ))
        for p in projects:
            p.remaining = max(p.planned - p.done, 0)
            p.progress = round(p.done / p.planned * 100) if p.planned else 0
            # وضعیت: بدون کار / عقب‌افتاده / عقب / روی روال / جلوتر
            if p.planned == 0:
                p.state = ('bad', 'بدون کار')
            elif p.overdue:
                p.state = ('bad', 'عقب‌افتاده')
            elif p.progress < 60:
                p.state = ('warn', 'عقب')
            elif p.progress < 100:
                p.state = ('ok', 'روی روال')
            else:
                p.state = ('info', 'جلوتر')
        # بدترین وضعیت بالا: بدون‌کار/عقب‌افتاده اول
        order = {'bad': 0, 'warn': 1, 'ok': 2, 'info': 3}
        projects.sort(key=lambda p: (order[p.state[0]], -p.overdue))
        ctx['projects'] = projects
        ctx['project_columns'] = get_columns(ColumnConfig.PROJECTS, ColumnConfig.DASHBOARD)

        # ── ردیف ۴ (راست): عملکرد همکاران در بازه ──
        colleagues = list(Colleague.objects.filter(status=Colleague.ACTIVE).annotate(
            planned=Count('tasks', filter=Q(tasks__planned_date__range=(start, end)) & colleague_task_q),
            done=Count('tasks', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end)) & colleague_task_q),
            words=Sum('tasks__word_count', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end)) & colleague_task_q),
            minutes=Sum('tasks__spent_minutes', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end)) & colleague_task_q),
            overdue=Count('tasks', filter=Q(tasks__status__in=[Task.TODO, Task.DOING], tasks__planned_date__lt=today) & colleague_task_q),
        ))
        ctx['colleagues'] = colleagues
        ctx['colleague_columns'] = get_columns(ColumnConfig.COLLEAGUES, ColumnConfig.DASHBOARD)

        # ── ردیف ۴ (چپ): فید بازبینی ──
        ctx['review_feed'] = task_qs.select_related('project', 'assignee').filter(
            status=Task.DONE, review_status=Task.UNREVIEWED
        ).filter(reviewable_q(self.request)).order_by('-done_date')[:8]

        # ── ردیف ۵: تسک‌های انجام‌شده به تفکیک روز — جدول (نه نمودار)، ۷ روز اخیر
        ctx['daily_groups'] = group_done_by_day(task_qs, today - timedelta(days=6), today)

        ctx['page_title'] = 'داشبورد'
        return ctx
