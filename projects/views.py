"""ویوهای پروژه‌ها — CRUD + سینگل با تب‌ها + API دسترسی‌های رمزنگاری‌شده."""
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from accounts.access import has_perm, require_perm
from core.columns import get_columns
from core.daterange import DateRangeMixin
from core.models import ActivityLog, ColumnConfig

from .access import accessible_project_ids
from .forms import ProjectForm
from .models import Credential, Project


def _current_jalali_ym():
    from datetime import date

    from core.jalali import g2j
    j = g2j(date.today())
    return j.year, j.month


def _report_month_rows(project_ids, periods):
    """{project_id: {(year, month): ستون‌های آماریِ همان ماهِ گزارش}} — برای ردیف‌های
    ماهانهٔ صفحهٔ پروژه‌ها (شخصی‌سازیِ سئو). فیلترشده روی (report_year, report_month).
    `periods` = لیستِ tupleهای (year, month)."""
    from datetime import date
    from types import SimpleNamespace

    from django.db.models import Count, Max, Q, Sum

    from tasks.models import Task

    if not project_ids or not periods:
        return {}
    today = date.today()
    year_q = Q()
    for yr, mo in periods:
        year_q |= Q(report_year=yr, report_month=mo)
    agg = (Task.objects.filter(project_id__in=project_ids).filter(year_q)
           .values('project_id', 'report_year', 'report_month')
           .annotate(
               planned=Count('id'),
               done=Count('id', filter=Q(status=Task.DONE)),
               words=Sum('word_count', filter=Q(status=Task.DONE)),
               minutes=Sum('spent_minutes', filter=Q(status=Task.DONE)),
               overdue=Count('id', filter=Q(status__in=[Task.TODO, Task.DOING], planned_date__lt=today)),
               last_activity=Max('updated_at')))
    by = {(r['project_id'], r['report_year'], r['report_month']): r for r in agg}
    out = {}
    for pid in project_ids:
        out[pid] = {}
        for yr, mo in periods:
            r = by.get((pid, yr, mo), {})
            key = f'{yr}-{mo}'
            planned = r.get('planned') or 0
            done = r.get('done') or 0
            progress = round(done / planned * 100) if planned else 0
            overdue = r.get('overdue') or 0
            if planned == 0:
                state = ('mute', 'بدون کار')
            elif overdue:
                state = ('bad', 'عقب‌افتاده')
            elif progress < 60:
                state = ('warn', 'عقب')
            elif progress < 100:
                state = ('ok', 'روی روال')
            else:
                state = ('info', 'کامل')
            out[pid][key] = SimpleNamespace(
                planned=planned, done=done, remaining=max(planned - done, 0),
                overdue=overdue, words=r.get('words') or 0, minutes=r.get('minutes') or 0,
                progress=progress, state=state,
                last_report=None, last_payment=None, last_activity=r.get('last_activity'))
    return out


class ProjectListView(LoginRequiredMixin, DateRangeMixin, ListView):
    """لیست جدولی پروژه‌ها با اطلاعات مدیریتی (مثل جدول داشبورد)."""

    model = Project
    template_name = 'projects/list.html'
    context_object_name = 'projects'
    paginate_by = 50

    def get_queryset(self):
        from datetime import date

        from django.db.models import Count, Max, Sum

        from tasks.models import Task

        start, end = self.get_range(self.request)
        self._start, self._end = start, end
        qs = super().get_queryset()
        ids = accessible_project_ids(self.request)
        if ids is not None:
            qs = qs.filter(id__in=ids)
        query = self.request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(domain__icontains=query))
        from django.db.models import Case, IntegerField, Value, When
        return qs.annotate(
            planned=Count('tasks', filter=Q(tasks__planned_date__range=(start, end))),
            done=Count('tasks', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            words=Sum('tasks__word_count', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            minutes=Sum('tasks__spent_minutes', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            overdue=Count('tasks', filter=Q(tasks__status__in=[Task.TODO, Task.DOING], tasks__planned_date__lt=date.today())),
            last_report=Max('reports__date_to'),
            last_activity=Max('tasks__updated_at'),
            # پروژه‌ی شخصی همیشه اولِ لیست (فقط پروژه‌ی شخصیِ خودِ کاربر اینجا هست)
            _personal=Case(When(personal_owner__isnull=False, then=Value(0)),
                           default=Value(1), output_field=IntegerField()),
        ).order_by('_personal', 'status', 'name')  # شخصی اول، سپس ترتیبِ پایدار

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.range_context())
        for p in ctx['projects']:
            p.remaining = max(p.planned - p.done, 0)
            p.progress = round(p.done / p.planned * 100) if p.planned else 0
            if not p.is_active:
                p.state = ('mute', 'غیرفعال')
            elif p.planned == 0:
                p.state = ('bad', 'بدون کار')
            elif p.overdue:
                p.state = ('bad', 'عقب‌افتاده')
            elif p.progress < 60:
                p.state = ('warn', 'عقب')
            elif p.progress < 100:
                p.state = ('ok', 'روی روال')
            else:
                p.state = ('info', 'جلوتر')
        ctx['columns'] = get_columns(ColumnConfig.PROJECTS, ColumnConfig.PAGE)
        # ── ماه‌های گزارش (شخصی‌سازیِ سئو): ماهِ قبل/جاری/بعد ──
        from tasks.models import Task
        cur_y, cur_m = _current_jalali_ym()
        prev_y, prev_m = (cur_y - 1, 12) if cur_m == 1 else (cur_y, cur_m - 1)
        nxt_y, nxt_m = (cur_y + 1, 1) if cur_m == 12 else (cur_y, cur_m + 1)
        from types import SimpleNamespace
        month_labels = dict(Task.REPORT_MONTH_CHOICES)
        # برچسبِ ماه با سال: «مرداد ۱۴۰۵». key = «سال-ماه» برای نگاشت به month_rows.
        ctx['month_meta'] = [
            SimpleNamespace(key=f'{yr}-{mo}', year=yr, month=mo,
                            label=f'{month_labels[mo]} {yr}', tag=tag)
            for yr, mo, tag in [(prev_y, prev_m, 'قبل'), (cur_y, cur_m, 'جاری'), (nxt_y, nxt_m, 'بعد')]
        ]
        ctx['month_rows'] = _report_month_rows(
            [p.id for p in ctx['projects']], [(prev_y, prev_m), (cur_y, cur_m), (nxt_y, nxt_m)])
        ctx['page_title'] = 'پروژه‌ها'
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class ProjectDetailView(LoginRequiredMixin, DateRangeMixin, DetailView):
    model = Project
    template_name = 'projects/detail.html'
    context_object_name = 'project'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        ids = accessible_project_ids(self.request)
        if ids is not None and obj.id not in ids:
            raise PermissionDenied('به این پروژه دسترسی نداری')
        return obj

    def get_context_data(self, **kwargs):
        from datetime import date

        from django.db.models import Q, Sum

        from tasks.models import Task

        ctx = super().get_context_data(**kwargs)
        start, end = self.get_range(self.request)
        ctx.update(self.range_context())
        p = self.object

        done_qs = p.tasks.filter(status=Task.DONE, done_date__range=(start, end))
        planned = p.tasks.filter(planned_date__range=(start, end)).count()
        done = done_qs.count()
        ctx['stats'] = {
            'done': done, 'planned': planned, 'remaining': max(planned - done, 0),
            'overdue': p.tasks.filter(status__in=[Task.TODO, Task.DOING], planned_date__lt=date.today()).count(),
            'words': done_qs.aggregate(s=Sum('word_count'))['s'] or 0,
        }
        if p.track_keyword_rank:
            from seo import rank as seo_rank
            period = seo_rank.resolve_period(self.request)
            ctx['kw_period'] = period
            ctx['kw_period_choices'] = seo_rank.PERIOD_CHOICES
            ctx['keyword_rows'] = seo_rank.keyword_rows(p, period)
            ctx['page_rows'] = seo_rank.page_rows(p, period)
            ctx['scheduled_rows'] = seo_rank.scheduled_rows(p)

        ctx['task_rows'] = p.tasks.select_related('assignee','type_def').filter(
            Q(planned_date__range=(start, end)) | Q(status=Task.DONE, done_date__range=(start, end))
        ).order_by('-planned_date')[:40]

        # ── تفکیکِ ماهِ گزارش (شخصی‌سازیِ سئو) — آخرِ تبِ «نمای کلی» ──
        from django.db.models import Count
        labels = dict(Task.REPORT_MONTH_CHOICES)
        mb = (p.tasks.filter(report_month__isnull=False)
              .values('report_year', 'report_month')
              .annotate(total=Count('id'), done=Count('id', filter=Q(status=Task.DONE))))
        # مرتب‌سازی: جدیدترین سال/ماه اول (سالِ نامشخص انتها)
        rows = sorted(mb, key=lambda r: (r['report_year'] or 0, r['report_month']), reverse=True)
        ctx['month_breakdown'] = [
            {'num': r['report_month'], 'year': r['report_year'],
             'label': f"{labels[r['report_month']]} {r['report_year']}" if r['report_year'] else labels[r['report_month']],
             'total': r['total'], 'done': r['done']}
            for r in rows]

        ctx['page_title'] = p.name
        ctx['credentials'] = p.credentials.all()
        from colleagues.models import Colleague
        ctx['all_colleagues'] = Colleague.objects.filter(status=Colleague.ACTIVE)
        ctx['member_ids'] = set(p.members.values_list('id', flat=True))
        ctx['can_manage_members'] = has_perm(self.request, 'project_colleagues_access')

        # ── بردِ سئو: سکشن‌های ماهِ گزارش (شخصی‌سازیِ سئو) ──
        from tasks.models import ReportMonthStrategy, ReportPeriod, TaskTypeDef
        seo_type = self.request.GET.get('seo_type') or ''
        bt = p.tasks.select_related('assignee', 'type_def').filter(report_month__isnull=False)
        if seo_type:
            bt = bt.filter(type_def_id=seo_type)
        bt = bt.order_by('board_order', 'id')
        strat = {(s.year, s.month): s for s in ReportMonthStrategy.objects.filter(project=p)}
        periods, by = set(strat), {}
        for t in bt:
            k = (t.report_year, t.report_month)
            periods.add(k); by.setdefault(k, []).append(t)
        sections = []
        for yr, mo in sorted(periods, key=lambda k: (k[0] or 0, k[1]), reverse=True):
            s = strat.get((yr, mo))
            sections.append({'year': yr, 'month': mo, 'label': f'{labels.get(mo, mo)} {yr}',
                             'strategy': s.description if s else '', 'has_strategy': bool(s and s.description),
                             'tasks': by.get((yr, mo), [])})
        ctx['seo_sections'] = sections
        ctx['seo_types'] = list(TaskTypeDef.objects.filter(is_active=True).values_list('id', 'name'))
        ctx['seo_type'] = seo_type
        ctx['status_choices'] = Task.STATUS_CHOICES
        # ستون‌های سفارشی مطابقِ لیستِ تسک‌ها؛ فیلدهای سفارشی فقط وقتی نوعی انتخاب شده
        cols = get_columns(ColumnConfig.TASKS, ColumnConfig.PAGE)
        ctx['seo_cols'] = [c for c in cols if (not c['key'].startswith('cf:')) or c['key'].split(':')[1] == seo_type]
        ctx['can_edit_task'] = bool(getattr(self.request, 'membership', None) and self.request.membership.can('edit_task'))
        # ماه‌های گزارشِ تعریف‌شده در تنظیمات (منبعِ واحدِ افزودنِ سکشن) — منهای سکشن‌های موجود
        existing = {(s['year'], s['month']) for s in sections}
        ctx['seo_periods'] = [rp for rp in ReportPeriod.objects.all() if (rp.year, rp.month) not in existing]
        return ctx


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/form.html'

    def dispatch(self, request, *args, **kwargs):
        require_perm(request, 'add_project')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'پروژه‌ی جدید'
        ctx['is_edit'] = False
        return ctx


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/form.html'

    def dispatch(self, request, *args, **kwargs):
        require_perm(request, 'edit_project')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not _project_access_ok(self.request, obj.id):
            raise PermissionDenied('به این پروژه دسترسی نداری')
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'ویرایش {self.object.name}'
        ctx['is_edit'] = True
        return ctx


class ProjectArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        require_perm(request, 'edit_project')
        project = get_object_or_404(Project, pk=pk)
        if not _project_access_ok(request, project.id):
            raise PermissionDenied('به این پروژه دسترسی نداری')
        project.archive()
        return redirect(project.get_absolute_url())


class ProjectRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        require_perm(request, 'edit_project')
        project = get_object_or_404(Project, pk=pk)
        if not _project_access_ok(request, project.id):
            raise PermissionDenied('به این پروژه دسترسی نداری')
        project.restore()
        return redirect(project.get_absolute_url())


@login_required
@require_http_methods(['PATCH'])
def project_members(request, pk):
    """تبِ «دسترسی به همکاران»: فهرستِ کاملِ اعضای مجاز را یک‌جا ست می‌کند.
    فقط مالکِ سازمان همیشه دسترسی دارد؛ بقیه (حتی مدیرِ خودِ پروژه) باید همین‌جا
    اضافه شوند تا پروژه/تسک‌هایش را ببینند (`projects/access.py`)."""
    require_perm(request, 'project_colleagues_access')
    if not _project_access_ok(request, pk):
        return JsonResponse({'detail': 'به این پروژه دسترسی نداری'}, status=403)
    project = get_object_or_404(Project, pk=pk)
    data = json.loads(request.body or '{}')
    ids = data.get('members')
    if not isinstance(ids, list):
        return JsonResponse({'detail': 'فهرستِ اعضا لازم است'}, status=400)
    from colleagues.models import Colleague
    valid = Colleague.objects.filter(id__in=ids)
    project.members.set(valid)
    return JsonResponse({'ok': True, 'members': list(valid.values_list('id', flat=True))})


# ── API دسترسی‌ها (JSON) ────────────────────────────────────────────────

def _cred_json(cred):
    return {
        'id': cred.id, 'title': cred.title, 'url': cred.url,
        'username': cred.username, 'note': cred.note,
    }


def _project_access_ok(request, project_id):
    ids = accessible_project_ids(request)
    return ids is None or project_id in ids


@require_http_methods(['POST'])
def credential_create(request, pk):
    require_perm(request, 'project_credentials')
    if not _project_access_ok(request, pk):
        return JsonResponse({'detail': 'به این پروژه دسترسی نداری'}, status=403)
    project = get_object_or_404(Project, pk=pk)
    data = json.loads(request.body or '{}')
    if not data.get('title'):
        return JsonResponse({'detail': 'عنوان لازم است'}, status=400)
    cred = Credential(
        project=project, title=data['title'], url=data.get('url', ''),
        username=data.get('username', ''), note=data.get('note', ''),
    )
    cred.set_password(data.get('password', ''))
    cred.save()
    return JsonResponse(_cred_json(cred), status=201)


@require_http_methods(['GET'])
def credential_reveal(request, pk):
    """بازگشایی پسورد + ثبت رویداد در ActivityLog."""
    require_perm(request, 'project_credentials')
    cred = get_object_or_404(Credential, pk=pk)
    if not _project_access_ok(request, cred.project_id):
        return JsonResponse({'detail': 'به این پروژه دسترسی نداری'}, status=403)
    ActivityLog.objects.create(
        actor=request.user, verb='reveal_credential', content_object=cred,
        changes={'credential': cred.title, 'project': cred.project.name},
    )
    return JsonResponse({'password': cred.reveal_password()})


@require_http_methods(['DELETE'])
def credential_delete(request, pk):
    require_perm(request, 'project_credentials')
    cred = get_object_or_404(Credential, pk=pk)
    if not _project_access_ok(request, cred.project_id):
        return JsonResponse({'detail': 'به این پروژه دسترسی نداری'}, status=403)
    cred.delete()
    return JsonResponse({'ok': True})


# ── فایل‌های پروژه (Attachment) ──────────────────────────────────────────

def _file_json(a):
    return {'id': a.id, 'name': a.original_name or a.file.name.split('/')[-1],
            'url': a.file.url, 'is_image': a.is_image, 'size': a.size_h}


@require_http_methods(['GET', 'POST'])
def project_files(request, pk):
    require_perm(request, 'project_files')
    if not _project_access_ok(request, pk):
        return JsonResponse({'detail': 'به این پروژه دسترسی نداری'}, status=403)
    from django.contrib.contenttypes.models import ContentType

    from core.models import Attachment
    project = get_object_or_404(Project, pk=pk)
    ct = ContentType.objects.get_for_model(Project)
    if request.method == 'GET':
        files = Attachment.objects.filter(content_type=ct, object_id=project.id).order_by('-uploaded_at')
        return JsonResponse({'files': [_file_json(a) for a in files]})
    # POST — آپلود (یک یا چند فایل)
    created = []
    for f in request.FILES.getlist('file'):
        if f.size > 20 * 1024 * 1024:
            continue
        a = Attachment.objects.create(
            content_type=ct, object_id=project.id, file=f,
            original_name=f.name, size=f.size, mime=f.content_type or '',
            uploaded_by=request.user,
        )
        created.append(_file_json(a))
    return JsonResponse({'files': created}, status=201)


@require_http_methods(['DELETE'])
def project_file_delete(request, pk):
    require_perm(request, 'project_files')
    from core.models import Attachment
    a = get_object_or_404(Attachment, pk=pk)
    if not _project_access_ok(request, a.object_id):
        return JsonResponse({'detail': 'به این پروژه دسترسی نداری'}, status=403)
    a.delete()
    return JsonResponse({'ok': True})


# ── بردِ سئو: استراتژیِ ماه، افزودنِ سکشن/ردیف، ترتیب‌دهی ────────────────
def _seo_gate(request, pk):
    """گیتِ مشترکِ اندپوینت‌های برد: لاگین + دسترسی به پروژه. تغییرِ داده نیازمندِ
    edit_task یا داشتنِ پروفایلِ همکار (مثلِ tasks.api.task_create)."""
    if not _project_access_ok(request, pk):
        return JsonResponse({'detail': 'به این پروژه دسترسی نداری'}, status=403)
    return None


@login_required
@require_http_methods(['POST'])
def seo_strategy(request, pk):
    """ذخیره/به‌روزرسانیِ استراتژیِ یک ماهِ گزارش (مودالِ «استراتژی»)."""
    from core.htmlsan import clean_html
    from tasks.models import ReportMonthStrategy
    err = _seo_gate(request, pk)
    if err:
        return err
    project = get_object_or_404(Project, pk=pk)
    d = json.loads(request.body or '{}')
    try:
        year, month = int(d.get('year')), int(d.get('month'))
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'سال و ماه لازم است'}, status=400)
    s, _ = ReportMonthStrategy.objects.get_or_create(project=project, year=year, month=month)
    s.description = clean_html(d.get('description', ''))
    s.save()
    return JsonResponse({'ok': True, 'description': s.description})


@login_required
@require_http_methods(['POST'])
def seo_section_add(request, pk):
    """افزودنِ یک سکشنِ ماهِ گزارش (رکوردِ خالیِ استراتژی می‌سازد تا سکشن ظاهر شود)."""
    from tasks.models import ReportMonthStrategy
    err = _seo_gate(request, pk)
    if err:
        return err
    project = get_object_or_404(Project, pk=pk)
    d = json.loads(request.body or '{}')
    try:
        year, month = int(d.get('year')), int(d.get('month'))
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'سال و ماه لازم است'}, status=400)
    ReportMonthStrategy.objects.get_or_create(project=project, year=year, month=month)
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['POST'])
def seo_task_add(request, pk):
    """افزودنِ ردیفِ تسک به یک سکشن — «ایده» (بدونِ تاریخ، فقط عنوان). فیلدهای لازم
    فقط موقعِ برنامه‌ریزی (ست‌کردنِ تاریخ/تکمیل) اعمال می‌شوند (tasks.api)."""
    from tasks.models import Task, TaskTypeDef
    err = _seo_gate(request, pk)
    if err:
        return err
    project = get_object_or_404(Project, pk=pk)
    d = json.loads(request.body or '{}')
    title = (d.get('title') or '').strip()
    if not title:
        return JsonResponse({'detail': 'عنوان لازم است'}, status=400)
    try:
        year, month = int(d.get('year')), int(d.get('month'))
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'سال و ماه لازم است'}, status=400)
    my = getattr(request.user, 'colleague', None)
    td = None
    if d.get('type'):
        td = TaskTypeDef.objects.filter(pk=d['type']).first()
    # ردیفِ جدید ته سکشن
    last = Task.objects.filter(project=project, report_year=year, report_month=month).order_by('-board_order').first()
    task = Task(project=project, title=title, report_year=year, report_month=month,
                planned_date=None, assignee=my, created_by=request.user,
                board_order=(last.board_order + 1 if last else 0))
    if td:
        task.type_def = td
        task.task_type = td.builtin_key or Task.OTHER
    else:
        task.task_type = Task.OTHER
    task.save()
    return JsonResponse({'ok': True, 'id': task.id})


@login_required
@require_http_methods(['POST'])
def seo_reorder(request, pk):
    """جابه‌جاییِ ردیف‌ها: فهرستِ id به ترتیبِ جدید → board_order را ست می‌کند."""
    from tasks.models import Task
    err = _seo_gate(request, pk)
    if err:
        return err
    d = json.loads(request.body or '{}')
    ids = d.get('ids') or []
    tasks = {t.id: t for t in Task.objects.filter(project_id=pk, id__in=ids)}
    for i, tid in enumerate(ids):
        t = tasks.get(int(tid))
        if t and t.board_order != i:
            t.board_order = i
            t.save(update_fields=['board_order'])
    return JsonResponse({'ok': True})
