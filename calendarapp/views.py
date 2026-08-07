"""ویوهای تقویم — رندر اولیه سمت سرور، سپس ناوبری ماه با AJAX."""
from collections import defaultdict

import jdatetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import TemplateView

from colleagues.models import Colleague
from core.models import Holiday
from projects.models import Project
from tasks.models import Task

from .calendar_logic import build_month, month_bounds_gregorian, month_title


def _filtered_tasks(request, start, end):
    qs = Task.objects.select_related('project', 'assignee', 'type_def').filter(planned_date__range=(start, end))
    if request.GET.get('project'):
        qs = qs.filter(project_id=request.GET['project'])
    if request.GET.get('assignee'):
        qs = qs.filter(assignee_id=request.GET['assignee'])
    if request.GET.get('type'):
        qs = qs.filter(task_type=request.GET['type'])
    if request.GET.get('status'):
        qs = qs.filter(status=request.GET['status'])
    return qs


def _tasks_by_date(qs):
    grouped = defaultdict(list)
    for t in qs:
        grouped[t.planned_date].append(t.to_dict())
    return grouped


def _holiday_map(start, end):
    return {h.date: h.title for h in Holiday.objects.filter(is_off=True, date__range=(start, end))}


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
        cells = build_month(jyear, jmonth, _tasks_by_date(qs), _holiday_map(start, end))

        ctx['cells'] = cells
        ctx['jyear'] = jyear
        ctx['jmonth'] = jmonth
        ctx['month_title'] = month_title(jyear, jmonth)
        ctx['projects'] = Project.objects.filter(status=Project.ACTIVE)
        ctx['colleagues'] = Colleague.objects.filter(status=Colleague.ACTIVE)
        ctx['type_choices'] = Task.TYPE_CHOICES
        ctx['page_title'] = 'تقویم'
        return ctx


@login_required
def calendar_api(request):
    """داده‌ی ماه برای ناوبری AJAX. GET ?year=&month=&project=&assignee=&type="""
    jyear, jmonth = _resolve_ym(request)
    start, end = month_bounds_gregorian(jyear, jmonth)
    qs = _filtered_tasks(request, start, end)
    cells = build_month(jyear, jmonth, _tasks_by_date(qs), _holiday_map(start, end))
    return JsonResponse({
        'year': jyear, 'month': jmonth, 'title': month_title(jyear, jmonth), 'days': cells,
    })


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
