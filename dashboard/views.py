"""ویو داشبورد — قلب سیستم.

همه‌ی آمار با کوئری‌های تجمیعی (annotate/aggregate) و فیلترهای شرطی محاسبه
می‌شوند، نه حلقه‌ی پایتونی روی رکوردها. بازه‌ی زمانی سراسری روی همه اثر دارد.

هینت تکمیل (گام‌های بعد):
- تب‌های امروز/دیروز/۷روز جدول همکاران فعلاً بازه‌ی جاری را نشان می‌دهند؛
  برای AJAX سبک یک endpoint در dashboard/urls اضافه کن که period بگیرد.
- کشوی جزئیات همکار (کلیک روی ردیف) هنوز نیست — یک API «تسک‌های همکار در روز X».
- نمودار دونات، هیت‌مپ ۱۲ هفته و اسپارک‌لاین همکاران: داده‌شان اینجا آماده
  نشده؛ متد _daily_series نمونه‌ی الگوست. کارت مالی به FinanceEntry (گام ۸) وصل شود.
"""
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Max, Q, Sum
from django.views.generic import TemplateView

from colleagues.models import Colleague
from core.daterange import DateRangeMixin
from projects.models import Project
from tasks.models import Task


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

        done_q = Q(status=Task.DONE, done_date__range=(start, end))
        prev_done_q = Q(status=Task.DONE, done_date__range=(pstart, pend))
        open_q = Q(status__in=[Task.TODO, Task.DOING])

        # ── ردیف ۱: کارت‌های وضعیت ──
        done_count = Task.objects.filter(done_q).count()
        prev_done = Task.objects.filter(prev_done_q).count()
        remaining = Task.objects.filter(open_q, planned_date__range=(start, end)).count()
        overdue = Task.objects.filter(open_q, planned_date__lt=today).count()
        minutes = Task.objects.filter(done_q).aggregate(s=Sum('estimate_minutes'))['s'] or 0
        prev_minutes = Task.objects.filter(prev_done_q).aggregate(s=Sum('estimate_minutes'))['s'] or 0

        ctx['cards'] = {
            'done': done_count, 'done_pct': _pct(done_count, prev_done),
            'remaining': remaining, 'overdue': overdue,
            'minutes': minutes, 'minutes_pct': _pct(minutes, prev_minutes),
            'balance': 0,  # هینت: از FinanceEntry (گام ۸) محاسبه شود
        }

        # ── ردیف ۲: نوار هشدارها ──
        projects_with_plan = set(
            Task.objects.filter(planned_date__range=(start, end))
            .values_list('project_id', flat=True)
        )
        active_ids = set(Project.objects.filter(status=Project.ACTIVE).values_list('id', flat=True))
        no_plan = len(active_ids - projects_with_plan)
        done_no_link = Task.objects.filter(done_q, published_url='').count()
        unreviewed = Task.objects.filter(status=Task.DONE, review_status=Task.UNREVIEWED).exclude(published_url='').count()

        ctx['alerts'] = {'overdue': overdue, 'no_plan': no_plan,
                         'done_no_link': done_no_link, 'unreviewed': unreviewed}

        # ── ردیف ۳: جدول وضعیت پروژه‌ها (یک کوئری با annotate شرطی) ──
        projects = list(Project.objects.filter(status=Project.ACTIVE).annotate(
            planned=Count('tasks', filter=Q(tasks__planned_date__range=(start, end))),
            done=Count('tasks', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            minutes=Sum('tasks__estimate_minutes', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            overdue=Count('tasks', filter=Q(tasks__status__in=[Task.TODO, Task.DOING], tasks__planned_date__lt=today)),
            last_activity=Max('tasks__updated_at'),
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

        # ── ردیف ۴ (راست): عملکرد همکاران در بازه ──
        colleagues = list(Colleague.objects.filter(status=Colleague.ACTIVE).annotate(
            planned=Count('tasks', filter=Q(tasks__planned_date__range=(start, end))),
            done=Count('tasks', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            minutes=Sum('tasks__estimate_minutes', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            overdue=Count('tasks', filter=Q(tasks__status__in=[Task.TODO, Task.DOING], tasks__planned_date__lt=today)),
        ))
        ctx['colleagues'] = colleagues

        # ── ردیف ۴ (چپ): فید بازبینی ──
        ctx['review_feed'] = Task.objects.select_related('project', 'assignee').filter(
            status=Task.DONE, review_status=Task.UNREVIEWED).exclude(published_url='').order_by('-done_date')[:8]

        # ── ردیف ۵: نمودار میله‌ای تسک‌های انجام‌شده به تفکیک روز ──
        ctx['daily_bars'] = self._daily_series(start, end)

        ctx['page_title'] = 'داشبورد'
        return ctx

    @staticmethod
    def _daily_series(start, end):
        """تعداد تسک انجام‌شده در هر روز بازه — برای نمودار میله‌ای SVG.
        الگو برای هیت‌مپ/اسپارک‌لاین هم همین است (گروه‌بندی در پایتون)."""
        rows = (Task.objects.filter(status=Task.DONE, done_date__range=(start, end))
                .values_list('done_date', flat=True))
        counts = {}
        for d in rows:
            counts[d] = counts.get(d, 0) + 1
        span = min((end - start).days + 1, 31)
        series = []
        mx = max(counts.values()) if counts else 1
        for i in range(span):
            d = start + timedelta(days=i)
            n = counts.get(d, 0)
            series.append({'h': round(n / mx * 100) if mx else 0, 'n': n})
        return series
