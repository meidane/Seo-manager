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
        return qs.annotate(
            planned=Count('tasks', filter=Q(tasks__planned_date__range=(start, end))),
            done=Count('tasks', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            words=Sum('tasks__word_count', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            minutes=Sum('tasks__spent_minutes', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            overdue=Count('tasks', filter=Q(tasks__status__in=[Task.TODO, Task.DOING], tasks__planned_date__lt=date.today())),
            last_report=Max('reports__date_to'),
            last_activity=Max('tasks__updated_at'),
        ).order_by('status', 'name')  # ترتیب صریح برای صفحه‌بندیِ پایدار

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

        ctx['task_rows'] = p.tasks.select_related('assignee','type_def').filter(
            Q(planned_date__range=(start, end)) | Q(status=Task.DONE, done_date__range=(start, end))
        ).order_by('-planned_date')[:40]
        ctx['page_title'] = p.name
        ctx['credentials'] = p.credentials.all()
        from colleagues.models import Colleague
        ctx['all_colleagues'] = Colleague.objects.filter(status=Colleague.ACTIVE)
        ctx['member_ids'] = set(p.members.values_list('id', flat=True))
        ctx['can_manage_members'] = has_perm(self.request, 'project_colleagues_access')
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
