"""ویوهای تقویم — رندر اولیه سمت سرور، سپس ناوبری ماه با AJAX."""
from collections import defaultdict

import jdatetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import TemplateView

from colleagues.models import Colleague
from core.models import Holiday
from projects.access import accessible_project_ids
from projects.models import Project
from tasks.models import Task, TaskTypeDef

from .calendar_logic import build_month, month_bounds_gregorian, month_title


def _filtered_tasks(request, start, end):
    # تقویم پیش‌نماهای تکرار را هم نشان می‌دهد (کم‌رنگ)
    qs = Task.objects.with_placeholders().select_related('project', 'assignee', 'type_def').filter(planned_date__range=(start, end))
    ids = accessible_project_ids(request)
    if ids is not None:
        qs = qs.filter(project_id__in=ids)
    m = getattr(request, 'membership', None)
    if m and m.can('own_tasks_only'):
        colleague = getattr(request.user, 'colleague', None)
        qs = qs.filter(assignee_id=colleague.id if colleague else -1)
    if request.GET.get('project'):
        qs = qs.filter(project_id=request.GET['project'])
    if request.GET.get('assignee'):
        qs = qs.filter(assignee_id=request.GET['assignee'])
    if request.GET.get('type_def'):
        qs = qs.filter(type_def_id=request.GET['type_def'])
    elif request.GET.get('type'):  # سازگاری با لینک‌های قدیمی
        qs = qs.filter(task_type=request.GET['type'])
    if request.GET.get('status'):
        qs = qs.filter(status=request.GET['status'])
    return qs


def _tasks_by_date(qs):
    grouped = defaultdict(list)
    for t in qs:
        grouped[t.planned_date].append(t.to_dict())
    # انجام‌شده‌ها ته سلول (طوسی)، بقیه بر اساس ساعت
    for day in grouped.values():
        day.sort(key=lambda d: (d['done'], d['time']))
    return grouped


def _holiday_map(start, end):
    return {h.date: h.title for h in Holiday.objects.filter(is_off=True, date__range=(start, end))}


def _virtual_recurrence(start, end):
    """#۲: رخدادهای آینده‌ی قواعدِ تکرار را به‌صورت «مجازی» (بدون ساختِ رکورد) برای
    نمایشِ محوِ کلِ ماه در تقویم برمی‌گرداند. تاریخ‌هایی که تسکِ واقعی دارند رد می‌شوند."""
    from collections import defaultdict

    from tasks.models import RecurrenceRule, Task
    out = defaultdict(list)
    for rule in RecurrenceRule.objects.filter(active=True):
        tmpl = Task.all_objects.filter(recurrence=rule).order_by('planned_date').first()
        if not tmpl:
            continue
        real_dates = set(Task.all_objects.filter(recurrence=rule).values_list('planned_date', flat=True))
        d, steps = rule.start_date, 0
        while d <= end and steps < 400:
            if rule.end_date and d > rule.end_date:
                break
            if d >= start and d not in real_dates:
                vd = tmpl.to_dict()
                vd.update(id=None, virtual=True, is_placeholder=True, done=False, overdue=False)
                out[d].append(vd)
            d = rule.raw_next_date(d)
            steps += 1
    return out


def _merge_virtual(tbd, start, end):
    """رخدادهای مجازی تکرار را ته سلولِ هر روز اضافه می‌کند."""
    for d, items in _virtual_recurrence(start, end).items():
        tbd.setdefault(d, []).extend(items)
    return tbd


def _resolve_ym(request):
    today = jdatetime.date.today()
    try:
        jyear = int(request.GET.get('year', today.year))
        jmonth = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        jyear, jmonth = today.year, today.month
    return jyear, jmonth


class CalendarView(LoginRequiredMixin, TemplateView):
    template_name = 'calendarapp/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        jyear, jmonth = _resolve_ym(self.request)
        start, end = month_bounds_gregorian(jyear, jmonth)
        qs = _filtered_tasks(self.request, start, end)
        cells = build_month(jyear, jmonth, _merge_virtual(_tasks_by_date(qs), start, end), _holiday_map(start, end))

        ctx['cells'] = cells
        ctx['jyear'] = jyear
        ctx['jmonth'] = jmonth
        ctx['month_title'] = month_title(jyear, jmonth)
        ids = accessible_project_ids(self.request)
        visible = Project.objects.filter(id__in=ids) if ids is not None else Project.objects.all()
        ctx['projects'] = visible.filter(status=Project.ACTIVE)
        ctx['colleagues'] = Colleague.objects.filter(status=Colleague.ACTIVE)
        ctx['task_types'] = TaskTypeDef.objects.filter(is_active=True)
        ctx['page_title'] = 'تقویم'
        return ctx


@login_required
def calendar_api(request):
    """داده‌ی ماه برای ناوبری AJAX. GET ?year=&month=&project=&assignee=&type_def="""
    jyear, jmonth = _resolve_ym(request)
    start, end = month_bounds_gregorian(jyear, jmonth)
    qs = _filtered_tasks(request, start, end)
    cells = build_month(jyear, jmonth, _tasks_by_date(qs), _holiday_map(start, end))
    return JsonResponse({
        'year': jyear, 'month': jmonth, 'title': month_title(jyear, jmonth), 'days': cells,
    })


@login_required
def picker_api(request):
    """شبکه‌ی ماه فقط با پرچم تعطیلی/امروز — برای دیت‌پیکر فیلدهای تاریخ."""
    jyear, jmonth = _resolve_ym(request)
    start, end = month_bounds_gregorian(jyear, jmonth)
    cells = build_month(jyear, jmonth, {}, _holiday_map(start, end))
    days = [{
        'jday_fa': c['jday_fa'], 'jdate': c['jdate'], 'gdate': c['gdate'],
        'dim': c['dim'], 'is_today': c['is_today'], 'is_holiday': c['is_holiday'],
        'holiday_title': c['holiday_title'],
    } for c in cells]
    return JsonResponse({'year': jyear, 'month': jmonth, 'title': month_title(jyear, jmonth), 'days': days})


@login_required
def workload_api(request):
    """بار کاری یک همکار در یک ماه — برای انتخابگر تاریخ داخل مودال تسک.
    GET ?assignee=&year=&month=  →  {date: count}"""
    jyear, jmonth = _resolve_ym(request)
    start, end = month_bounds_gregorian(jyear, jmonth)
    qs = Task.objects.filter(planned_date__range=(start, end))
    if request.GET.get('assignee'):
        qs = qs.filter(assignee_id=request.GET['assignee'])
    counts = defaultdict(int)
    for d in qs.values_list('planned_date', flat=True):
        counts[d.isoformat()] += 1
    return JsonResponse({'workload': counts, 'total': sum(counts.values())})
