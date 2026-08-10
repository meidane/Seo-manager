"""ویوهای همکاران — CRUD کامل + غیرفعال/فعال‌سازی + آمار سینگل (گام ۶)."""
import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from accounts.access import require_perm
from core.columns import get_columns
from core.daterange import DateRangeMixin
from core.models import ColumnConfig
from projects.access import accessible_project_ids
from tasks.models import Task

from .forms import ColleagueForm
from .models import Colleague


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}

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


class ColleagueListView(LoginRequiredMixin, DateRangeMixin, ListView):
    """لیست جدولی همکاران با آمار بازه‌ای + اسپارک‌لاین روند (مثل داشبورد)."""

    model = Colleague
    template_name = 'colleagues/list.html'
    context_object_name = 'colleagues'
    paginate_by = 50

    def get_queryset(self):
        from datetime import date

        start, end = self.get_range(self.request)
        self._start, self._end = start, end
        qs = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(Q(full_name__icontains=query) | Q(email__icontains=query))
        ids = accessible_project_ids(self.request)
        tq = Q(tasks__project_id__in=ids) if ids is not None else Q()
        return qs.annotate(
            planned=Count('tasks', filter=Q(tasks__planned_date__range=(start, end)) & tq),
            done=Count('tasks', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end)) & tq),
            words=Sum('tasks__word_count', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end)) & tq),
            minutes=Sum('tasks__spent_minutes', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end)) & tq),
            overdue=Count('tasks', filter=Q(tasks__status__in=[Task.TODO, Task.DOING], tasks__planned_date__lt=date.today()) & tq),
        ).order_by('status', 'full_name')  # ترتیب صریح برای صفحه‌بندیِ پایدار

    def get_context_data(self, **kwargs):
        from collections import defaultdict
        from datetime import timedelta

        ctx = super().get_context_data(**kwargs)
        ctx.update(self.range_context())
        colleagues = ctx['colleagues']

        # اسپارک‌لاین ۱۴ روزه: یک کوئری برای همه، گروه‌بندی در پایتون
        span_end = self._end
        span_start = span_end - timedelta(days=13)
        rows = Task.objects.filter(
            status=Task.DONE, done_date__range=(span_start, span_end)
        ).values_list('assignee_id', 'done_date')
        series = defaultdict(lambda: [0] * 14)
        for aid, d in rows:
            idx = (d - span_start).days
            if 0 <= idx < 14:
                series[aid][idx] += 1
        for c in colleagues:
            raw = series.get(c.id, [0] * 14)
            mx = max(raw) or 1
            c.spark = [max(round(v / mx * 100), 5) if v else 5 for v in raw]

        ctx['columns'] = get_columns(ColumnConfig.COLLEAGUES, ColumnConfig.PAGE)
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

        from datetime import date

        from core.jalali import format_jalali
        from projects.access import accessible_project_ids
        ids = accessible_project_ids(self.request)
        tasks_qs = c.tasks.filter(project_id__in=ids) if ids is not None else c.tasks.all()

        done_q = Q(status=Task.DONE, done_date__range=(start, end))
        done_qs = tasks_qs.filter(done_q)

        done = done_qs.count()
        words = done_qs.aggregate(s=Sum('word_count'))['s'] or 0
        planned = tasks_qs.filter(planned_date__range=(start, end)).count()
        minutes = done_qs.aggregate(s=Sum('spent_minutes'))['s'] or 0
        open_count = tasks_qs.filter(status__in=[Task.TODO, Task.DOING]).count()
        overdue = tasks_qs.filter(status__in=[Task.TODO, Task.DOING], planned_date__lt=date.today()).count()

        # نرخ تحویل به‌موقع: انجام‌شده‌هایی که done_date <= planned_date
        on_time = sum(1 for t in done_qs.only('done_date', 'planned_date') if t.done_date and t.done_date <= t.planned_date)

        ctx['stats'] = {
            'planned': planned, 'done': done, 'open': open_count, 'overdue': overdue,
            'words': words, 'minutes': minutes, 'avg_words': round(words / done) if done else 0,
            'on_time': round(on_time / done * 100) if done else 0,
        }

        # تفکیک نوع تسک (دونات) بر اساس نوعِ مؤثر (سفارشی یا built-in) و پروژه
        ctx['donut'] = self._donut(done_qs)
        ctx['by_project'] = list(done_qs.values('project__name').annotate(n=Count('id')).order_by('-n'))

        # نمودار میله‌ای روزانه (+ محور برای #۱۵)
        bars, dmax = self._daily(done_qs, start, end)
        ctx['daily_bars'] = bars
        ctx['daily_max'] = dmax
        ctx['daily_from'] = format_jalali(start, '%m/%d')
        ctx['daily_to'] = format_jalali(end, '%m/%d')
        # لیست تسک‌های او در بازه
        ctx['task_rows'] = tasks_qs.select_related('project','type_def').filter(
            Q(planned_date__range=(start, end)) | done_q).order_by('-planned_date')[:40]
        ctx['page_title'] = c.full_name

        from accounts.models import Invite
        org = getattr(self.request, 'organization', None)
        ctx['can_manage_colleagues'] = bool(getattr(self.request, 'membership', None)
                                             and self.request.membership.can('manage_colleagues'))
        ctx['pending_invite'] = Invite.objects.filter(colleague=c, status=Invite.PENDING).first()
        ctx['org_roles'] = list(org.roles.all()) if org else []
        return ctx

    @staticmethod
    def _donut(done_qs):
        """قطعه‌های دونات بر اساس نوعِ مؤثر: نوع سفارشی (نام/رنگِ خودش) وگرنه built-in."""
        from collections import defaultdict
        buckets = defaultdict(lambda: {'n': 0, 'label': '', 'color': ''})
        for t in done_qs.select_related('type_def'):
            if t.type_def_id:
                key, label, color = f'd{t.type_def_id}', t.type_def.name, t.type_def.color
            else:
                key = t.task_type
                label, color = TYPE_LABEL.get(key, key), TYPE_HEX.get(key, '#8FA0B8')
            b = buckets[key]
            b['n'] += 1
            b['label'], b['color'] = label, color
        total = sum(b['n'] for b in buckets.values()) or 1
        segs, offset = [], 0.0
        for b in sorted(buckets.values(), key=lambda x: -x['n']):
            pct = b['n'] / total * 100
            segs.append({'label': b['label'], 'color': b['color'], 'pct': round(pct),
                         'dash': round(pct, 2), 'rest': round(100 - pct, 2), 'offset': round(-offset, 2)})
            offset += pct
        return segs

    @staticmethod
    def _daily(qs, start, end):
        counts = {}
        for d in qs.values_list('done_date', flat=True):
            if d:
                counts[d] = counts.get(d, 0) + 1
        mx = max(counts.values()) if counts else 1
        span = min((end - start).days + 1, 31)
        bars = [{'h': round(counts.get(start + timedelta(days=i), 0) / mx * 100),
                 'n': counts.get(start + timedelta(days=i), 0)} for i in range(span)]
        return bars, mx


class ColleagueCreateView(LoginRequiredMixin, CreateView):
    model = Colleague
    form_class = ColleagueForm
    template_name = 'colleagues/form.html'

    def dispatch(self, request, *args, **kwargs):
        require_perm(request, 'manage_colleagues')
        return super().dispatch(request, *args, **kwargs)

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

    def dispatch(self, request, *args, **kwargs):
        require_perm(request, 'manage_colleagues')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'ویرایش {self.object.full_name}'
        ctx['is_edit'] = True
        return ctx


class ColleagueArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        require_perm(request, 'manage_colleagues')
        colleague = get_object_or_404(Colleague, pk=pk)
        colleague.archive()
        return redirect(colleague.get_absolute_url())


class ColleagueRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        require_perm(request, 'manage_colleagues')
        colleague = get_object_or_404(Colleague, pk=pk)
        colleague.restore()
        return redirect(colleague.get_absolute_url())


# ── API: دسترسیِ همکار به سیستم (دعوت‌نامه) ─────────────────────────────────

@login_required
@require_http_methods(['POST'])
def colleague_grant_access(request, pk):
    """برای همکاری که هنوز حساب کاربری ندارد، دعوت‌نامه‌ی در انتظار می‌سازد —
    یا با شماره‌ی فردِ ازقبل‌ثبت‌نام‌کرده (mode=existing) یا با ساختِ حساب تازه
    (mode=new، چون سرور ایمیل نداریم و نمی‌توانیم لینکِ دعوت بفرستیم؛ نام‌کاربری/رمز
    را خودِ مدیر باید به همکار برساند). قبول/ردِ دعوت با `accounts.Invite.accept/reject`."""
    from accounts.models import Invite, Membership, User

    org = require_perm(request, 'manage_colleagues')
    colleague = get_object_or_404(Colleague, pk=pk)
    if colleague.user_id:
        return JsonResponse({'detail': 'این همکار قبلاً به سیستم دسترسی دارد'}, status=400)
    if Invite.objects.filter(colleague=colleague, status=Invite.PENDING).exists():
        return JsonResponse({'detail': 'قبلاً دعوت‌نامه‌ی در انتظار برای این همکار ثبت شده'}, status=400)

    d = _body(request)
    role = d.get('role') if org.roles.filter(key=d.get('role')).exists() else 'member'
    mode = d.get('mode') or 'new'

    if mode == 'existing':
        phone = (d.get('phone') or '').strip()
        u = User.objects.filter(phone=phone).first() if phone else None
        if not u:
            return JsonResponse({'detail': 'کاربری با این شماره ثبت‌نام نکرده است'}, status=400)
        if Membership.objects.filter(user=u, organization=org).exists():
            return JsonResponse({'detail': 'این کاربر قبلاً عضو سازمان است'}, status=400)
    else:
        username = (d.get('username') or '').strip()
        password = d.get('password') or ''
        if not username or not password:
            return JsonResponse({'detail': 'نام‌کاربری و رمز لازم است'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'detail': 'این نام‌کاربری قبلاً ثبت شده'}, status=400)
        name_parts = colleague.full_name.split(maxsplit=1)
        u = User.objects.create_user(
            username=username, password=password,
            first_name=name_parts[0] if name_parts else '',
            last_name=name_parts[1] if len(name_parts) > 1 else '',
            email=colleague.email, phone=colleague.phone)

    Invite.objects.create(organization=org, user=u, role=role, colleague=colleague, invited_by=request.user)
    return JsonResponse({'ok': True}, status=201)


@login_required
@require_http_methods(['POST'])
def colleague_revoke_invite(request, pk):
    """دعوت‌نامه‌ی در انتظارِ این همکار را لغو می‌کند (حذف، نه رد — تا بشود دوباره دعوت کرد)."""
    from accounts.models import Invite

    require_perm(request, 'manage_colleagues')
    colleague = get_object_or_404(Colleague, pk=pk)
    Invite.objects.filter(colleague=colleague, status=Invite.PENDING).delete()
    return JsonResponse({'ok': True})
