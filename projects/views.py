"""ویوهای پروژه‌ها — CRUD + سینگل با تب‌ها + API دسترسی‌های رمزنگاری‌شده."""
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from core.daterange import DateRangeMixin
from core.models import ActivityLog

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
        query = self.request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(domain__icontains=query))
        return qs.annotate(
            planned=Count('tasks', filter=Q(tasks__planned_date__range=(start, end))),
            done=Count('tasks', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            words=Sum('tasks__word_count', filter=Q(tasks__status=Task.DONE, tasks__done_date__range=(start, end))),
            overdue=Count('tasks', filter=Q(tasks__status__in=[Task.TODO, Task.DOING], tasks__planned_date__lt=date.today())),
            last_report=Max('reports__date_to'),
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
        ctx['page_title'] = 'پروژه‌ها'
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class ProjectDetailView(LoginRequiredMixin, DateRangeMixin, DetailView):
    model = Project
    template_name = 'projects/detail.html'
    context_object_name = 'project'

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
        ctx['task_rows'] = p.tasks.select_related('assignee','type_def').filter(
            Q(planned_date__range=(start, end)) | Q(status=Task.DONE, done_date__range=(start, end))
        ).order_by('-planned_date')[:40]
        ctx['page_title'] = p.name
        ctx['credentials'] = p.credentials.all()
        return ctx


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/form.html'

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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = f'ویرایش {self.object.name}'
        ctx['is_edit'] = True
        return ctx


class ProjectArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        project.archive()
        return redirect(project.get_absolute_url())


class ProjectRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        project.restore()
        return redirect(project.get_absolute_url())


# ── API دسترسی‌ها (JSON) ────────────────────────────────────────────────

def _cred_json(cred):
    return {
        'id': cred.id, 'title': cred.title, 'url': cred.url,
        'username': cred.username, 'note': cred.note,
    }


@require_http_methods(['POST'])
def credential_create(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'نیاز به ورود'}, status=403)
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
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'نیاز به ورود'}, status=403)
    cred = get_object_or_404(Credential, pk=pk)
    ActivityLog.objects.create(
        actor=request.user, verb='reveal_credential', content_object=cred,
        changes={'credential': cred.title, 'project': cred.project.name},
    )
    return JsonResponse({'password': cred.reveal_password()})


@require_http_methods(['DELETE'])
def credential_delete(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'نیاز به ورود'}, status=403)
    cred = get_object_or_404(Credential, pk=pk)
    cred.delete()
    return JsonResponse({'ok': True})


# ── فایل‌های پروژه (Attachment) ──────────────────────────────────────────

def _file_json(a):
    return {'id': a.id, 'name': a.original_name or a.file.name.split('/')[-1],
            'url': a.file.url, 'is_image': a.is_image, 'size': a.size_h}


@require_http_methods(['GET', 'POST'])
def project_files(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'نیاز به ورود'}, status=403)
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
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'نیاز به ورود'}, status=403)
    from core.models import Attachment
    get_object_or_404(Attachment, pk=pk).delete()
    return JsonResponse({'ok': True})
