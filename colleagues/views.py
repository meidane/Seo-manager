"""ویوهای همکاران — CRUD کامل + غیرفعال/فعال‌سازی + آمار سینگل (گام ۶)."""
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from core.daterange import DateRangeMixin
from tasks.models import Task

from .forms import ColleagueForm
from .models import Colleague

# رنگ hex هر نوع تسک — برای نمودار دونات
TYPE_HEX = {
    'publish': '#38BDF8', 'update': '#FBBF24', 'tech': '#A78BFA',
    'reportage': '#F472B6', 'linkbuilding': '#2DD4A7', 'other': '#8FA0B8',
}
TYPE_LABEL = dict(Task.TYPE_CHOICES)


def donut_segments(pairs):
    """[(key,count)] → قطعه‌های SVG دونات با dasharray/dashoffset (مبنا ۱۰۰)."""
    total = sum(c for _, c in pairs) or 1
    segs, offset = [], 0.0
    for key, count in pairs:
        if not count:
            continue
        pct = count / total * 100
        segs.append({
            'label': TYPE_LABEL.get(key, key), 'color': TYPE_HEX.get(key, '#8FA0B8'),
            'pct': round(pct), 'dash': round(pct, 2), 'rest': round(100 - pct, 2),
            'offset': round(-offset, 2),
        })
        offset += pct
    return segs


class ColleagueListView(LoginRequiredMixin, ListView):
    model = Colleague
    template_name = 'colleagues/list.html'
    context_object_name = 'colleagues'
    paginate_by = 24

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(Q(full_name__icontains=query) | Q(email__icontains=query))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'همکاران'
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class ColleagueDetailView(LoginRequiredMixin, DateRangeMixin, DetailView):
    """سینگل همکار با آمار بازه‌ای، تفکیک نوع/پروژه و تب تقویم شخصی."""

    model = Colleague
    template_name = 'colleagues/detail.html'
    context_object_name = 'colleague'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        start, end = self.get_range(self.request)
        ctx.update(self.range_context())
        c = self.object

        done_q = Q(status=Task.DONE, done_date__range=(start, end))
        done_qs = c.tasks.filter(done_q)

        done = done_qs.count()
        words = done_qs.aggregate(s=Sum('word_count'))['s'] or 0
        open_count = c.tasks.filter(status__in=[Task.TODO, Task.DOING]).count()
        from datetime import date
        overdue = c.tasks.filter(status__in=[Task.TODO, Task.DOING], planned_date__lt=date.today()).count()

        # نرخ تحویل به‌موقع: انجام‌شده‌هایی که done_date <= planned_date
        on_time = sum(1 for t in done_qs.only('done_date', 'planned_date') if t.done_date and t.done_date <= t.planned_date)

        ctx['stats'] = {
            'done': done, 'open': open_count, 'overdue': overdue, 'words': words,
            'avg_words': round(words / done) if done else 0,
            'on_time': round(on_time / done * 100) if done else 0,
        }

        # تفکیک نوع تسک (دونات) و پروژه
        type_pairs = list(done_qs.values_list('task_type').annotate(n=Count('id')).values_list('task_type', 'n'))
        ctx['donut'] = donut_segments(type_pairs)
        ctx['by_project'] = list(done_qs.values('project__name').annotate(n=Count('id')).order_by('-n'))

        # نمودار میله‌ای روزانه
        ctx['daily_bars'] = self._daily(done_qs, start, end)
        # لیست تسک‌های او در بازه
        ctx['task_rows'] = c.tasks.select_related('project').filter(
            Q(planned_date__range=(start, end)) | done_q).order_by('-planned_date')[:40]
        ctx['page_title'] = c.full_name
        return ctx

    @staticmethod
    def _daily(qs, start, end):
        counts = {}
        for d in qs.values_list('done_date', flat=True):
            if d:
                counts[d] = counts.get(d, 0) + 1
        mx = max(counts.values()) if counts else 1
        span = min((end - start).days + 1, 31)
        return [{'h': round(counts.get(start + timedelta(days=i), 0) / mx * 100)} for i in range(span)]


class ColleagueCreateView(LoginRequiredMixin, CreateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleagues/form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'همکار جدید'
        ctx['is_edit'] = False
        return ctx


class ColleagueUpdateView(LoginRequiredMixin, UpdateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleagues/form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'ویرایش {self.object.full_name}'
        ctx['is_edit'] = True
        return ctx


class ColleagueArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        colleague = get_object_or_404(Colleague, pk=pk)
        colleague.archive()
        return redirect(colleague.get_absolute_url())


class ColleagueRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        colleague = get_object_or_404(Colleague, pk=pk)
        colleague.restore()
        return redirect(colleague.get_absolute_url())
